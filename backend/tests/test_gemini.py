"""Gemini wrapper behaviour with the SDK mocked: fallback chain, backoff, cache, grounding, offline samples."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import errors

from app.errors import UpstreamError
from app.gemini import GeminiClient, Media, extract_grounding, parse_json_text
from app.models import ModelOrderOut
from tests.conftest import FIXTURES, make_settings


def live_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kw: Any) -> GeminiClient:
    monkeypatch.setattr("app.gemini.time.sleep", lambda _s: None)
    settings = dataclasses.replace(make_settings(tmp_path, FIXTURES, **kw), gemini_api_key="test-key", demo_offline=False)
    return GeminiClient(settings)


def api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "message": "x"}})


def test_falls_back_to_next_model_after_503s_and_records_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        calls.append(model)
        if model == "m1":
            raise api_error(503)
        return '{"language": "hi", "lines": []}', [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    result = client.generate_structured(("m1", "m2"), "prompt", ModelOrderOut)
    assert result.model == "m2"
    assert calls == ["m1", "m1", "m1", "m2"]  # three attempts on m1, then the fallback
    assert client.telemetry()["fallbacks"] == 1
    assert client.telemetry()["by_model"] == {"m2": 1}


def test_non_retryable_error_skips_straight_to_next_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        calls.append(model)
        if model == "missing":
            raise api_error(404)
        return "{}", [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    assert client.generate_structured(("missing", "ok"), "p", ModelOrderOut).model == "ok"
    assert calls == ["missing", "ok"]


def test_all_models_failing_raises_upstream_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch, gemini_max_attempts=2)

    def always_429(self: GeminiClient, *args: Any, **kw: Any) -> None:
        raise api_error(429)

    monkeypatch.setattr(GeminiClient, "_once", always_429)
    with pytest.raises(UpstreamError):
        client.generate_structured(("a", "b"), "p", ModelOrderOut)
    assert client.telemetry()["errors"] == 1


def test_disk_cache_serves_second_call_without_calling_gemini(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    count = {"n": 0}

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        count["n"] += 1
        return '{"language": "en"}', [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    media = [Media(data=b"abc", mime_type="audio/ogg")]
    first = client.generate_structured(("m",), "p", ModelOrderOut, media=media)
    second = client.generate_structured(("m",), "p", ModelOrderOut, media=media)
    other = client.generate_structured(("m",), "p", ModelOrderOut, media=[Media(data=b"abd", mime_type="audio/ogg")])
    assert (count["n"], first.cached, second.cached, other.cached) == (2, False, True, False)
    assert second.latency_ms == first.latency_ms
    assert client.telemetry()["cache_hits"] == 1


def test_cache_key_depends_on_model_prompt_and_media() -> None:
    key = GeminiClient.cache_key
    audio = [Media(b"x", "audio/ogg")]
    base = key("m", "json", "p", "", "S", audio)
    assert base == key("m", "json", "p", "", "S", audio)
    variants = {
        base,
        key("n", "json", "p", "", "S", audio),
        key("m", "json", "q", "", "S", audio),
        key("m", "json", "p", "", "S", [Media(b"y", "audio/ogg")]),
    }
    assert len(variants) == 4


def test_grounding_sources_come_from_metadata_not_text() -> None:
    def chunk(uri: str, title: str | None) -> SimpleNamespace:
        return SimpleNamespace(web=SimpleNamespace(uri=uri, title=title, domain=None))

    meta = SimpleNamespace(
        grounding_chunks=[chunk("https://a.example/1", "A"), chunk("https://a.example/1", "A again"),
                          chunk("https://b.example/2", None)],
        web_search_queries=["q1"],
    )
    response = SimpleNamespace(candidates=[SimpleNamespace(grounding_metadata=meta)])
    sources, queries = extract_grounding(response)
    assert [s["url"] for s in sources] == ["https://a.example/1", "https://b.example/2"]
    assert sources[1]["title"] == "https://b.example/2" and queries == ["q1"]
    assert extract_grounding(SimpleNamespace(candidates=[])) == ([], [])


def test_parse_json_text_handles_fences_and_rejects_garbage() -> None:
    assert parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(UpstreamError):
        parse_json_text("not json")
    with pytest.raises(UpstreamError):
        parse_json_text("[1, 2]")


def test_offline_mode_refuses_live_calls_and_finds_samples_by_name_and_hash(tmp_path: Path) -> None:
    samples = tmp_path / "data" / "samples"
    samples.mkdir(parents=True)
    (samples / "order_x.expected.json").write_text('{"lines": []}', encoding="utf-8")
    (samples / "order_x.mp3").write_bytes(b"audio-bytes")
    settings = dataclasses.replace(make_settings(tmp_path, tmp_path / "data"), demo_offline=True)
    client = GeminiClient(settings)
    assert client.offline
    with pytest.raises(UpstreamError):
        client.generate_structured(("m",), "p", ModelOrderOut)
    assert client.offline_samples.lookup(filename="order_x.mp3") == {"lines": []}
    assert client.offline_samples.lookup(filename="renamed.mp3", data=b"audio-bytes") == {"lines": []}
    assert client.offline_samples.lookup(filename="unknown.mp3", data=b"other") is None


def test_a_timeout_moves_on_to_the_next_model_without_retrying(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    client = live_client(tmp_path, monkeypatch)
    calls: list[str] = []

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        calls.append(model)
        if model == "slow":
            raise httpx.ReadTimeout("timed out")
        return "{}", [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    assert client.generate_structured(("slow", "quick"), "p", ModelOrderOut).model == "quick"
    assert calls == ["slow", "quick"]


def test_quota_error_with_long_retry_info_skips_the_model_and_short_one_waits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.gemini import retry_delay_s

    def quota(delay: str) -> errors.APIError:
        return errors.APIError(429, {"error": {"code": 429, "details": [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": delay}]}})

    assert retry_delay_s(quota("91s")) == 91.0 and retry_delay_s(api_error(429)) is None
    sleeps: list[float] = []
    client = live_client(tmp_path, monkeypatch)
    monkeypatch.setattr("app.gemini.time.sleep", sleeps.append)
    calls: list[str] = []

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        calls.append(model)
        if model == "long":
            raise quota("91s")
        if model == "short" and calls.count("short") == 1:
            raise quota("2s")
        return "{}", [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    assert client.generate_structured(("long", "short"), "p", ModelOrderOut).model == "short"
    assert calls == ["long", "short", "short"] and sleeps == [2.0]


def test_grounding_quota_error_fails_fast_and_pauses_search(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    calls: list[str] = []

    def quota(self: GeminiClient, model: str, *args: Any, **kw: Any) -> None:
        calls.append(model)
        raise api_error(429)

    monkeypatch.setattr(GeminiClient, "_once", quota)
    with pytest.raises(UpstreamError):
        client.generate_grounded(("a", "b"), "news?")
    assert calls == ["a", "b"]                      # one try per model, no backoff loop
    with pytest.raises(UpstreamError, match="skipped"):
        client.generate_grounded(("a", "b"), "news again?")
    assert calls == ["a", "b"]                      # no further calls while paused


def test_a_model_that_rejects_the_thinking_setting_is_retried_with_its_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    seen: list[bool] = []

    def fake_once(self: GeminiClient, model: str, prompt: str, system: str, media: Any, temperature: float,
                  schema: Any, search: bool, fast: bool, **kw: Any) -> tuple[str, list, list]:
        seen.append(fast)
        if fast:
            raise errors.APIError(400, {"error": {"code": 400, "message": "Thinking level MINIMAL is not supported"}})
        return "{}", [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    assert client.generate_structured(("m",), "p", ModelOrderOut, fast=True).model == "m"
    assert seen == [True, False]
