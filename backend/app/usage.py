"""Usage ledger for every Gemini call: tokens by type, latency, cache and fallback flags, cost, daily budget guard.

Prices are the official list prices from https://ai.google.dev/gemini-api/docs/pricing (read 21 Nov 2026, USD per
1M tokens, standard paid tier). A model that page does not list is priced by a named proxy and flagged, never silently.
The ledger is append-only, thread-safe, kept in memory for fast summaries and mirrored to the store.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

IST = timezone(timedelta(hours=5, minutes=30))
GROUNDING_USD_PER_REQUEST = 14.0 / 1000  # after the free monthly allowance
GROUNDING_FREE_PER_MONTH = 5000
MAX_KEPT = 5000


@dataclass(frozen=True)
class Price:
    """USD per 1M tokens."""

    input: float
    output: float
    cached: float
    audio_input: float | None = None
    listed: bool = True  # False: the model id is not on the official pricing page; `basis` names the proxy used
    basis: str = ""


# Longest matching prefix wins. See docs/GEMINI_ENGINEERING.md for the source of each row.
PRICES: dict[str, Price] = {
    "gemini-3.8-flash": Price(0.75, 3.75, 0.075, basis="list price through 31 Dec 2026 (doubles from 1 Jan 2027)"),
    "gemini-3.1-flash-lite": Price(0.25, 1.50, 0.025, audio_input=0.50, basis="list price"),
    "gemini-3.5-flash-lite": Price(0.30, 2.50, 0.03, basis="list price"),
    "gemini-4-hydrogen": Price(1.50, 7.50, 0.075, basis="list price"),
    # gemini-3.5-flash serves requests but is not on the pricing page: priced as its listed sibling 3.5-flash-lite.
    "gemini-3.5-flash": Price(0.30, 2.50, 0.03, listed=False, basis="not listed; priced as gemini-3.5-flash-lite"),
}
UNKNOWN_PRICE = Price(1.50, 7.50, 0.075, listed=False, basis="unknown model; priced at the most expensive listed model")


def price_for(model: str) -> Price:
    best = ""
    for prefix in PRICES:
        if model.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    return PRICES[best] if best else UNKNOWN_PRICE


def token_usage(response: Any) -> dict[str, int]:
    """Pull the token counts out of a google-genai response's usage_metadata (missing fields count as 0)."""
    meta = getattr(response, "usage_metadata", None)

    def n(name: str) -> int:
        value = getattr(meta, name, None) if meta is not None else None
        return int(value) if isinstance(value, (int, float)) else 0

    audio = 0
    for item in (getattr(meta, "prompt_tokens_details", None) or []) if meta is not None else []:
        if "AUDIO" in str(getattr(item, "modality", "")).upper():
            audio += int(getattr(item, "token_count", 0) or 0)
    prompt, out, thoughts, cached = (n("prompt_token_count"), n("candidates_token_count"), n("thoughts_token_count"),
                                     n("cached_content_token_count"))
    total = n("total_token_count") or prompt + out + thoughts + n("tool_use_prompt_token_count")
    return {"prompt_tokens": prompt, "output_tokens": out, "thought_tokens": thoughts, "cached_tokens": cached,
            "audio_tokens": audio, "tool_tokens": n("tool_use_prompt_token_count"), "total_tokens": total}


def cost_usd(model: str, tok: dict[str, int], grounded_paid: bool = False) -> float:
    price = price_for(model)
    cached = min(tok.get("cached_tokens", 0), tok.get("prompt_tokens", 0))
    audio = min(tok.get("audio_tokens", 0), max(0, tok.get("prompt_tokens", 0) - cached))
    text = max(0, tok.get("prompt_tokens", 0) - cached - audio)
    usd = (text * price.input + audio * (price.audio_input or price.input) + cached * price.cached
           + (tok.get("output_tokens", 0) + tok.get("thought_tokens", 0)) * price.output) / 1e6
    return usd + (GROUNDING_USD_PER_REQUEST if grounded_paid else 0.0)


def _pct(values: list[float], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return int(ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))])


class UsageLedger:
    def __init__(self, store: Any = None, *, usd_inr: float = 90.0, budget_inr: float = 300.0,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.store, self.usd_inr, self.budget_inr = store, usd_inr, budget_inr
        self._clock = clock or (lambda: datetime.now(IST))
        self._lock = threading.Lock()
        self._rows: deque[dict[str, Any]] = deque(maxlen=MAX_KEPT)
        if store is not None:
            try:
                for row in store.list_ai_usage()[-MAX_KEPT:]:
                    self._rows.append(row)
            except Exception:  # a store without the collection must not stop the app
                pass

    # ------------------------------------------------------------------ writing

    def record(self, *, job: str, model: str, requested_model: str = "", tokens: dict[str, int] | None = None,
               latency_ms: int = 0, queue_ms: int = 0, attempt: int = 1, disk_cache_hit: bool = False,
               fallback: bool = False, error_code: str | None = None, grounded: bool = False,
               sources: int = 0) -> dict[str, Any]:
        tok = tokens or {}
        now = self._clock()
        month = now.strftime("%Y-%m")
        with self._lock:
            paid_grounding = False
            if grounded and not error_code and not disk_cache_hit:
                used = sum(1 for r in self._rows if r.get("grounded") and not r.get("error_code")
                           and not r.get("disk_cache_hit") and r["day"].startswith(month))
                paid_grounding = used >= GROUNDING_FREE_PER_MONTH
            usd = 0.0 if disk_cache_hit else cost_usd(model, tok, paid_grounding)
            row = {
                "id": uuid.uuid4().hex[:12], "ts": now.isoformat(timespec="seconds"), "day": now.strftime("%Y-%m-%d"),
                "job": job, "model": model, "requested_model": requested_model or model,
                "prompt_tokens": tok.get("prompt_tokens", 0), "output_tokens": tok.get("output_tokens", 0),
                "thought_tokens": tok.get("thought_tokens", 0), "cached_tokens": tok.get("cached_tokens", 0),
                "audio_tokens": tok.get("audio_tokens", 0), "total_tokens": tok.get("total_tokens", 0),
                "latency_ms": latency_ms, "queue_ms": queue_ms, "attempt": attempt,
                "disk_cache_hit": disk_cache_hit, "fallback": fallback, "error_code": error_code,
                "grounded": grounded, "sources": sources, "cost_usd": round(usd, 6),
                "cost_inr": round(usd * self.usd_inr, 4), "price_listed": price_for(model).listed,
            }
            self._rows.append(row)
        if self.store is not None:
            try:
                self.store.add_ai_usage(row)
            except Exception:
                pass
        return row

    # ------------------------------------------------------------------ budget

    def spent_today_inr(self) -> float:
        today = self._clock().strftime("%Y-%m-%d")
        with self._lock:
            return sum(r["cost_inr"] for r in self._rows if r["day"] == today)

    def over_budget(self) -> bool:
        return self.budget_inr > 0 and self.spent_today_inr() >= self.budget_inr

    # ------------------------------------------------------------------ summary

    def rows(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._rows)

    def summary(self) -> dict[str, Any]:
        rows = self.rows()
        live = [r for r in rows if not r["disk_cache_hit"] and not r["error_code"] and r["model"] != "labelled-sample"]
        hits = [r for r in rows if r["disk_cache_hit"]]
        errors = [r for r in rows if r["error_code"] and r["model"] != "labelled-sample"]
        labelled = [r for r in rows if r["model"] == "labelled-sample"]

        def bucket(items: list[dict[str, Any]]) -> dict[str, Any]:
            n = len(items)
            tot = lambda k: sum(r[k] for r in items)  # noqa: E731
            lat = [r["latency_ms"] for r in items]
            return {
                "calls": n, "prompt_tokens": tot("prompt_tokens"), "output_tokens": tot("output_tokens"),
                "thought_tokens": tot("thought_tokens"), "cached_tokens": tot("cached_tokens"),
                "audio_tokens": tot("audio_tokens"), "total_tokens": tot("total_tokens"),
                "cost_inr": round(tot("cost_inr"), 4),
                "avg_prompt_tokens": int(tot("prompt_tokens") / n) if n else 0,
                "avg_output_tokens": int(tot("output_tokens") / n) if n else 0,
                "avg_thought_tokens": int(tot("thought_tokens") / n) if n else 0,
                "avg_total_tokens": int(tot("total_tokens") / n) if n else 0,
                "avg_cost_inr": round(tot("cost_inr") / n, 4) if n else 0.0,
                "avg_latency_ms": int(sum(lat) / n) if n else 0,
                "p50_latency_ms": _pct(lat, 0.5), "p95_latency_ms": _pct(lat, 0.95),
            }

        def group(key: str) -> dict[str, dict[str, Any]]:
            names = sorted({r[key] for r in live})
            return {name: bucket([r for r in live if r[key] == name]) for name in names}

        answered = len(live) + len(hits)
        prompt_total = sum(r["prompt_tokens"] for r in live)
        fallbacks = [r for r in live if r["fallback"]]
        parse_jobs = ("parse_audio", "parse_image", "parse_text")
        parse = [r for r in live if r["job"] in parse_jobs]
        spent = self.spent_today_inr()
        return {
            "totals": {**bucket(live), "errors": len(errors), "disk_cache_hits": len(hits),
                       "labelled_fallbacks": len(labelled), "requests_seen": len(rows)},
            "by_job": group("job"), "by_model": group("model"),
            "cache": {"disk_hit_rate": round(len(hits) / answered, 3) if answered else 0.0,
                      "implicit_cached_token_share": round(sum(r["cached_tokens"] for r in live) / prompt_total, 3)
                      if prompt_total else 0.0},
            "fallback_rate": round((len(fallbacks) + len(labelled)) / (len(live) + len(labelled)), 3)
            if (live or labelled) else 0.0,
            "error_rate": round(len(errors) / (len(live) + len(errors)), 3) if (live or errors) else 0.0,
            "latency_ms": {"p50": _pct([r["latency_ms"] for r in live], 0.5),
                           "p95": _pct([r["latency_ms"] for r in live], 0.95)},
            "cost_per_order_inr": round(sum(r["cost_inr"] for r in parse) / len(parse), 4) if parse else 0.0,
            "budget": {"daily_inr": self.budget_inr, "spent_today_inr": round(spent, 4),
                       "remaining_inr": round(max(0.0, self.budget_inr - spent), 4),
                       "exceeded": self.budget_inr > 0 and spent >= self.budget_inr},
            "assumptions": {"usd_inr": self.usd_inr, "currency": "INR",
                            "prices_usd_per_1m": {m: {"input": p.input, "audio_input": p.audio_input or p.input,
                                                      "output_incl_thinking": p.output, "cached_input": p.cached,
                                                      "listed_on_pricing_page": p.listed, "basis": p.basis}
                                                  for m, p in PRICES.items()},
                            "grounding_usd_per_request_after_free_5000_month": GROUNDING_USD_PER_REQUEST},
            "since": rows[0]["ts"] if rows else None,
        }


def now_ms() -> float:
    return time.perf_counter() * 1000
