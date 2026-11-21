"""Extended simulated dataset endpoints, chemist send, and the release fixes (struck-out lines, calibration, deadline)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import parsing
from app.catalogue import Catalogue
from app.gemini import GeminiClient, GeminiResult
from app.models import ModelOrderLine
from app.parsing import Upload, parse_order
from app.store import Reference
from tests.conftest import FIXTURES, REAL_DATA, make_settings, needs_real_data
from tests.test_gemini import api_error, live_client
from tests.test_parsing import CHEMIST, StubGemini

needs_extended = pytest.mark.skipif(not (REAL_DATA / "extended" / "orders.csv").exists(),
                                    reason="extended dataset not generated")
SAMPLES = REAL_DATA / "samples"


# ------------------------------------------------------------------ overview


@needs_real_data
@needs_extended
def test_overview_tiles_are_never_zero_and_are_labelled_simulated(client: TestClient) -> None:
    body = client.get("/api/overview").json()
    assert body["simulated"] is True and body["orders_30d"] > 1000 and body["lines_30d"] > body["orders_30d"]
    assert body["chemists_active"] > 50 and body["stockouts_14d"] > 0
    assert set(body["share_by_channel"]) == {"voice_note", "photo", "whatsapp_text", "salesman", "phone_call", "app"}
    assert abs(sum(body["share_by_channel"].values()) - 1) < 0.01
    assert body["avg_clerk_minutes_saved_per_order"] > 0 and "Estimate" in body["avg_clerk_minutes_saved_basis"]
    assert body["alerts_open"] >= 1 and body["alerts_confirmed"] == 0


@needs_real_data
@needs_extended
def test_overview_counts_a_live_approved_order(client: TestClient) -> None:
    before = client.get("/api/overview").json()["orders_30d"]
    sent = client.post("/api/chemist/send", data={"chemist_id": "CH002", "text": "dolo 650 10 strip"}).json()
    parsed = client.post("/api/orders/parse", data={"message_id": sent["message_id"]}).json()
    line = next(ln for ln in parsed["lines"] if ln["sku_id"])
    done = client.post("/api/orders", json={"chemist_id": "CH002", "message_id": sent["message_id"],
                                           "lines": [line], "approved_by": "Imran"})
    assert done.status_code == 200
    after = client.get("/api/overview").json()
    assert after["orders_30d"] == before + 1


def test_overview_degrades_without_extended_data(fixture_client: TestClient) -> None:
    response = fixture_client.get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["simulated"] is True and body["orders_30d"] == 0 and "not installed" in body["note"]


# ------------------------------------------------------------------ back-test


@needs_real_data
@needs_extended
def test_backtest_shape_and_honest_labels(client: TestClient) -> None:
    body = client.get("/api/backtest").json()
    assert body["simulated"] is True and "PROJECTED" in body["note"] and body["rule"]
    assert len(body["events"]) == 6
    first = body["events"][0]
    assert set(first) >= {"event", "pin", "group", "signal_first", "asha_rise", "official_date",
                          "lead_days_vs_official", "lead_days_vs_asha", "data_status"}
    assert {e["data_status"] for e in body["events"]} <= {"projected_sim", "observed_sim"}
    assert any(e["data_status"] == "projected_sim" for e in body["events"])
    assert any(e["asha_rise"] is None and e["lead_days_vs_asha"] is None for e in body["events"])
    assert len(body["false_alarms"]) == 5 and body["false_alarms"][0]["official_elevated"] is False
    assert len(body["missed"]) == 1 and body["missed"][0]["pin"] == "400017"
    assert body["missed"][0]["data_status"] == "observed_sim"
    assert body["median_lead_days_vs_official"] == 12.0 and body["median_lead_days_vs_asha"] == 2.0


@needs_real_data
@needs_extended
def test_backtest_filters_to_an_alerts_pins_and_group(client: TestClient) -> None:
    alert = next(a for a in client.get("/api/alerts").json() if a["group"] == "diarrhoea")
    body = client.get("/api/backtest", params={"alert_id": alert["alert_id"]}).json()
    assert body["filtered_by"]["alert_id"] == alert["alert_id"]
    assert body["events"] and all(e["group"] == "diarrhoea" and e["pin"] in alert["pins"] for e in body["events"])
    assert all(m["pin"] in alert["pins"] for m in body["missed"])
    assert client.get("/api/backtest", params={"alert_id": "nope-1"}).status_code == 404


def test_backtest_degrades_without_the_file(fixture_client: TestClient) -> None:
    body = fixture_client.get("/api/backtest").json()
    assert body["simulated"] is True and body["events"] == [] and "not found" in body["note"]


# --------------------------------------------------------------- environment


@needs_real_data
@needs_extended
def test_environment_returns_real_rows(client: TestClient) -> None:
    response = client.get("/api/environment", params={"pin": "400022", "days": 7})
    rows = response.json()
    assert len(rows) == 7 and rows == sorted(rows, key=lambda r: r["date"])
    assert set(rows[0]) == {"date", "temp_max", "temp_min", "precip_mm", "humidity", "pm25", "pm10", "source"}
    assert {r["source"] for r in rows} == {"open-meteo"} and "Real data" in response.headers["x-data-note"]
    assert client.get("/api/environment", params={"pin": "999999"}).status_code == 404
    assert client.get("/api/environment", params={"pin": "40"}).status_code == 422


def test_environment_degrades_without_the_file(fixture_client: TestClient) -> None:
    response = fixture_client.get("/api/environment", params={"pin": "400001"})
    assert response.status_code == 200 and response.json() == [] and "not installed" in response.headers["x-data-note"]


# ----------------------------------------------------- stock-outs and radar


@needs_real_data
@needs_extended
def test_stockouts_are_ranked_and_carry_cover(client: TestClient) -> None:
    rows = client.get("/api/stockouts", params={"days": 14}).json()
    assert rows and set(rows[0]) >= {"sku_id", "brand", "group", "pins", "chemists", "qty_wanted"}
    assert [r["chemists"] for r in rows] == sorted((r["chemists"] for r in rows), reverse=True)
    ors = next(r for r in rows if r["sku_id"] == "SKU0021")
    assert ors["days_of_cover"] == 0.0 and ors["group"] == "diarrhoea" and ors["pins"]
    short = client.get("/api/stockouts", params={"days": 1}).json()
    assert sum(r["chemists"] for r in short) < sum(r["chemists"] for r in rows)


@needs_real_data
@needs_extended
def test_live_not_available_mention_joins_the_stockouts(client: TestClient) -> None:
    before = {r["sku_id"]: r["chemists"] for r in client.get("/api/stockouts").json()}
    sent = client.post("/api/chemist/send", data={"chemist_id": "CH002", "text": "dolo 650 10 strip, electral nahi aaya"})
    mid = sent.json()["message_id"]
    client.post("/api/orders/parse", data={"message_id": mid})
    client.post("/api/orders/parse", data={"message_id": mid})  # parsing twice must not count twice
    after = {r["sku_id"]: r["chemists"] for r in client.get("/api/stockouts").json()}
    electral = "SKU0022"
    assert after[electral] >= before.get(electral, 0) + 0 and (after[electral] - before.get(electral, 0)) <= 1
    live = client.app.state.ctx.store.list_stockouts()  # type: ignore[attr-defined]
    assert len(live) == 1 and live[0]["sku_id"] == electral


@needs_real_data
@needs_extended
def test_radar_reasons_use_cover_and_stockouts(client: TestClient) -> None:
    radar = client.get("/api/radar").json()
    reasons = [s["reason"] for item in radar for s in item["skus"]]
    assert any("days of cover" in r and "asked last week" in r for r in reasons)
    ors = next(s for item in radar if item["group"] == "diarrhoea" for s in item["skus"] if s["sku_id"] == "SKU0021")
    assert ors["reason"].startswith("0 days of cover") and "already missed" in ors["reason"]
    assert ors["suggested_qty"] > 0


def test_radar_still_works_without_extended_data(fixture_client: TestClient) -> None:
    assert fixture_client.get("/api/radar").status_code == 200
    assert fixture_client.get("/api/stockouts").json() == []


# --------------------------------------------------------------- ASHA history


@needs_real_data
@needs_extended
def test_asha_history_is_continuous_and_adds_live_reports(client: TestClient) -> None:
    rows = client.get("/api/asha/history", params={"pin": "400022", "days": 10}).json()
    assert len(rows) == 10 and rows[-1]["date"] == "2026-11-19"
    assert set(rows[0]) == {"date", "households_visited", "fever", "diarrhoea", "cough", "referred", "reports"}
    assert rows[-1]["diarrhoea"] == 15 and rows[-1]["reports"] == 4  # equals the asha_reports.csv sums for that day
    assert client.get("/api/asha/history", params={"pin": "999999"}).status_code == 404

    asha = next(a for a in client.get("/api/asha").json() if a["pin"] == "400022")
    loc = next(x for x in client.get("/api/localities", params={"pin": "400022"}).json())
    posted = client.post("/api/asha/report", data={"asha_id": asha["asha_id"], "locality_id": loc["locality_id"],
                                                    "text": "visited 20 households, 4 diarrhoea cases"})
    assert posted.status_code == 200, posted.text
    live = client.get("/api/asha/history", params={"pin": "400022", "days": 3}).json()
    assert sum(r["diarrhoea"] for r in live) >= 4 and live[-1]["date"] >= "2026-11-19"
    assert sum(r["reports"] for r in live) >= 1


def test_asha_history_degrades_without_the_file(fixture_client: TestClient) -> None:
    response = fixture_client.get("/api/asha/history", params={"pin": "400001", "days": 3})
    assert response.status_code == 200 and "not installed" in response.headers["x-data-note"]
    assert all(r["reports"] == 0 for r in response.json())


# --------------------------------------------------------------- chemist send


@needs_real_data
def test_chemist_sends_a_voice_note_and_it_lands_in_the_inbox(client: TestClient, tmp_path: Path) -> None:
    audio = (SAMPLES / "order_01.mp3").read_bytes()
    sent = client.post("/api/chemist/send", data={"chemist_id": "CH002"}, files={"file": ("note.mp3", audio, "audio/mpeg")})
    assert sent.status_code == 200 and sent.json()["status"] == "new" and sent.json()["message_id"].startswith("msg_")
    mid = sent.json()["message_id"]
    inbox = client.get("/api/inbox").json()
    msg = next(m for m in inbox if m["id"] == mid)
    assert msg["status"] == "new" and msg["type"] == "voice" and msg["chemist"]["shop_name"] and len(inbox) == 11
    media = client.get(f"/api/media/{mid}")
    assert media.status_code == 200 and media.content == audio and media.headers["content-type"].startswith("audio/")
    assert client.get(f"/api/inbox/{mid}/media").content == audio
    assert (tmp_path / "media" / f"{mid}.mp3").read_bytes() == audio
    assert any(a["kind"] == "message_received" for a in client.get("/api/audit").json())
    # a bundled sample is served on the same route
    assert client.get("/api/media/msg_01").status_code == 200


@needs_real_data
def test_chemist_send_text_and_photo_and_validation(client: TestClient) -> None:
    text = client.post("/api/chemist/send", data={"chemist_id": "CH004", "text": "ors 25, electral 12"}).json()
    parsed = client.post("/api/orders/parse", data={"message_id": text["message_id"]}).json()
    assert parsed["lines"] and parsed["message_id"] == text["message_id"]
    assert client.get(f"/api/media/{text['message_id']}").status_code == 404   # a text message has no media

    photo = (SAMPLES / "order_05.jpg").read_bytes()
    sent = client.post("/api/chemist/send", data={"chemist_id": "CH021"}, files={"file": ("list.jpg", photo, "image/jpeg")})
    assert sent.status_code == 200
    assert next(m for m in client.get("/api/inbox").json() if m["id"] == sent.json()["message_id"])["type"] == "photo"

    fake = client.post("/api/chemist/send", data={"chemist_id": "CH004"}, files={"file": ("x.mp3", b"<html>no</html>", "audio/mpeg")})
    assert fake.status_code == 400 and fake.json()["error"]["code"] == "invalid_media"
    assert client.post("/api/chemist/send", data={"chemist_id": "CH004"}).status_code == 400
    assert client.post("/api/chemist/send", data={"chemist_id": "NOPE", "text": "x"}).status_code == 404
    assert client.get("/api/media/msg_nope").status_code == 404
    assert len(client.get("/api/inbox").json()) == 12  # only the two valid sends were added


@needs_real_data
def test_a_sent_message_survives_reset_cleanly(client: TestClient) -> None:
    client.post("/api/chemist/send", data={"chemist_id": "CH004", "text": "ors 25"})
    assert len(client.get("/api/inbox").json()) == 11
    assert client.post("/api/demo/reset").status_code == 200
    assert len(client.get("/api/inbox").json()) == 10


# ---------------------------------------------------- release fixes: struck out


def _order(payload: dict[str, Any], catalogue: Catalogue) -> Any:
    return parse_order(StubGemini(payload), catalogue, CHEMIST, upload=Upload(b"\xff\xd8\xffjpeg", "list.jpg"))  # type: ignore[arg-type]


def test_struck_through_line_is_never_green(fixture_catalogue: Catalogue) -> None:
    payload = {"language": "en", "transcript": "Dolo 650  10\nCrocin  4", "lines": [
        {"raw_text": "Dolo 650", "sku_id": "S1", "qty": 10, "unit": "strip", "confidence": 0.95},
        {"raw_text": "Crocin", "sku_id": "S3", "qty": 4, "unit": "strip", "confidence": 0.95, "struck_through": True}],
        "struck_out": []}
    parsed = _order(payload, fixture_catalogue)
    assert [ln.status for ln in parsed.lines] == ["matched", "unknown"]
    assert "Crossed out" in parsed.lines[1].reason and parsed.lines[1].sku_id is None


def test_item_listed_in_struck_out_is_demoted_even_if_the_model_also_returned_it(fixture_catalogue: Catalogue) -> None:
    payload = {"language": "en", "transcript": "x", "lines": [
        {"raw_text": "Dolo 650", "sku_id": "S1", "qty": 10, "unit": "strip", "confidence": 0.95},
        {"raw_text": "Crocin 4", "sku_id": "S3", "qty": 4, "unit": "strip", "confidence": 0.95}],
        "struck_out": ["Crocin 4"]}
    parsed = _order(payload, fixture_catalogue)
    assert parsed.struck_out == ["Crocin 4"]
    assert [ln.status for ln in parsed.lines] == ["matched", "unknown"]


def test_marker_text_in_a_line_is_demoted_and_cleaned(fixture_catalogue: Catalogue) -> None:
    payload = {"language": "en", "transcript": "x", "lines": [
        {"raw_text": "[struck out] Avil 25", "sku_id": None, "qty": 5, "confidence": 0.9}]}
    line = _order(payload, fixture_catalogue).lines[0]
    assert line.status == "unknown" and line.raw_text == "Avil 25"


def test_prompt_tells_the_model_to_report_struck_items_separately() -> None:
    assert "struck_out" in parsing.ORDER_SYSTEM and "CANCELLED" in parsing.ORDER_SYSTEM


@needs_real_data
def test_bundled_crossed_out_sample_reports_struck_out(client: TestClient) -> None:
    parsed = client.post("/api/orders/parse", data={"message_id": "msg_07"}).json()
    assert parsed["struck_out"] == ["Avil 25   5"] or parsed["struck_out"][0].startswith("Avil 25")
    assert all("avil" not in ln["raw_text"].lower() for ln in parsed["lines"])


# ------------------------------------------------- release fixes: calibration


@needs_real_data
@pytest.mark.parametrize("said,qty,unit,expected_sku", [
    ("ondem 4 ke 8 patte", 8, "strip", "SKU0027"),
    ("zinc 20 dt 15 strip", 15, "strip", "SKU0036"),
    ("bachchon wali ondem syrup 6 bottle", 6, "bottle", "SKU0028"),
    ("metrogyl 400 12 patta", 12, "strip", None),
    ("ors 30", 30, None, "SKU0021"),
    ("electral 10", 10, None, "SKU0022"),
    ("sporlac 10 sachet", 10, "sachet", None),
])
def test_clean_latin_brand_names_in_free_text_match_green(said: str, qty: int, unit: str | None,
                                                          expected_sku: str | None) -> None:
    catalogue = Catalogue(Reference.load(REAL_DATA).catalogue)
    for sku in (None, expected_sku):   # with and without the model naming the item
        line = catalogue.validate_line(ModelOrderLine(raw_text=said, sku_id=sku, qty=qty, unit=unit, confidence=0.9))
        assert line.status == "matched", (said, sku, line.reason)
        if expected_sku:
            assert line.sku_id == expected_sku


@needs_real_data
def test_calibration_still_flags_real_doubt() -> None:
    catalogue = Catalogue(Reference.load(REAL_DATA).catalogue)
    misspelt = catalogue.validate_line(ModelOrderLine(raw_text="crosin 30", qty=30, confidence=0.9))
    assert misspelt.status == "uncertain" and misspelt.reason
    wrong_strength = catalogue.validate_line(ModelOrderLine(raw_text="dolo 600", qty=10, confidence=0.9))
    assert wrong_strength.status != "matched"


@needs_real_data
def test_offline_free_text_parse_is_mostly_green(client: TestClient) -> None:
    sent = client.post("/api/chemist/send", data={"chemist_id": "CH004", "text": "ors 25, electral 12, ondem 4 8 strip"}).json()
    parsed = client.post("/api/orders/parse", data={"message_id": sent["message_id"]}).json()
    assert [ln["status"] for ln in parsed["lines"]].count("matched") == len(parsed["lines"]) == 3


# --------------------------------------------- release fixes: deadline and warm


def test_gemini_call_is_capped_by_the_request_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    seen: list[float | None] = []

    def fake_once(self: GeminiClient, model: str, *args: Any, **kw: Any) -> tuple[str, list, list]:
        seen.append(kw.get("timeout_s"))
        return "{}", [], []

    monkeypatch.setattr(GeminiClient, "_once", fake_once)
    from app.models import ModelOrderOut
    client.generate_structured(("m1",), "p", ModelOrderOut, deadline_s=25.0)
    assert seen[0] is not None and seen[0] <= 25.0


def test_slow_models_stop_at_the_deadline_instead_of_retrying_for_minutes(tmp_path: Path,
                                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    client = live_client(tmp_path, monkeypatch)
    calls: list[str] = []

    def always_504(self: GeminiClient, model: str, *args: Any, **kw: Any) -> None:
        calls.append(model)
        raise api_error(504)

    monkeypatch.setattr(GeminiClient, "_once", always_504)
    clock = {"t": 1000.0}
    monkeypatch.setattr("app.gemini.time.monotonic", lambda: clock["t"])
    monkeypatch.setattr("app.gemini.time.sleep", lambda s: clock.__setitem__("t", clock["t"] + s))
    from app.errors import UpstreamError
    from app.models import ModelOrderOut
    started = clock["t"]
    with pytest.raises(UpstreamError):
        client.generate_structured(("a", "b", "c"), "p", ModelOrderOut, deadline_s=3.0)
    assert clock["t"] - started <= 3.5 + 8.0 and len(calls) < 9   # a full chain would make 9 calls


class _SlowThenWarm(StubGemini):
    """Fails fast for the interactive call (deadline set), succeeds for the background warm."""

    def __init__(self) -> None:
        super().__init__({"language": "mr", "transcript": "t", "lines": []})
        self.deadlines: list[float | None] = []

    def generate_structured(self, models: Any, prompt: str, schema: Any, *, media: Any = (), system: str = "",
                            **kw: Any) -> GeminiResult:
        self.deadlines.append(kw.get("deadline_s"))
        if kw.get("deadline_s") == 25.0:
            from app.errors import UpstreamError
            raise UpstreamError("slow")
        return super().generate_structured(models, prompt, schema, media=media, system=system, **kw)


def test_a_slow_demo_sample_falls_back_fast_and_warms_in_the_background(fixture_ctx: Any) -> None:
    gemini = _SlowThenWarm()
    gemini.offline_samples = fixture_ctx.gemini.offline_samples
    expected = {"language": "mr", "transcript": "t", "notes": "orig", "lines": [
        {"raw_text": "crocin", "sku_id": "S3", "qty": 4, "unit": "strip", "confidence": 0.9}]}
    parsed = parse_order(gemini, fixture_ctx.catalogue, CHEMIST, upload=Upload(b"OggS-warm-test", "a.ogg"),  # type: ignore[arg-type]
                         expected_hint=expected)
    assert parsed.model == "offline-sample" and parsed.notes.startswith("Gemini was unavailable")
    for _ in range(100):
        if len(gemini.deadlines) >= 2 and not parsing._warming:
            break
        time.sleep(0.05)
    assert gemini.deadlines[0] == 25.0 and gemini.deadlines[1] == 150.0


def test_settings_carry_the_new_deadlines() -> None:
    settings = make_settings(Path("."), FIXTURES)
    assert settings.parse_deadline_s == 25.0 and settings.warm_deadline_s == 150.0


def test_json_note_header_is_ascii(fixture_client: TestClient) -> None:
    note = fixture_client.get("/api/stockouts").headers["x-data-note"]
    assert note.isascii() and json.dumps(note)
