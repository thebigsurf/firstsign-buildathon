"""Order and ASHA parsing with Gemini mocked, plus the offline readers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.context import AppContext
from app.errors import BadRequest, UpstreamError
from app.gemini import GeminiResult, SampleIndex
from app.parsing import (
    Upload,
    detect_mime,
    parse_asha_report,
    parse_order,
    rule_based_asha,
    rule_based_lines,
)

CHEMIST = {"chemist_id": "C00", "language": "hi"}


class StubGemini:
    """Stands in for GeminiClient on the live path."""

    offline = False

    def __init__(self, payload: dict[str, Any], model: str = "stub-model") -> None:
        self.payload, self.model = payload, model
        self.prompts: list[tuple[str, str, list[Any]]] = []
        self.settings = type("S", (), {"model_fast": ("stub-model",)})()
        self.offline_samples = SampleIndex(Path("no-such-samples-dir"))

    def generate_structured(self, models: Any, prompt: str, schema: Any, *, media: Any = (), system: str = "",
                            **kw: Any) -> GeminiResult:
        self.prompts.append((prompt, system, list(media)))
        return GeminiResult(text=json.dumps(self.payload), model=self.model, latency_ms=321)


def test_live_order_parse_sends_audio_inline_and_validates_against_catalogue(fixture_ctx: AppContext) -> None:
    gemini = StubGemini({
        "language": "hi", "transcript": "dolo 650 das patta, kuch aur cheez, electral nahi aaya",
        "lines": [
            {"raw_text": "dolo 650", "sku_id": "S1", "qty": 10, "unit": "strip", "confidence": 0.95},
            {"raw_text": "zzzz", "sku_id": "S777", "qty": 2, "confidence": 0.6},
        ],
        "not_available": ["electral"], "notes": "",
    })
    parsed = parse_order(gemini, fixture_ctx.catalogue, CHEMIST, message_id="m9",  # type: ignore[arg-type]
                         upload=Upload(b"OggS-bytes", "note.ogg", "audio/ogg"))
    assert [ln.status for ln in parsed.lines] == ["matched", "unknown"]
    assert parsed.not_available == ["electral"] and parsed.model == "stub-model" and parsed.latency_ms == 321
    prompt, system, media = gemini.prompts[0]
    assert media[0].mime_type == "audio/ogg" and media[0].data == b"OggS-bytes"
    assert "S1|Dolo 650" in prompt and "never invent" in system.lower()


def test_text_order_goes_in_the_prompt(fixture_ctx: AppContext) -> None:
    gemini = StubGemini({"lines": []})
    parse_order(gemini, fixture_ctx.catalogue, CHEMIST, text="dolo 650 10 strip")  # type: ignore[arg-type]
    assert "dolo 650 10 strip" in gemini.prompts[0][0] and gemini.prompts[0][2] == []


def test_empty_request_and_bad_files_are_rejected(fixture_ctx: AppContext) -> None:
    with pytest.raises(BadRequest):
        parse_order(StubGemini({}), fixture_ctx.catalogue, CHEMIST)  # type: ignore[arg-type]
    with pytest.raises(BadRequest):
        detect_mime(Upload(b"x", "notes.pdf"), ("audio", "image"))
    with pytest.raises(BadRequest):
        detect_mime(Upload(b"", "a.ogg"), ("audio",))
    assert detect_mime(Upload(bytes([0x1A, 0x45, 0xDF, 0xA3]), "blob", "audio/webm;codecs=opus"), ("audio",)) == "audio/webm"
    assert detect_mime(Upload(bytes([0xFF, 0xD8, 0xFF]), "p.JPG"), ("audio", "image")) == "image/jpeg"


def test_offline_rule_reader_extracts_qty_unit_and_not_available() -> None:
    out = rule_based_lines("dolo 650 10 strip, ors 20 sachet\npan d x5 and electral nahi aaya")
    assert [(ln.raw_text, ln.qty, ln.unit) for ln in out.lines] == [
        ("dolo 650", 10, "strip"), ("ors", 20, "sachet"), ("pan d", 5, None)]
    assert out.not_available == ["electral nahi aaya"]


def test_offline_text_order_end_to_end(fixture_ctx: AppContext) -> None:
    parsed = parse_order(fixture_ctx.gemini, fixture_ctx.catalogue, CHEMIST, text="dolo 650 10 strip, ors 20 sachet")
    assert parsed.model == "offline-rules"
    assert [ln.sku_id for ln in parsed.lines] == ["S1", "S4"]
    assert all(ln.qty for ln in parsed.lines)


def test_offline_unknown_media_returns_empty_with_a_note(fixture_ctx: AppContext) -> None:
    parsed = parse_order(fixture_ctx.gemini, fixture_ctx.catalogue, CHEMIST, upload=Upload(b"zz", "mystery.ogg"))
    assert parsed.lines == [] and "not one of the bundled samples" in parsed.notes


def test_offline_expected_hint_is_used_and_still_validated(fixture_ctx: AppContext) -> None:
    expected = {"language": "hi", "transcript": "t", "lines": [
        {"raw_text": "crocin", "sku_id": "S3", "qty": 4, "unit": "strip", "confidence": 0.9}]}
    parsed = parse_order(fixture_ctx.gemini, fixture_ctx.catalogue, CHEMIST, upload=Upload(b"OggS", "a.ogg"),
                         expected_hint=expected)
    assert parsed.model == "offline-sample" and parsed.lines[0].sku_id == "S3" and parsed.lines[0].qty == 4


def test_live_asha_report_uses_gemini_structure() -> None:
    payload = {"language": "hi", "transcript": "x", "households_visited": 14, "fever": 0, "diarrhoea": 5, "cough": 0,
               "breathing": 0, "rash": 0, "children_affected": 3, "referred": 1, "water_issue_reported": True,
               "notes": "n"}
    parsed = parse_asha_report(StubGemini(payload), {"language": "hi"},  # type: ignore[arg-type]
                               upload=Upload(b"OggS", "r.ogg", "audio/ogg"))
    assert parsed.report.diarrhoea == 5 and parsed.report.water_issue_reported and parsed.model == "stub-model"


def test_rule_based_asha_reads_numbers_next_to_symptoms() -> None:
    report = rule_based_asha("I visited 20 households. 6 diarrhoea cases and 2 fever. dirty water in the lane")
    assert (report.households_visited, report.diarrhoea, report.fever) == (20, 6, 2)
    assert report.water_issue_reported is True
    assert rule_based_asha("nothing to report").diarrhoea == 0


def test_real_expected_files_round_trip_through_the_catalogue(real_ctx: AppContext) -> None:
    """Every bundled sample's expected answer must validate back to its own SKUs (offline mode relies on it)."""
    samples = real_ctx.settings.data_dir / "samples"
    files = sorted(samples.glob("order_*.expected.json"))
    assert files
    for path in files:
        expected = json.loads(path.read_text(encoding="utf-8"))
        chemist = real_ctx.ref.chemist(expected["chemist_id"])
        assert chemist is not None
        parsed = parse_order(real_ctx.gemini, real_ctx.catalogue, chemist, text="x", expected_hint=expected)
        assert parsed.lines, path.name
        wrong = [(ln.raw_text, ln.sku_id) for ln, want in zip(parsed.lines, expected["lines"], strict=False)
                 if want.get("sku_id") and ln.sku_id != want["sku_id"]]
        assert not wrong, f"{path.name}: {wrong}"


class DownGemini(StubGemini):
    """Gemini that is unavailable for every call, but still knows the bundled samples."""

    def __init__(self, samples: Any) -> None:
        super().__init__({})
        self.offline_samples = samples

    def generate_structured(self, *args: Any, **kwargs: Any) -> GeminiResult:
        raise UpstreamError("all models failed")


def test_gemini_down_on_a_demo_sample_falls_back_to_the_prerecorded_reading_and_says_so(fixture_ctx: AppContext) -> None:
    down = DownGemini(fixture_ctx.gemini.offline_samples)
    expected = {"language": "hi", "transcript": "t", "notes": "orig", "lines": [
        {"raw_text": "crocin", "sku_id": "S3", "qty": 4, "unit": "strip", "confidence": 0.9}]}
    parsed = parse_order(down, fixture_ctx.catalogue, CHEMIST, upload=Upload(b"OggS", "a.ogg"),  # type: ignore[arg-type]
                         expected_hint=expected)
    assert parsed.model == "offline-sample" and parsed.latency_ms == 0
    assert parsed.notes.startswith("Gemini was unavailable") and parsed.lines[0].sku_id == "S3"
    with pytest.raises(UpstreamError):   # not a known sample: the failure must surface, not be faked
        parse_order(down, fixture_ctx.catalogue, CHEMIST, text="dolo 650 10")  # type: ignore[arg-type]


def test_fake_media_is_rejected_before_any_gemini_call() -> None:
    for name in ("fake.mp3", "fake.jpg", "fake.ogg"):
        with pytest.raises(BadRequest) as exc:
            detect_mime(Upload(b"<html>not media</html>", name), ("audio", "image"))
        assert exc.value.code == "invalid_media"


def test_lines_the_model_admits_interpreting_are_not_green() -> None:
    from app.models import OrderLine
    from app.parsing import _flag_interpreted

    def green(raw: str) -> OrderLine:
        return OrderLine(raw_text=raw, sku_id="S1", qty=1, confidence=0.95, status="matched")

    notes = "Interpreted 'pan' as Pan 40. 'patta' translated to strip."
    out = _flag_interpreted([green("pan 20 patta"), green("pantop d 5"), green("dolo 650 patta")], notes)
    assert [x.status for x in out] == ["uncertain", "matched", "matched"]
    assert "interpret" in (out[0].reason or "")


def test_unplaced_words_warn_the_clerk() -> None:
    from app.models import ModelOrderOut
    from app.parsing import _missing_line_warning

    warning = _missing_line_warning(ModelOrderOut(unplaced=["electral 15"]), 4)
    assert "electral 15" in warning and "missing" in warning
    assert _missing_line_warning(ModelOrderOut(transcript="ors 10", unplaced=[]), 1) == ""


def test_offline_bundled_sample_keeps_the_designed_green_yellow_red_story(client) -> None:
    body = client.post("/api/orders/parse", data={"message_id": "msg_02", "chemist_id": "CH020"}).json()
    statuses = [(ln["raw_text"], ln["status"]) for ln in body["lines"]]
    assert body["model"] == "offline-sample"
    assert statuses[0] == ("pan dee", "uncertain") and statuses[-1][1] == "unknown"
    assert body["lines"][-1]["sku_id"] is None
    assert sum(1 for _, s in statuses if s == "matched") == 4
