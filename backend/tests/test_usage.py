"""Usage ledger, rate limiter, budget guard and the cache-friendly prompt layout."""

from __future__ import annotations

import dataclasses
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.errors import UpstreamError
from app.gemini import BudgetExceeded, GeminiClient, Media
from app.models import ModelOrderOut
from app.parsing import ORDER_SYSTEM, _order_prompt, _order_system
from app.ratelimit import RateLimited, RateLimiter
from app.usage import IST, UsageLedger, cost_usd, price_for, token_usage
from tests.conftest import FIXTURES, make_settings


def usage_meta(prompt: int, out: int, thoughts: int = 0, cached: int = 0, audio: int = 0) -> Any:
    details = [SimpleNamespace(modality="AUDIO", token_count=audio)] if audio else []
    return SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=prompt, candidates_token_count=out, thoughts_token_count=thoughts,
        cached_content_token_count=cached, total_token_count=prompt + out + thoughts, tool_use_prompt_token_count=None,
        prompt_tokens_details=details))


def test_token_usage_reads_every_field_and_tolerates_missing_metadata() -> None:
    tok = token_usage(usage_meta(1000, 200, thoughts=50, cached=600, audio=300))
    assert tok["prompt_tokens"] == 1000 and tok["cached_tokens"] == 600 and tok["audio_tokens"] == 300
    assert tok["total_tokens"] == 1250
    assert token_usage(SimpleNamespace(usage_metadata=None))["total_tokens"] == 0


def test_cost_uses_official_prices_and_charges_cached_tokens_less() -> None:
    tok = {"prompt_tokens": 1_000_000, "output_tokens": 100_000, "thought_tokens": 100_000, "cached_tokens": 600_000}
    # gemini-4-hydrogen: $1.50 in, $0.075 cached, $7.50 out (thinking is billed as output)
    assert cost_usd("gemini-4-hydrogen", tok) == pytest.approx(0.4 * 1.5 + 0.6 * 0.075 + 0.2 * 7.5)
    assert price_for("gemini-3.1-flash-lite").audio_input == 0.50
    assert price_for("gemini-3.5-flash").listed is False  # not on the official page: priced by a named proxy
    assert price_for("brand-new-model").listed is False


def test_ledger_summary_has_per_job_averages_cache_and_fallback_rates() -> None:
    ledger = UsageLedger(usd_inr=90, budget_inr=300)
    tok = {"prompt_tokens": 8000, "output_tokens": 700, "cached_tokens": 6000, "total_tokens": 8700}
    for latency in (1000, 2000, 3000, 4000):
        ledger.record(job="parse_audio", model="m1", requested_model="m1", tokens=tok, latency_ms=latency)
    ledger.record(job="parse_audio", model="m2", requested_model="m1", tokens=tok, latency_ms=9000, fallback=True)
    ledger.record(job="parse_audio", model="m1", disk_cache_hit=True)
    ledger.record(job="parse_audio", model="m1", error_code="503")
    ledger.record(job="parse_audio", model="labelled-sample", fallback=True, error_code="fell_back")
    s = ledger.summary()
    job = s["by_job"]["parse_audio"]
    assert job["calls"] == 5 and job["avg_prompt_tokens"] == 8000 and job["p50_latency_ms"] == 3000
    assert s["latency_ms"]["p95"] == 9000
    assert s["totals"]["disk_cache_hits"] == 1 and s["totals"]["errors"] == 1 and s["totals"]["labelled_fallbacks"] == 1
    assert s["cache"]["disk_hit_rate"] == round(1 / 6, 3)
    assert s["cache"]["implicit_cached_token_share"] == 0.75
    assert s["fallback_rate"] == round(2 / 6, 3)  # one model fallback + one labelled sample, of 5 live + 1 labelled
    assert s["cost_per_order_inr"] > 0 and s["by_model"]["m2"]["calls"] == 1


def test_ledger_persists_to_the_store_and_reloads(tmp_path: Path) -> None:
    from app.store import LocalStore

    store = LocalStore(tmp_path / "s.json")
    UsageLedger(store).record(job="asha_report", model="m", tokens={"prompt_tokens": 10, "output_tokens": 5})
    again = UsageLedger(LocalStore(tmp_path / "s.json"))
    assert again.summary()["totals"]["calls"] == 1


def test_daily_budget_resets_the_next_day() -> None:
    now = [datetime(2026, 11, 21, 10, tzinfo=IST)]
    ledger = UsageLedger(usd_inr=100, budget_inr=1.0, clock=lambda: now[0])
    ledger.record(job="x", model="gemini-4-hydrogen", tokens={"prompt_tokens": 100_000, "output_tokens": 0})  # 1.5 INR
    assert ledger.over_budget()
    now[0] = datetime(2026, 11, 22, 9, tzinfo=IST)
    assert not ledger.over_budget()


def live_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kw: Any) -> GeminiClient:
    monkeypatch.setattr("app.gemini.time.sleep", lambda _s: None)
    settings = dataclasses.replace(make_settings(tmp_path, FIXTURES, **kw), gemini_api_key="test-key", demo_offline=False)
    return GeminiClient(settings)


def test_budget_guard_blocks_the_call_but_a_cached_answer_still_serves(tmp_path: Path,
                                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch, daily_budget_inr=0.01)
    calls: list[str] = []

    def fake_once(self: GeminiClient, model: str, *a: Any, **kw: Any) -> tuple[Any, ...]:
        calls.append(model)
        return '{"language": "hi", "lines": []}', [], [], {"prompt_tokens": 1_000_000, "output_tokens": 0,
                                                            "total_tokens": 1_000_000}

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    first = client.generate_structured(("m",), "p", ModelOrderOut, job="parse_text")
    assert not first.cached and client.ledger.over_budget()
    again = client.generate_structured(("m",), "p", ModelOrderOut, job="parse_text")  # disk cache: free, allowed
    assert again.cached and calls == ["m"]
    with pytest.raises(BudgetExceeded):
        client.generate_structured(("m",), "different prompt", ModelOrderOut, job="parse_text")
    assert issubclass(BudgetExceeded, UpstreamError)  # callers' existing labelled-fallback path catches it
    assert calls == ["m"]


def test_every_live_call_lands_in_the_ledger_with_tokens_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from google.genai import errors

    client = live_client(tmp_path, monkeypatch)

    def fake_once(self: GeminiClient, model: str, *a: Any, **kw: Any) -> tuple[Any, ...]:
        if model == "m1":
            raise errors.APIError(503, {"error": {"code": 503, "message": "x"}})
        return "{}", [], [], {"prompt_tokens": 500, "output_tokens": 50, "cached_tokens": 400, "total_tokens": 550}

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    client.generate_structured(("m1", "m2"), "p", ModelOrderOut, job="parse_image")
    rows = client.ledger.rows()
    assert [r["error_code"] for r in rows] == ["503", "503", "503", None]
    assert rows[-1]["job"] == "parse_image" and rows[-1]["fallback"] is True and rows[-1]["cached_tokens"] == 400


def test_rate_limiter_blocks_the_burst_then_recovers() -> None:
    t = [0.0]
    limiter = RateLimiter(3, clock=lambda: t[0])
    for _ in range(3):
        limiter.check("1.2.3.4")
    with pytest.raises(RateLimited) as err:
        limiter.check("1.2.3.4")
    assert err.value.status_code == 429 and err.value.retry_after_s >= 1
    limiter.check("5.6.7.8")  # another client is unaffected
    t[0] = 61.0
    limiter.check("1.2.3.4")


def test_api_returns_429_with_retry_after_and_the_usage_endpoint_works(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.store import LocalStore

    app = create_app(make_settings(tmp_path, FIXTURES, rate_limit_per_min=2), LocalStore(tmp_path / "state.json"))
    with TestClient(app) as c:
        statuses = [c.post("/api/orders/parse", data={"text": "dolo 10"}).status_code for _ in range(3)]
        assert statuses[-1] == 429
        blocked = c.post("/api/orders/parse", data={"text": "dolo 10"})
        assert blocked.headers["retry-after"].isdigit() and "wait" in blocked.json()["error"]["message"]
        body = c.get("/api/ai/usage").json()
        assert {"totals", "by_job", "cache", "latency_ms", "budget", "assumptions", "limits"} <= body.keys()
        assert body["budget"]["daily_inr"] == 300 and c.get("/api/health").status_code == 200  # reads are not throttled


def test_oversized_text_is_rejected(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.store import LocalStore

    app = create_app(make_settings(tmp_path, FIXTURES, max_text_chars=50), LocalStore(tmp_path / "s.json"))
    with TestClient(app) as c:
        r = c.post("/api/orders/parse", data={"text": "x" * 51, "chemist_id": "C00"})
        assert r.status_code == 400 and r.json()["error"]["code"] == "too_long"


def test_parse_prompt_puts_the_stable_part_first_for_implicit_caching(fixture_catalogue: Any) -> None:
    system = _order_system(fixture_catalogue)
    assert system.startswith(ORDER_SYSTEM) and fixture_catalogue.prompt_table() in system
    a = _order_prompt(fixture_catalogue, {"language": "hi"}, "voice note", None)
    b = _order_prompt(fixture_catalogue, {"language": "mr"}, "photo", "other text")
    assert fixture_catalogue.prompt_table() not in a + b  # the variable part carries no catalogue
    assert _order_system(fixture_catalogue) == system  # byte-identical on every call: the cacheable prefix


def test_variable_media_comes_after_the_stable_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class FakeModels:
        def generate_content(self, model: str, contents: list[Any], config: Any) -> Any:
            captured["contents"], captured["config"] = contents, config
            r = usage_meta(10, 5)
            r.text, r.candidates = "{}", []
            return r

    client = live_client(tmp_path, monkeypatch)
    client._client = SimpleNamespace(models=FakeModels())
    client.generate_structured(("gemini-3.5-flash",), "variable text", ModelOrderOut, system="STABLE", thinking="minimal",
                               media=[Media(b"\xff\xd8\xff", "image/jpeg")], max_output_tokens=123)
    assert captured["contents"][0] == "variable text" and captured["contents"][1].inline_data is not None
    cfg = captured["config"]
    assert cfg.system_instruction == "STABLE" and cfg.max_output_tokens == 123
    assert str(cfg.thinking_config.thinking_level).endswith("MINIMAL")
    assert "HIGH" in str(cfg.media_resolution)
