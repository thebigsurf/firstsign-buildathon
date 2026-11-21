"""The explain agent with Gemini mocked: grounding sources, locality validation, honest fallbacks, caching."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.agent import ExplainAgent
from app.context import AppContext
from app.errors import NotFound, UpstreamError
from app.gemini import GeminiResult

REASONING = {
    "summary": "Diarrhoea medicine orders are well above normal in Alpha Nagar and Beta Colony.",
    "likely_causes": [
        {"cause": "Possible water contamination", "evidence": "Ratio 2.8x with broad chemist participation.", "confidence": 0.6},
        {"cause": "Post-rain flooding", "evidence": "Found in a news item.", "confidence": 1.7},
    ],
    "distributor_note": "Stock ORS and Electral for Alpha Nagar and Beta Colony.",
    "officer_note": "Early signal only: please verify on the ground.",
    "asha_visit_list": [
        {"locality_id": "400002-01", "priority": 2, "reason": "Largest chawl block."},
        {"locality_id": "DOES-NOT-EXIST", "priority": 1, "reason": "Invented by the model."},
        {"locality_id": "400001-01", "priority": 3, "reason": "Water tank lane."},
    ],
}


class StubGemini:
    offline = False

    def __init__(self, search_sources: list[dict[str, str]], reasoning: dict[str, Any] | None = REASONING,
                 search_fails: bool = False) -> None:
        self.search_sources, self.reasoning, self.search_fails = search_sources, reasoning, search_fails
        self.settings = type("S", (), {"model_reason": ("reason-model",)})()
        self.calls = {"search": 0, "reason": 0}
        self.reason_prompt = ""

    def generate_grounded(self, models: Any, prompt: str, **kw: Any) -> GeminiResult:
        self.calls["search"] += 1
        if self.search_fails:
            raise UpstreamError("search down")
        return GeminiResult(text="Heavy rain on 12 Nov flooded low-lying lanes (Example News).", model="reason-model",
                            latency_ms=900, sources=self.search_sources, search_queries=["kurla flooding november"])

    def generate_structured(self, models: Any, prompt: str, schema: Any, **kw: Any) -> GeminiResult:
        self.calls["reason"] += 1
        self.reason_prompt = prompt
        if self.reasoning is None:
            raise UpstreamError("reasoning down")
        return GeminiResult(text=json.dumps(self.reasoning), model="reason-model", latency_ms=1500)


def agent_with(ctx: AppContext, stub: StubGemini) -> ExplainAgent:
    return ExplainAgent(stub, ctx.signal, ctx.store, ctx.ref)  # type: ignore[arg-type]


SOURCES = [{"title": "Example News", "url": "https://news.example/flood"}]


def test_grounded_explanation_uses_metadata_sources_and_our_numbers(fixture_ctx: AppContext) -> None:
    stub = StubGemini(SOURCES)
    result = agent_with(fixture_ctx, stub).explain("diarrhoea-400001")
    assert result.grounded and [s.url for s in result.sources] == ["https://news.example/flood"]
    assert result.search_queries == ["kurla flooding november"]
    assert result.latency_ms == 900 + 1500 and result.model == "reason-model"
    assert "Heavy rain on 12 Nov" in stub.reason_prompt and "decoy_check" in stub.reason_prompt
    assert "Alpha Nagar" in stub.reason_prompt or "400001" in stub.reason_prompt


def test_visit_list_keeps_only_real_localities_ranked_and_confidence_is_clamped(fixture_ctx: AppContext) -> None:
    result = agent_with(fixture_ctx, StubGemini(SOURCES)).explain("diarrhoea-400001")
    visits = result.actions.asha_visit_list
    assert [v.locality_id for v in visits][:2] == ["400002-01", "400001-01"]
    assert [v.priority for v in visits] == list(range(1, len(visits) + 1))
    assert len(visits) >= 3 and all(v.name and v.landmark for v in visits)
    assert "DOES-NOT-EXIST" not in {v.locality_id for v in visits}
    assert all(0 <= c.confidence <= 1 for c in result.likely_causes)


def test_no_sources_is_stated_honestly_but_reasoning_still_returns(fixture_ctx: AppContext) -> None:
    stub = StubGemini([])
    result = agent_with(fixture_ctx, stub).explain("diarrhoea-400001")
    assert result.grounded is False and result.sources == []
    assert "No external sources found" in result.search_note
    assert "NO EXTERNAL SOURCES WERE FOUND" in stub.reason_prompt
    assert result.summary


def test_search_failure_does_not_block_the_explanation(fixture_ctx: AppContext) -> None:
    result = agent_with(fixture_ctx, StubGemini([], search_fails=True)).explain("diarrhoea-400001")
    assert "No external sources found" in result.search_note and result.actions.officer_note


def test_reasoning_failure_falls_back_to_data_only_and_says_so(fixture_ctx: AppContext) -> None:
    result = agent_with(fixture_ctx, StubGemini(SOURCES, reasoning=None)).explain("diarrhoea-400001")
    assert result.model == "data-only-fallback" and "uses our data only" in result.search_note
    assert result.actions.asha_visit_list and "not a confirmed outbreak" in result.actions.officer_note


def test_result_is_cached_per_alert_and_refresh_recomputes(fixture_ctx: AppContext) -> None:
    stub = StubGemini(SOURCES)
    agent = agent_with(fixture_ctx, stub)
    first = agent.explain("diarrhoea-400001")
    second = agent.explain("diarrhoea-400001")
    assert (first.cached, second.cached, stub.calls) == (False, True, {"search": 1, "reason": 1})
    agent.explain("diarrhoea-400001", refresh=True)
    assert stub.calls == {"search": 2, "reason": 2}


def test_offline_mode_gives_a_labelled_data_only_explanation(fixture_ctx: AppContext) -> None:
    result = fixture_ctx.agent.explain("diarrhoea-400001")
    assert result.model == "offline-rules" and "Offline demo mode" in result.search_note and not result.sources


def test_unknown_alert_raises_not_found(fixture_ctx: AppContext) -> None:
    with pytest.raises(NotFound):
        fixture_ctx.agent.explain("fever-999999")


def test_reasoning_failure_reuses_the_last_good_explanation(fixture_ctx: AppContext, tmp_path: Any) -> None:
    good = StubGemini(SOURCES)
    good.settings = type("S", (), {"model_reason": ("reason-model",), "cache_dir": tmp_path})()
    first = agent_with(fixture_ctx, good).explain("diarrhoea-400001")
    assert first.model == "reason-model"
    down = StubGemini(SOURCES, reasoning=None)
    down.settings = good.settings
    again = agent_with(fixture_ctx, down).explain("diarrhoea-400001", refresh=True)
    assert again.model == "reason-model" and "Earlier Gemini explanation" in again.search_note
