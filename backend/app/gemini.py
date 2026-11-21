"""The single Gemini client for FirstSign.

Responsibilities:
  * model fallback chain with exponential backoff on 429/500/503/504 and timeouts
  * structured output (response schema) and Google Search grounding helpers
  * latency measurement on every call
  * a disk cache keyed by sha256 of (model, prompt, media bytes) so repeated demo
    runs are instant and the free-tier quota is spared
  * DEMO_OFFLINE: canned answers from data/samples/*.expected.json, matched by
    media filename or content hash
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .config import Settings
from .errors import BadRequest, UpstreamError
from .usage import UsageLedger, token_usage

log = logging.getLogger("firstsign.gemini")

RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}
SEARCH_BLOCK_S = 300.0  # after a grounding quota error, skip search for this long instead of waiting on futile retries
MAX_QUOTA_WAIT_S = 45.0  # longest Retry-After we will sit through on a 429
MODEL_COOLDOWN_S = 600.0  # a model that is out of daily quota or missing is skipped for this long
SKIP_MODEL_CODES = {400, 403, 404}
THINKING_LEVELS = ("minimal", "low", "medium", "high")  # this model cannot serve the request: try the next one


@dataclass(frozen=True)
class Media:
    """A binary input (audio or image) sent inline to Gemini."""

    data: bytes
    mime_type: str
    filename: str = ""

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass
class GeminiResult:
    text: str
    model: str
    latency_ms: int
    cached: bool = False
    sources: list[dict[str, str]] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)
    queue_ms: int = 0
    attempt: int = 1

    def json(self) -> dict[str, Any]:
        return parse_json_text(self.text)


def parse_json_text(text: str) -> dict[str, Any]:
    """Parse model JSON, tolerating a Markdown code fence around it."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise UpstreamError(f"Gemini returned text that is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise UpstreamError("Gemini returned JSON that is not an object.")
    return value


class SampleIndex:
    """Offline answers: data/samples/<name>.expected.json looked up by filename or media hash."""

    def __init__(self, samples_dir: Path) -> None:
        self.dir = samples_dir
        self._by_stem: dict[str, Path] = {}
        self._by_hash: dict[str, Path] = {}
        self._built = False
        self._lock = threading.Lock()

    def _build(self) -> None:
        with self._lock:
            if self._built:
                return
            if self.dir.exists():
                for expected in self.dir.glob("*.expected.json"):
                    stem = expected.name[: -len(".expected.json")]
                    self._by_stem[stem.lower()] = expected
                for media in self.dir.iterdir():
                    if media.is_file() and not media.name.endswith(".json") and media.name != ".gitkeep":
                        expected = self._by_stem.get(media.stem.lower())
                        if expected:
                            self._by_hash[hashlib.sha256(media.read_bytes()).hexdigest()] = expected
            self._built = True

    def lookup(self, filename: str | None = None, data: bytes | None = None) -> dict[str, Any] | None:
        """Return the expected JSON for a sample, or None if it is not a known sample."""
        self._build()
        path: Path | None = None
        if data is not None:
            path = self._by_hash.get(hashlib.sha256(data).hexdigest())
        if path is None and filename:
            path = self._by_stem.get(Path(filename).stem.lower())
        if path is None:
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def lookup_path(self, relative: str) -> dict[str, Any] | None:
        """Read an expected-JSON path given relative to data/ (as in demo_inbox.json)."""
        target = (self.dir.parent / relative).resolve()
        if self.dir.parent.resolve() not in target.parents or not target.is_file():
            return None
        return json.loads(target.read_text(encoding="utf-8"))


class BudgetExceeded(UpstreamError):
    """The daily Gemini spend guard is closed: callers fall back to labelled cached or offline results."""


class GeminiClient:
    """Thin, resilient wrapper over google-genai."""

    def __init__(self, settings: Settings, ledger: UsageLedger | None = None) -> None:
        self.settings = settings
        self.ledger = ledger or UsageLedger(None, usd_inr=settings.usd_inr, budget_inr=settings.daily_budget_inr)
        self.offline_samples = SampleIndex(settings.data_dir / "samples")
        self._client: Any = None
        self._client_lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(settings.gemini_max_concurrency)
        settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self._stats_lock = threading.Lock()
        self._calls = 0
        self._errors = 0
        self._fallbacks = 0
        self._cache_hits = 0
        self._latency_total = 0
        self._sources_total = 0
        self._by_model: dict[str, int] = {}
        self._search_blocked_until = 0.0
        self._model_blocked_until: dict[str, float] = {}

    def telemetry(self) -> dict[str, Any]:
        """Usage counters since start-up (live calls only, cache hits counted separately)."""
        with self._stats_lock:
            return {
                "calls": self._calls, "by_model": dict(self._by_model), "fallbacks": self._fallbacks,
                "errors": self._errors, "avg_latency_ms": int(self._latency_total / self._calls) if self._calls else 0,
                "grounded_sources_total": self._sources_total, "cache_hits": self._cache_hits,
                "offline": self.offline,
            }

    def _record(self, *, result: GeminiResult | None = None, first_model: str = "", cache_hit: bool = False,
                error: bool = False) -> None:
        with self._stats_lock:
            if cache_hit:
                self._cache_hits += 1
            elif error:
                self._errors += 1
            elif result is not None:
                self._calls += 1
                self._latency_total += result.latency_ms
                self._sources_total += len(result.sources)
                self._by_model[result.model] = self._by_model.get(result.model, 0) + 1
                if result.model != first_model:
                    self._fallbacks += 1

    # ------------------------------------------------------------------ plumbing

    @property
    def offline(self) -> bool:
        return self.settings.offline

    def _sdk(self) -> Any:
        with self._client_lock:
            if self._client is None:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=self.settings.gemini_api_key,
                    http_options=types.HttpOptions(timeout=int(self.settings.gemini_timeout_s * 1000)),
                )
            return self._client

    @staticmethod
    def cache_key(model: str, mode: str, prompt: str, system: str, schema_name: str, media: Sequence[Media]) -> str:
        digest = hashlib.sha256()
        for part in (model, mode, system, schema_name, prompt):
            digest.update(part.encode("utf-8"))
            digest.update(b"\x00")
        for item in media:
            digest.update(item.mime_type.encode())
            digest.update(item.data)
        return digest.hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.settings.cache_dir / f"{key}.json"

    def _cache_read(self, key: str) -> dict[str, Any] | None:
        path = self._cache_path(key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _cache_write(self, key: str, payload: dict[str, Any]) -> None:
        path = self._cache_path(key)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            log.warning("could not write Gemini cache entry")

    # ------------------------------------------------------------------ calls

    def generate_structured(
        self,
        models: Sequence[str],
        prompt: str,
        schema: type[BaseModel],
        *,
        media: Sequence[Media] = (),
        system: str = "",
        temperature: float = 0.0,
        use_cache: bool = True,
        fast: bool = False,
        thinking: str | None = None,
        job: str = "unknown",
        max_output_tokens: int | None = None,
        deadline_s: float | None = None,
    ) -> GeminiResult:
        """Call Gemini with a response schema and return JSON text.

        `thinking` is "minimal", "low", "medium" or "high" (`fast=True` means "minimal"): low for extraction, higher
        for reasoning. `job` labels the call in the usage ledger. `deadline_s` caps the whole fallback chain.
        """
        return self._run(models, prompt, system, media, temperature, use_cache, schema=schema, search=False,
                         thinking=thinking or ("minimal" if fast else None), job=job,
                         max_output_tokens=max_output_tokens, deadline_s=deadline_s)

    def generate_grounded(
        self,
        models: Sequence[str],
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.2,
        use_cache: bool = True,
        thinking: str | None = None,
        job: str = "explain_grounded",
    ) -> GeminiResult:
        """Call Gemini with the Google Search tool; sources come from grounding metadata."""
        return self._run(models, prompt, system, (), temperature, use_cache, schema=None, search=True,
                         thinking=thinking, job=job)

    def _run(
        self,
        models: Sequence[str],
        prompt: str,
        system: str,
        media: Sequence[Media],
        temperature: float,
        use_cache: bool,
        *,
        schema: type[BaseModel] | None,
        search: bool,
        thinking: str | None,
        job: str = "unknown",
        max_output_tokens: int | None = None,
        deadline_s: float | None = None,
    ) -> GeminiResult:
        if self.offline:
            raise UpstreamError("Gemini is in offline demo mode: no live call was made.")
        if search and time.monotonic() < self._search_blocked_until:
            raise UpstreamError("Google Search grounding is over its quota right now; skipped.")
        mode = ("search" if search else "json") + (f"-{thinking}" if thinking else "")
        schema_name = schema.__name__ if schema else ""
        key = self.cache_key(models[0], mode, prompt, system, schema_name, media)
        if use_cache and not self.settings.bypass_cache:
            hit = self._cache_read(key)
            if hit:
                self._record(cache_hit=True)
                self.ledger.record(job=job, model=hit["model"], requested_model=models[0], disk_cache_hit=True,
                                   latency_ms=0, grounded=search, sources=len(hit.get("sources", [])))
                return GeminiResult(
                    text=hit["text"],
                    model=hit["model"],
                    latency_ms=int(hit["latency_ms"]),
                    cached=True,
                    sources=hit.get("sources", []),
                    search_queries=hit.get("search_queries", []),
                )

        if self.ledger.over_budget():
            self.ledger.record(job=job, model=models[0], requested_model=models[0], error_code="budget")
            raise BudgetExceeded("The daily AI budget is used up, so no new Gemini call was made. Showing the "
                                 "labelled saved result instead.")
        failures: list[str] = []
        deadline = time.monotonic() + (deadline_s if deadline_s is not None else self.settings.gemini_deadline_s)
        for model in models:
            if time.monotonic() > deadline:
                failures.append("overall time limit reached")
                break
            if time.monotonic() < self._model_blocked_until.get(model, 0.0) and model != models[-1]:
                failures.append(f"{model} skipped (cooling down)")
                continue
            result = self._call_with_retries(model, prompt, system, media, temperature, schema, search, thinking,
                                             failures, deadline, job, models[0], max_output_tokens)
            if result is not None:
                self.ledger.record(job=job, model=result.model, requested_model=models[0], tokens=result.tokens,
                                   latency_ms=result.latency_ms, queue_ms=result.queue_ms, attempt=result.attempt,
                                   fallback=result.model != models[0], grounded=search, sources=len(result.sources))
                self._record(result=result, first_model=models[0])
                self._cache_write(
                    key,
                    {
                        "text": result.text,
                        "model": result.model,
                        "latency_ms": result.latency_ms,
                        "sources": result.sources,
                        "search_queries": result.search_queries,
                    },
                )
                return result
        self._record(error=True)
        real = [f for f in failures if "skipped" not in f]
        if media and real and all(f.endswith("HTTP 400") for f in real):
            raise BadRequest("Gemini could not read this file as audio or an image. Please upload a genuine file.",
                             code="invalid_media")
        if search and any("HTTP 429" in f for f in failures):
            self._search_blocked_until = time.monotonic() + SEARCH_BLOCK_S
        raise UpstreamError("Every Gemini model in the fallback chain failed: " + "; ".join(failures[-4:]))

    def _call_with_retries(
        self,
        model: str,
        prompt: str,
        system: str,
        media: Sequence[Media],
        temperature: float,
        schema: type[BaseModel] | None,
        search: bool,
        thinking: str | None,
        failures: list[str],
        deadline: float,
        job: str = "unknown",
        first_model: str = "",
        max_output_tokens: int | None = None,
    ) -> GeminiResult | None:
        from google.genai import errors

        attempts = max(1, self.settings.gemini_max_attempts)
        for attempt in range(1, attempts + 1):
            if time.monotonic() > deadline:
                return None
            queued = time.perf_counter()
            queue_ms = 0
            try:
                with self._slots:  # per-process concurrency cap: a burst waits here instead of hitting the quota
                    started = time.perf_counter()
                    queue_ms = int((started - queued) * 1000)
                    out = self._once(model, prompt, system, media, temperature, schema, search, thinking,
                                     timeout_s=deadline - time.monotonic(), max_output_tokens=max_output_tokens)
                    text, sources, queries = out[0], out[1], out[2]
                    tokens = out[3] if len(out) > 3 else {}
                latency = int((time.perf_counter() - started) * 1000)
                if not text.strip():
                    raise ValueError("empty response")
                log.info("gemini ok job=%s model=%s attempt=%d latency_ms=%d tokens=%s", job, model, attempt, latency,
                         tokens.get("total_tokens"))
                return GeminiResult(text=text, model=model, latency_ms=latency, sources=sources, search_queries=queries,
                                    tokens=tokens, queue_ms=queue_ms, attempt=attempt)
            except errors.APIError as exc:
                code = int(getattr(exc, "code", 0) or 0)
                failures.append(f"{model} HTTP {code}")
                self.ledger.record(job=job, model=model, requested_model=first_model, attempt=attempt,
                                   queue_ms=queue_ms, error_code=str(code or "api"), grounded=search)
                log.warning("gemini error model=%s attempt=%d code=%s", model, attempt, code)
                if code == 400 and thinking and "hinking" in str(exc):
                    thinking = None  # this model rejects our thinking setting: retry it with its default
                    continue
                if code == 404:
                    self._model_blocked_until[model] = time.monotonic() + MODEL_COOLDOWN_S
                if code in SKIP_MODEL_CODES or code not in RETRYABLE_CODES:
                    return None
                if search and code == 429:
                    return None  # grounding quota is separate and rarely recovers within seconds
                wait = retry_delay_s(exc)
                if code == 429 and wait is not None:
                    if wait > MAX_QUOTA_WAIT_S:
                        if not search:
                            self._model_blocked_until[model] = time.monotonic() + MODEL_COOLDOWN_S
                        return None  # quota window is long: the next model in the chain is the better bet
                    if attempt < attempts:
                        wait += random.uniform(0, 0.25 * wait + 0.25)  # jitter so parallel clients do not re-collide
                        if time.monotonic() + wait > deadline:
                            return None  # waiting would blow this request's budget
                        time.sleep(wait)
                        continue
            except Exception as exc:  # timeouts, connection resets, empty bodies
                failures.append(f"{model} {type(exc).__name__}")
                self.ledger.record(job=job, model=model, requested_model=first_model, attempt=attempt,
                                   queue_ms=queue_ms, error_code=type(exc).__name__, grounded=search)
                log.warning("gemini failure model=%s attempt=%d type=%s", model, attempt, type(exc).__name__)
                if "Timeout" in type(exc).__name__:
                    return None  # a model that is this slow will not recover on retry: try the next one
            if attempt < attempts:
                pause = min(8.0, (2 ** (attempt - 1)) * 1.0 + random.uniform(0, 0.4))
                if time.monotonic() + pause > deadline:
                    return None
                time.sleep(pause)
        return None

    def _once(
        self,
        model: str,
        prompt: str,
        system: str,
        media: Sequence[Media],
        temperature: float,
        schema: type[BaseModel] | None,
        search: bool,
        thinking: str | None,
        timeout_s: float | None = None,
        max_output_tokens: int | None = None,
    ) -> tuple[str, list[dict[str, str]], list[str], dict[str, int]]:
        from google.genai import types

        # Stable text first, then the variable media (the shared prefix is what implicit caching keys on).
        parts: list[Any] = [prompt]
        parts.extend(types.Part.from_bytes(data=m.data, mime_type=m.mime_type) for m in media)
        config_args: dict[str, Any] = {"temperature": temperature}
        if system:
            config_args["system_instruction"] = system
        if schema is not None:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = schema
        if search:
            config_args["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        if thinking:
            config = thinking_config(model, thinking)
            if config is not None:
                config_args["thinking_config"] = config
        if max_output_tokens:
            config_args["max_output_tokens"] = max_output_tokens
        resolution = self.settings.image_resolution
        if resolution and any(m.mime_type.startswith("image/") for m in media):
            config_args["media_resolution"] = getattr(types.MediaResolution, f"MEDIA_RESOLUTION_{resolution.upper()}",
                                                      types.MediaResolution.MEDIA_RESOLUTION_UNSPECIFIED)
        if timeout_s is not None:
            # Never wait longer than the request's remaining budget (and never longer than the client default).
            budget = max(1.0, min(timeout_s, self.settings.gemini_timeout_s))
            config_args["http_options"] = types.HttpOptions(timeout=int(budget * 1000))
        response = self._sdk().models.generate_content(
            model=model, contents=parts, config=types.GenerateContentConfig(**config_args)
        )
        sources, queries = extract_grounding(response) if search else ([], [])
        return response.text or "", sources, queries, token_usage(response)


def retry_delay_s(exc: Exception) -> float | None:
    """Seconds Gemini asks us to wait (RetryInfo in a 429), or None if it did not say."""
    headers = getattr(getattr(exc, "response", None), "headers", None)
    try:
        header = headers.get("retry-after") if headers is not None else None
        if header is not None:
            return min(float(header), 3600.0)  # standard Retry-After in seconds
    except (TypeError, ValueError, AttributeError):
        pass
    details = getattr(exc, "details", None)
    items = details.get("error", {}).get("details", []) if isinstance(details, dict) else []
    for item in items:
        if str(item.get("@type", "")).endswith("RetryInfo"):
            raw = str(item.get("retryDelay", "")).rstrip("s")
            try:
                return float(raw)
            except ValueError:
                return None
    return None


def thinking_config(model: str, level: str) -> Any:
    """Thinking level per model family, clamped to what the official docs list for it.

    Extraction (transcribe and structure) runs at "minimal"; the reasoning agent at "medium". Gemini 3.8 and 4 have no
    "minimal", so it becomes "low" there. 2.5-era models use a token budget instead of a level.
    """
    from google.genai import types

    level = level if level in THINKING_LEVELS else "low"
    if model.startswith("gemini-2.5-flash"):
        return types.ThinkingConfig(thinking_budget={"minimal": 0, "low": 512, "medium": 2048, "high": 8192}[level])
    if model.startswith(("gemini-4", "gemini-3.8")) and level == "minimal":
        level = "low"
    if model.startswith(("gemini-4", "gemini-3")):
        return types.ThinkingConfig(thinking_level=level.upper())
    return None


def extract_grounding(response: Any) -> tuple[list[dict[str, str]], list[str]]:
    """Pull (title, url) sources and search queries out of grounding metadata."""
    sources: list[dict[str, str]] = []
    queries: list[str] = []
    seen: set[str] = set()
    for candidate in getattr(response, "candidates", None) or []:
        meta = getattr(candidate, "grounding_metadata", None)
        if meta is None:
            continue
        queries.extend(getattr(meta, "web_search_queries", None) or [])
        for chunk in getattr(meta, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None) if web else None
            if not uri or uri in seen:
                continue
            seen.add(uri)
            title = getattr(web, "title", None) or getattr(web, "domain", None) or uri
            sources.append({"title": str(title), "url": str(uri)})
    return sources, queries
