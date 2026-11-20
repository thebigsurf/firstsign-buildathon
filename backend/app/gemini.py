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

log = logging.getLogger("firstsign.gemini")

RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}
SEARCH_BLOCK_S = 300.0  # after a grounding quota error, skip search for this long instead of waiting on futile retries
MAX_QUOTA_WAIT_S = 45.0  # longest Retry-After we will sit through on a 429
MODEL_COOLDOWN_S = 600.0  # a model that is out of daily quota or missing is skipped for this long
SKIP_MODEL_CODES = {400, 403, 404}  # this model cannot serve the request: try the next one


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


class GeminiClient:
    """Thin, resilient wrapper over google-genai."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
    ) -> GeminiResult:
        """Call Gemini with a response schema and return JSON text. `fast=True` turns thinking down for parsing."""
        return self._run(models, prompt, system, media, temperature, use_cache, schema=schema, search=False, fast=fast)

    def generate_grounded(
        self,
        models: Sequence[str],
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.2,
        use_cache: bool = True,
    ) -> GeminiResult:
        """Call Gemini with the Google Search tool; sources come from grounding metadata."""
        return self._run(models, prompt, system, (), temperature, use_cache, schema=None, search=True, fast=False)

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
        fast: bool,
    ) -> GeminiResult:
        if self.offline:
            raise UpstreamError("Gemini is in offline demo mode: no live call was made.")
        if search and time.monotonic() < self._search_blocked_until:
            raise UpstreamError("Google Search grounding is over its quota right now; skipped.")
        mode = ("search" if search else "json") + ("-fast" if fast else "")
        schema_name = schema.__name__ if schema else ""
        key = self.cache_key(models[0], mode, prompt, system, schema_name, media)
        if use_cache:
            hit = self._cache_read(key)
            if hit:
                self._record(cache_hit=True)
                return GeminiResult(
                    text=hit["text"],
                    model=hit["model"],
                    latency_ms=int(hit["latency_ms"]),
                    cached=True,
                    sources=hit.get("sources", []),
                    search_queries=hit.get("search_queries", []),
                )

        failures: list[str] = []
        deadline = time.monotonic() + self.settings.gemini_deadline_s
        for model in models:
            if time.monotonic() > deadline:
                failures.append("overall time limit reached")
                break
            if time.monotonic() < self._model_blocked_until.get(model, 0.0) and model != models[-1]:
                failures.append(f"{model} skipped (cooling down)")
                continue
            result = self._call_with_retries(model, prompt, system, media, temperature, schema, search, fast, failures,
                                             deadline)
            if result is not None:
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
        fast: bool,
        failures: list[str],
        deadline: float,
    ) -> GeminiResult | None:
        from google.genai import errors

        attempts = max(1, self.settings.gemini_max_attempts)
        for attempt in range(1, attempts + 1):
            if time.monotonic() > deadline:
                return None
            started = time.perf_counter()
            try:
                with self._slots:
                    text, sources, queries = self._once(model, prompt, system, media, temperature, schema, search, fast)
                latency = int((time.perf_counter() - started) * 1000)
                if not text.strip():
                    raise ValueError("empty response")
                log.info("gemini ok model=%s attempt=%d latency_ms=%d search=%s", model, attempt, latency, search)
                return GeminiResult(text=text, model=model, latency_ms=latency, sources=sources, search_queries=queries)
            except errors.APIError as exc:
                code = int(getattr(exc, "code", 0) or 0)
                failures.append(f"{model} HTTP {code}")
                log.warning("gemini error model=%s attempt=%d code=%s", model, attempt, code)
                if code == 400 and fast and "hinking" in str(exc):
                    fast = False  # this model rejects our thinking setting: retry it with its default
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
                        time.sleep(wait)
                        continue
            except Exception as exc:  # timeouts, connection resets, empty bodies
                failures.append(f"{model} {type(exc).__name__}")
                log.warning("gemini failure model=%s attempt=%d type=%s", model, attempt, type(exc).__name__)
                if "Timeout" in type(exc).__name__:
                    return None  # a model that is this slow will not recover on retry: try the next one
            if attempt < attempts:
                time.sleep(min(8.0, (2 ** (attempt - 1)) * 1.0 + random.uniform(0, 0.4)))
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
        fast: bool,
    ) -> tuple[str, list[dict[str, str]], list[str]]:
        from google.genai import types

        parts: list[Any] = [types.Part.from_bytes(data=m.data, mime_type=m.mime_type) for m in media]
        parts.append(prompt)
        config_args: dict[str, Any] = {"temperature": temperature}
        if system:
            config_args["system_instruction"] = system
        if schema is not None:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = schema
        if search:
            config_args["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        if fast:
            thinking = fast_thinking_config(model)
            if thinking is not None:
                config_args["thinking_config"] = thinking
        response = self._sdk().models.generate_content(
            model=model, contents=parts, config=types.GenerateContentConfig(**config_args)
        )
        sources, queries = extract_grounding(response) if search else ([], [])
        return response.text or "", sources, queries


def retry_delay_s(exc: Exception) -> float | None:
    """Seconds Gemini asks us to wait (RetryInfo in a 429), or None if it did not say."""
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


def fast_thinking_config(model: str) -> Any:
    """Minimal thinking for extraction work (transcribe and structure), where reasoning adds latency, not accuracy."""
    from google.genai import types

    if model.startswith("gemini-3.5"):
        return types.ThinkingConfig(thinking_level="MINIMAL")
    if model.startswith("gemini-3"):
        return types.ThinkingConfig(thinking_level="LOW")
    if model.startswith("gemini-2.5-flash"):
        return types.ThinkingConfig(thinking_budget=0)
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
