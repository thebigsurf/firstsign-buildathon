"""Signal maths: seeded events alert, the decoy does not, live orders count, ASHA reports move confidence."""

from __future__ import annotations

import pytest

from app.context import AppContext
from app.models import Alert, OrderCreate, OrderLine
from app.signal import (
    BACKGROUND_RATE,
    CONFIRM_AT,
    apply_reports,
    base_confidence,
    haversine_km,
    report_delta,
)
from tests.conftest import needs_real_data


def cell(ctx: AppContext, pin: str, group: str):
    return ctx.signal.snapshot.cells[(pin, group)]


def test_outbreak_pins_alert_and_cluster_into_one_alert(fixture_ctx: AppContext) -> None:
    assert cell(fixture_ctx, "400001", "diarrhoea").level == "alert"
    assert cell(fixture_ctx, "400002", "diarrhoea").level == "alert"
    alerts = [a for a in fixture_ctx.signal.alerts() if a.group == "diarrhoea"]
    assert len(alerts) == 1
    assert alerts[0].pins == ["400001", "400002"]
    assert alerts[0].level == "alert"
    assert alerts[0].alert_id == "diarrhoea-400001"
    assert alerts[0].ratio > 1.7


def test_decoy_bulk_order_does_not_alert_and_is_listed_as_suppressed(fixture_ctx: AppContext) -> None:
    decoy = cell(fixture_ctx, "400003", "diarrhoea")
    assert decoy.ratio > 1.7           # big volume...
    assert decoy.breadth < 0.2         # ...from one shop
    assert decoy.level == "normal"
    assert "concentrated_volume" in decoy.flags
    suppressed = fixture_ctx.signal.suppressed()
    assert [(s.pin, s.group) for s in suppressed] == [("400003", "diarrhoea")]
    assert not any("400003" in a.pins for a in fixture_ctx.signal.alerts())


def test_quiet_pin_stays_normal_everywhere(fixture_ctx: AppContext) -> None:
    levels = {c.level for (pin, _), c in fixture_ctx.signal.snapshot.cells.items() if pin == "400004"}
    assert levels == {"normal"}


def test_chronic_and_other_groups_never_alert(fixture_ctx: AppContext) -> None:
    for (_pin, group), c in fixture_ctx.signal.snapshot.cells.items():
        if group in {"chronic_bp", "other"}:
            assert c.level == "normal"


def test_signal_series_and_fields(fixture_ctx: AppContext) -> None:
    response = fixture_ctx.signal.signal(days=14)
    assert response.as_of == "2026-11-18"
    first = response.cells[0]
    assert len(first.series) == 14
    assert first.series[-1].date == "2026-11-18"
    assert response.simulated is True and "Simulated" in response.note
    assert response.cells[0].level == "alert"  # sorted most urgent first


def test_neighbour_distance_uses_haversine(fixture_ctx: AppContext) -> None:
    neighbours = fixture_ctx.signal.engine.neighbours
    assert "400002" in neighbours["400001"]
    assert "400003" not in neighbours["400001"]
    assert 0.9 < haversine_km(19.0, 72.8, 19.009, 72.8) < 1.1


def test_reasons_are_plain_words_and_explain_the_decision(fixture_ctx: AppContext) -> None:
    alert = fixture_ctx.signal.alert("diarrhoea-400001")
    text = " ".join(alert.reasons)
    assert "normal level" in text and "breadth" in text and "z-score" in text and "Chronic" in text
    assert alert.status == "open" and 0 < alert.confidence <= 0.9


def test_unknown_alert_is_not_found(fixture_ctx: AppContext) -> None:
    from app.errors import NotFound

    with pytest.raises(NotFound):
        fixture_ctx.signal.alert("nope-1")


def test_approved_live_orders_update_todays_counts(fixture_ctx: AppContext) -> None:
    before = cell(fixture_ctx, "400004", "fever").today
    line = fixture_ctx.catalogue.enrich(OrderLine(raw_text="dolo 650", sku_id="S1", qty=7, unit="strip", confidence=1))
    fixture_ctx.services.create_order(OrderCreate(chemist_id="C30", lines=[line], approved_by="Tester"))
    assert cell(fixture_ctx, "400004", "fever").today == before + 7


def test_confidence_formula_is_monotone() -> None:
    low = base_confidence(1.8, 3.0, 0.3, 1, 0)
    high = base_confidence(2.8, 8.0, 0.7, 3, 1)
    assert 0 < low < high <= 0.9
    assert base_confidence(1.0, 0.0, 0.0, 1, 0) < 0.1


def report(cases: int, households: int = 40, asha_id: str = "ASHA01", **kw) -> dict:
    return {"diarrhoea": cases, "households_visited": households, "asha_id": asha_id, **kw}


def test_report_above_background_raises_and_near_zero_lowers() -> None:
    assert report_delta("diarrhoea", report(7)) > 0.5
    assert report_delta("diarrhoea", report(0)) < -0.2
    assert report_delta("eye", report(7)) == 0.0           # cannot speak to this group
    assert report_delta("diarrhoea", report(3, water_issue_reported=True)) > report_delta("diarrhoea", report(3))


def test_status_rule_confirm_and_dismiss() -> None:
    conf, status, deltas = apply_reports(0.6, "diarrhoea", [report(8, water_issue_reported=True)])
    assert status == "open" and max(deltas) <= 1.0          # one visit alone never confirms
    conf, status, _ = apply_reports(0.6, "diarrhoea", [report(8, water_issue_reported=True), report(6, asha_id="ASHA02")])
    assert conf >= CONFIRM_AT and status == "confirmed"
    conf, status, _ = apply_reports(0.6, "diarrhoea", [report(0)])
    assert status == "open" and conf < 0.6                 # one near-zero report only lowers
    conf, status, _ = apply_reports(0.6, "diarrhoea", [report(0), report(0)])
    assert status == "dismissed"
    _, status, _ = apply_reports(0.6, "diarrhoea", [report(0), report(0), report(9)])
    assert status != "dismissed"                           # a raising report blocks dismissal


def test_background_rates_are_sensible() -> None:
    assert BACKGROUND_RATE["diarrhoea"] < BACKGROUND_RATE["respiratory"]


def test_asha_report_updates_confidence_and_status(fixture_ctx: AppContext) -> None:
    before = fixture_ctx.signal.alert("diarrhoea-400001")
    result = fixture_ctx.services.asha_report(
        "A1", "400001-01", None, "visited 30 households, 8 diarrhoea cases, 5 children, dirty water")
    after: Alert = fixture_ctx.signal.alert("diarrhoea-400001")
    assert result.alert_id == "diarrhoea-400001"
    assert result.new_confidence == after.confidence > before.confidence
    assert after.asha_reports == 1 and after.reports[0].effect == "raised"
    assert any("ASHA report" in r for r in after.reasons)


@needs_real_data
def test_backtest_on_seed_data(real_ctx: AppContext) -> None:
    """Both seeded events alert, the ORS decoy does not, and quiet pins raise no alert."""
    alerts = real_ctx.signal.alerts()
    diarrhoea_pins = {p for a in alerts if a.group == "diarrhoea" and a.level == "alert" for p in a.pins}
    fever_pins = {p for a in alerts if a.group == "fever" and a.level == "alert" for p in a.pins}
    assert {"400070", "400022"} <= diarrhoea_pins                     # Kurla and Sion/Chunabhatti
    assert fever_pins, "the dengue-like fever event must alert"
    decoy = real_ctx.signal.snapshot.cells[("400086", "diarrhoea")]
    assert decoy.level == "normal" and "concentrated_volume" in decoy.flags
    alerting_pins = {p for a in alerts if a.level == "alert" for p in a.pins}
    assert alerting_pins <= diarrhoea_pins | fever_pins                # nothing else alerts
    assert len(real_ctx.signal.suppressed()) >= 1


def test_radar_lists_alert_areas_first_line_stock_first_and_scales_with_demand(fixture_ctx: AppContext) -> None:
    radar = fixture_ctx.signal.radar()
    assert {(r.pin, r.group) for r in radar} == {("400001", "diarrhoea"), ("400002", "diarrhoea")}
    item = radar[0]
    assert item.level == "alert" and item.alert_id == "diarrhoea-400001"
    assert [s.sku_id for s in item.skus] == ["S4", "S5"]                  # oral rehydration salts, both first line
    assert item.skus[0].suggested_qty > item.skus[1].suggested_qty >= 1      # 40/30 weighting
    assert "days of cover" in item.skus[0].reason


def test_confirmation_needs_two_different_ashas_and_enough_households() -> None:
    same = [report(8, water_issue_reported=True), report(6)]                 # same ASHA twice
    conf, status, _ = apply_reports(0.6, "diarrhoea", same)
    assert conf >= CONFIRM_AT and status == "open"
    few = [report(4, households=12, water_issue_reported=True), report(4, households=12, asha_id="ASHA02", water_issue_reported=True)]
    conf, status, deltas = apply_reports(0.6, "diarrhoea", few)             # 24 households only
    assert min(deltas) > 0.2 and status == "open"
    ok = [report(4, households=15, water_issue_reported=True), report(4, households=15, asha_id="ASHA02", water_issue_reported=True)]
    assert apply_reports(0.6, "diarrhoea", ok)[1] == "confirmed"            # 30 households, over the 25 bar
    # a near-zero report from a second ASHA still lowers confidence and does not count towards confirming
    mixed = [report(8, water_issue_reported=True), report(0, asha_id="ASHA02")]
    conf_m, status_m, _ = apply_reports(0.6, "diarrhoea", mixed)
    assert status_m == "open" and conf_m < apply_reports(0.6, "diarrhoea", mixed[:1])[0]
