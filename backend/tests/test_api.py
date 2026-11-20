"""API smoke tests with TestClient on the real seed data, DEMO_OFFLINE=1 (no network)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.store import LocalStore
from tests.conftest import REAL_DATA, make_settings, needs_real_data

pytestmark = needs_real_data


def test_health_and_reference_endpoints(client: TestClient) -> None:
    health = client.get("/api/health").json()
    assert health["status"] == "ok" and health["offline"] is True and health["storage"] == "local"
    assert health["model_fast"] and health["model_reason"]
    assert len(client.get("/api/catalogue").json()) > 100
    assert {g["id"] for g in client.get("/api/groups").json()} >= {"fever", "diarrhoea", "chronic_bp"}
    assert client.get("/api/pincodes").json() and client.get("/api/chemists").json()
    assert client.get("/api/distributor").json()["name"]
    assert client.get("/api/asha").json()
    assert all(x["pin"] == "400070" for x in client.get("/api/localities", params={"pin": "400070"}).json())


def test_every_error_has_the_same_json_shape(client: TestClient) -> None:
    missing = client.get("/api/alerts/not-there")
    assert missing.status_code == 404
    body = missing.json()["error"]
    assert body["code"] == "not_found" and body["request_id"] == missing.headers["X-Request-ID"]
    invalid = client.get("/api/signal", params={"days": 500})
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "validation_error"
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").json()["error"]["code"] in {"http_error", "not_found"}
    assert client.get("/api/health", headers={"X-Request-ID": "abc123"}).headers["X-Request-ID"] == "abc123"


def test_inbox_parse_approve_and_audit_flow(client: TestClient) -> None:
    inbox = client.get("/api/inbox").json()
    assert inbox and all(m["status"] == "new" for m in inbox)
    message = next(m for m in inbox if m["type"] == "voice")

    parsed = client.post("/api/orders/parse", data={"message_id": message["id"], "chemist_id": message["chemist_id"]})
    assert parsed.status_code == 200, parsed.text
    order = parsed.json()
    assert order["lines"] and order["model"] == "offline-sample" and order["transcript"]
    assert {ln["status"] for ln in order["lines"]} <= {"matched", "uncertain", "unknown"}
    assert client.get("/api/inbox").json()[0]["status"] == "parsed"

    lines = [ln for ln in order["lines"] if ln["sku_id"]]
    lines[0]["qty"] += 2                              # the clerk edits one quantity
    created = client.post("/api/orders", json={"chemist_id": order["chemist_id"], "message_id": message["id"],
                                               "lines": lines, "approved_by": "Aman"})
    assert created.status_code == 200, created.text
    assert created.json()["order_id"].startswith("ord_")
    assert client.get("/api/orders").json()[0]["approved_by"] == "Aman"
    assert client.get("/api/inbox").json()[0]["status"] == "approved"

    audit = client.get("/api/audit").json()
    kinds = {a["kind"] for a in audit}
    assert {"order_approved", "line_edited"} <= kinds
    edit = next(a for a in audit if a["kind"] == "line_edited")
    assert edit["actor"] == "Aman" and edit["before"]["qty"] + 2 == edit["after"]["qty"]

    again = client.post("/api/orders", json={"chemist_id": order["chemist_id"], "message_id": message["id"],
                                             "lines": lines, "approved_by": "Aman"})
    assert again.status_code == 409


def test_order_with_a_line_that_has_no_sku_is_refused(client: TestClient) -> None:
    chemist = client.get("/api/chemists").json()[0]["chemist_id"]
    bad = {"raw_text": "mystery tablet", "qty": 1}
    response = client.post("/api/orders", json={"chemist_id": chemist, "lines": [bad], "approved_by": "Aman"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "line_without_sku"
    assert client.post("/api/orders/parse", data={"chemist_id": "NOPE", "text": "x"}).status_code == 404
    assert client.post("/api/orders/parse", data={"chemist_id": chemist}).status_code == 400


def test_parse_an_uploaded_sample_file_by_hash(client: TestClient) -> None:
    sample = next((REAL_DATA / "samples").glob("order_0*.mp3"))
    response = client.post("/api/orders/parse", data={"chemist_id": "CH002"},
                           files={"file": ("renamed.mp3", sample.read_bytes(), "audio/mpeg")})
    assert response.status_code == 200 and response.json()["model"] == "offline-sample"


def test_signal_alerts_and_radar(client: TestClient) -> None:
    signal = client.get("/api/signal", params={"days": 30}).json()
    assert signal["as_of"] == "2026-11-19" and signal["simulated"] is True
    assert signal["suppressed"] and signal["cells"][0]["level"] == "alert"
    assert len(signal["cells"][0]["series"]) == 30
    alerts = client.get("/api/alerts").json()
    top = alerts[0]
    assert top["level"] == "alert" and top["status"] == "open" and top["reasons"] and 0 < top["confidence"] <= 0.9
    assert client.get(f"/api/alerts/{top['alert_id']}").json()["alert_id"] == top["alert_id"]
    radar = client.get("/api/radar").json()
    assert radar and radar[0]["skus"] and radar[0]["skus"][0]["suggested_qty"] >= 1


def test_explain_approve_report_visits_and_metrics_loop(client: TestClient) -> None:
    alert = next(a for a in client.get("/api/alerts").json() if a["group"] == "diarrhoea" and "400070" in a["pins"])
    explained = client.post("/api/agent/explain", json={"alert_id": alert["alert_id"]})
    assert explained.status_code == 200, explained.text
    plan = explained.json()
    assert plan["summary"] and plan["actions"]["asha_visit_list"] and plan["actions"]["officer_note"]
    assert client.post("/api/agent/explain", json={"alert_id": alert["alert_id"]}).json()["cached"] is True

    approved = client.post("/api/actions/approve", json={
        "alert_id": alert["alert_id"], "action": "officer_note", "approved_by": "Dr Mehta",
        "edited_text": "Edited note for the ward officer."})
    assert approved.status_code == 200 and approved.json()["edited"] is True
    client.post("/api/actions/approve", json={"alert_id": alert["alert_id"], "action": "asha_visit_list",
                                              "approved_by": "Dr Mehta"})

    visit = plan["actions"]["asha_visit_list"][0]
    locality = next(x for x in client.get("/api/localities").json() if x["locality_id"] == visit["locality_id"])
    asha = next(a for a in client.get("/api/asha").json() if a["pin"] == locality["pin"])
    visits = client.get("/api/asha/visits", params={"asha_id": asha["asha_id"]}).json()
    assert visits and visits[0]["reported"] is False and visits[0]["approved_by"] == "Dr Mehta"

    before = alert["confidence"]
    report = client.post("/api/asha/report", data={
        "asha_id": asha["asha_id"], "locality_id": visit["locality_id"],
        "text": "visited 30 households, 8 diarrhoea cases, 5 children affected, dirty water"})
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["diarrhoea"] == 8 and body["alert_id"] == alert["alert_id"] and body["new_confidence"] > before
    refreshed = client.get(f"/api/alerts/{alert['alert_id']}").json()
    assert refreshed["asha_reports"] == 1 and refreshed["status"] == "open"   # one visit never confirms alone

    payload = {"asha_id": asha["asha_id"], "locality_id": visit["locality_id"],
               "text": "visited 30 households, 8 diarrhoea cases, 5 children affected, dirty water"}
    assert client.post("/api/asha/report", data=payload).status_code == 409    # same report twice is not counted twice
    other = next(loc for loc in client.get("/api/localities").json() if loc["pin"] != asha["pin"])
    wrong = client.post("/api/asha/report", data={**payload, "locality_id": other["locality_id"]})
    assert wrong.status_code == 422

    metrics = client.get("/api/metrics").json()
    assert metrics["asha_reports"] == 1 and metrics["decoys_suppressed"] >= 1 and metrics["alerts_raised"] >= 1
    assert metrics["days_first_sign_to_action"] is not None
    kinds = {a["kind"] for a in client.get("/api/audit").json()}
    assert {"action_approved", "asha_report"} <= kinds


def test_approving_before_explaining_is_a_conflict(client: TestClient) -> None:
    alert_id = client.get("/api/alerts").json()[0]["alert_id"]
    response = client.post("/api/actions/approve", json={"alert_id": alert_id, "action": "officer_note",
                                                         "approved_by": "Dr Mehta"})
    assert response.status_code == 409


def test_telemetry_and_reset(client: TestClient) -> None:
    telemetry = client.get("/api/telemetry").json()
    assert telemetry["offline"] is True and telemetry["calls"] == 0
    client.post("/api/orders/parse", data={"chemist_id": "CH002", "text": "dolo 650 10 strip"})
    assert client.get("/api/metrics").json()["orders_parsed"] == 1
    assert client.post("/api/demo/reset").json() == {"status": "reset"}
    assert client.get("/api/metrics").json()["orders_parsed"] == 0


def test_state_survives_a_restart(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, REAL_DATA)
    with TestClient(create_app(settings, LocalStore(settings.state_file))) as first:
        first.post("/api/orders/parse", data={"chemist_id": "CH002", "text": "dolo 650 10 strip"})
        assert first.get("/api/metrics").json()["orders_parsed"] == 1
    with TestClient(create_app(settings, LocalStore(settings.state_file))) as second:
        assert second.get("/api/metrics").json()["orders_parsed"] == 1


def test_frontend_is_served_with_spa_fallback_when_built(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (dist / "assets" / "a.js").write_text("console.log(1)", encoding="utf-8")
    settings = make_settings(tmp_path, REAL_DATA, frontend_dist=dist)
    with TestClient(create_app(settings, LocalStore())) as c:
        assert c.get("/").text == "<html>app</html>"
        assert c.get("/officer/alert/diarrhoea-400070").text == "<html>app</html>"
        assert c.get("/assets/a.js").text == "console.log(1)"
        assert c.get("/api/health").json()["status"] == "ok"
        assert c.get("/api/unknown").status_code == 404
        assert c.get("/%2e%2e/%2e%2e/secret").text == "<html>app</html>"  # no path traversal out of dist


def test_root_returns_a_note_when_frontend_is_not_built(client: TestClient) -> None:
    body = client.get("/").json()
    assert "frontend has not been built" in body["note"]
