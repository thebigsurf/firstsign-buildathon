"""Business operations behind the API: inbox, parsing, order approval, ASHA loop, approvals, metrics.

Design for blame: every approval, every clerk edit and every accepted uncertain line is written
to the audit log with who did it and when. Nothing is silently corrected.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from typing import Any

from .catalogue import Catalogue
from .config import MANUAL_MIN_PER_10_LINES, REVIEW_MIN_PER_10_LINES, Settings
from .errors import AppError, BadRequest, Conflict, NotFound
from .gemini import GeminiClient
from .models import (
    ActionApproved,
    ActionApproveRequest,
    Alert,
    AshaReportResult,
    Explanation,
    Metrics,
    OrderCreate,
    OrderLine,
    OrderRecord,
    ParsedOrder,
    VisitItem,
)
from .parsing import Upload, parse_asha_report, parse_order
from .signal import SignalService, report_delta
from .store import Reference, Store, new_id, utc_now

NOTES_MAX = 300


class Services:
    def __init__(self, settings: Settings, ref: Reference, store: Store, catalogue: Catalogue,
                 gemini: GeminiClient, signal: SignalService) -> None:
        self.settings, self.ref, self.store = settings, ref, store
        self.catalogue, self.gemini, self.signal = catalogue, gemini, signal

    # ------------------------------------------------------------------ inbox

    def inbox(self) -> list[dict[str, Any]]:
        approved = {o.get("message_id"): o["order_id"] for o in self.store.list_orders() if o.get("message_id")}
        out = []
        for msg in self.ref.inbox:
            parsed = self.store.get_parse(msg["id"])
            status = "approved" if msg["id"] in approved else "parsed" if parsed else "new"
            chemist = self.ref.chemist(msg.get("chemist_id", "")) or {}
            out.append({**msg, "status": status, "parsed": parsed, "order_id": approved.get(msg["id"]),
                        "chemist": {"shop_name": chemist.get("shop_name"), "owner_first_name": chemist.get("owner_first_name"),
                                    "pin": chemist.get("pin"), "language": chemist.get("language")} if chemist else None})
        return out

    # ---------------------------------------------------------------- parsing

    def parse_order(self, chemist_id: str | None, message_id: str | None, upload: Upload | None,
                    text: str | None) -> ParsedOrder:
        item = self.ref.inbox_item(message_id) if message_id else None
        if message_id and item is None and not upload and not text:
            raise NotFound("Inbox message", message_id)
        chemist_id = chemist_id or (item or {}).get("chemist_id")
        if not chemist_id:
            raise BadRequest("chemist_id is required.")
        chemist = self.ref.chemist(chemist_id)
        if chemist is None:
            raise NotFound("Chemist", chemist_id)

        expected_hint: dict[str, Any] | None = None
        if item and not upload and not text:
            if item.get("type") == "text":
                text = item.get("text")
            elif item.get("media"):
                path = self.ref.resolve_data_path(item["media"])
                if path is None:
                    raise NotFound("Sample file", item["media"])
                upload = Upload(data=path.read_bytes(), filename=path.name)
        if item and item.get("expected"):
            expected_path = self.ref.resolve_data_path(item["expected"])
            if expected_path is not None:
                expected_hint = json.loads(expected_path.read_text(encoding="utf-8"))

        parsed = parse_order(self.gemini, self.catalogue, chemist, message_id=message_id, upload=upload, text=text,
                             expected_hint=expected_hint)
        self.store.save_parse(message_id or f"chemist:{chemist_id}", parsed.model_dump())
        counts = {s: sum(1 for ln in parsed.lines if ln.status == s) for s in ("matched", "uncertain", "unknown")}
        self.store.log_parse({"at": utc_now(), "chemist_id": chemist_id, "message_id": message_id,
                              "lines": len(parsed.lines), "model": parsed.model, "latency_ms": parsed.latency_ms,
                              "cached": parsed.cached, **counts})
        return parsed

    # ----------------------------------------------------------------- orders

    def create_order(self, body: OrderCreate) -> str:
        chemist = self.ref.chemist(body.chemist_id)
        if chemist is None:
            raise NotFound("Chemist", body.chemist_id)
        if not body.lines:
            raise BadRequest("An order needs at least one line.")
        if body.message_id and any(o.get("message_id") == body.message_id for o in self.store.list_orders()):
            raise Conflict("This message already has an approved order.")
        final: list[OrderLine] = []
        for i, line in enumerate(body.lines, start=1):
            if self.catalogue.get(line.sku_id) is None:
                raise BadRequest(f"Line {i} ('{line.raw_text}') has no catalogue item. Pick one or remove the line.",
                                 code="line_without_sku")
            final.append(self.catalogue.enrich(line))

        original_lines = self._original_lines(body)
        order_id = new_id("ord")
        now = utc_now()
        record = OrderRecord(order_id=order_id, chemist_id=body.chemist_id, pin=chemist["pin"],
                             message_id=body.message_id, lines=final, approved_by=body.approved_by, created_at=now)
        self.store.add_order(record.model_dump())

        edits, accepted = self._audit_line_changes(order_id, body.approved_by, original_lines, final)
        units = sum(ln.qty for ln in final)
        self.store.add_audit(
            body.approved_by, "order_approved", order_id,
            f"Approved {len(final)} lines ({units} units) for {chemist['shop_name']}; {edits} edited, "
            f"{accepted} uncertain accepted as read.",
            detail={"chemist_id": body.chemist_id, "message_id": body.message_id, "lines": len(final), "units": units,
                    "edited_lines": edits, "uncertain_lines_accepted": accepted,
                    "ai_reading_found": original_lines is not None},
        )
        return order_id

    def _original_lines(self, body: OrderCreate) -> list[dict[str, Any]] | None:
        """The AI's reading to diff against: sent by the client, else the stored parse."""
        if body.original_lines is not None:
            return [ln.model_dump() for ln in body.original_lines]
        stored = self.store.get_parse(body.message_id or f"chemist:{body.chemist_id}")
        return stored.get("lines", []) if stored else None

    @staticmethod
    def _snap(line: dict[str, Any]) -> dict[str, Any]:
        keys = ("raw_text", "sku_id", "brand", "strength", "qty", "unit", "status", "confidence")
        return {k: line.get(k) for k in keys}

    def _audit_line_changes(self, order_id: str, actor: str, original: list[dict[str, Any]] | None,
                            final: list[OrderLine]) -> tuple[int, int]:
        """Compare approved lines with what the AI returned and log every difference (design for blame)."""
        if original is None:
            return 0, 0
        remaining = list(original)
        edits = accepted = 0
        for line in final:
            after = self._snap(line.model_dump())
            idx = next((i for i, o in enumerate(remaining) if o.get("raw_text") == line.raw_text), None)
            if idx is None:
                self.store.add_audit(actor, "line_added", order_id,
                                     f"Added '{line.raw_text}' as {line.brand} {line.strength}, qty {line.qty}.",
                                     after=after)
                edits += 1
                continue
            before = remaining.pop(idx)
            changed = [k for k in ("sku_id", "qty", "unit") if before.get(k) != getattr(line, k)]
            if changed:
                diff = ", ".join(f"{k} {before.get(k)} -> {getattr(line, k)}" for k in changed)
                self.store.add_audit(actor, "line_edited", order_id, f"'{line.raw_text}': {diff}",
                                     before=self._snap(before), after=after, detail={"changed": changed})
                edits += 1
            elif before.get("status") != "matched":
                pct = round(float(before.get("confidence") or 0) * 100)
                self.store.add_audit(
                    actor, "uncertain_accepted", order_id,
                    f"'{line.raw_text}' was {before.get('status')} ({pct}%) and was accepted as read: "
                    f"{line.brand} {line.strength}.",
                    before=self._snap(before), after=after)
                accepted += 1
        for gone in remaining:
            self.store.add_audit(actor, "line_removed", order_id,
                                 f"Removed '{gone.get('raw_text')}' (AI read it as {gone.get('brand') or 'unknown'}).",
                                 before=self._snap(gone))
            edits += 1
        return edits, accepted

    # ------------------------------------------------------------- ASHA loop

    def asha_report(self, asha_id: str, locality_id: str, upload: Upload | None, text: str | None) -> AshaReportResult:
        asha = self.ref.asha_by_id(asha_id)
        if asha is None:
            raise NotFound("ASHA worker", asha_id)
        locality = self.ref.locality(locality_id)
        if locality is None:
            raise NotFound("Locality", locality_id)
        if locality["pin"] != asha["pin"]:
            raise AppError(422, "wrong_area",
                           f"{locality['name']} is outside this ASHA's area (pin {asha['pin']}). "
                           "Pick a locality from her own visit list.")
        parsed = parse_asha_report(self.gemini, asha, upload=upload, text=text)
        report = parsed.report.model_copy(update={"notes": parsed.report.notes[:NOTES_MAX]})
        digest = hashlib.sha256(" ".join(report.transcript.lower().split()).encode("utf-8")).hexdigest()
        today = utc_now()[:10]
        for earlier in self.store.list_asha_reports():
            if (earlier["asha_id"], earlier["locality_id"], earlier.get("transcript_hash"),
                    str(earlier.get("created_at", ""))[:10]) == (asha_id, locality_id, digest, today):
                raise Conflict("This exact report was already submitted today for this locality; it was not counted twice.")

        pin = locality["pin"]
        before = {a.alert_id: a for a in self.signal.alerts() if pin in a.pins}
        report_id = new_id("rep")
        record = {"report_id": report_id, "asha_id": asha_id, "locality_id": locality_id,
                  "locality": locality["name"], "pin": pin, "created_at": utc_now(),
                  "transcript_hash": digest, **report.model_dump()}
        self.store.add_asha_report(record)

        updates: list[dict[str, Any]] = []
        for alert in self.signal.alerts():
            if pin not in alert.pins:
                continue
            old = before.get(alert.alert_id)
            updates.append({
                "alert_id": alert.alert_id, "group": alert.group, "group_label": alert.group_label,
                "old_confidence": old.confidence if old else alert.base_confidence,
                "new_confidence": alert.confidence, "old_status": old.status if old else "open",
                "new_status": alert.status, "delta": report_delta(alert.group, record),
            })
        updates.sort(key=lambda u: -abs(u["delta"]))
        moved = "; ".join(
            f"{u['group_label']} {round(u['old_confidence'] * 100)}% -> {round(u['new_confidence'] * 100)}%"
            for u in updates) or "no open alert covers this area"
        self.store.add_audit(
            asha_id, "asha_report", report_id,
            f"ASHA report from {locality['name']}: {report.households_visited} households visited; {moved}.",
            after=report.model_dump(exclude={"transcript"}),
            detail={"locality_id": locality_id, "pin": pin, "updates": [
                {k: u[k] for k in ("alert_id", "old_confidence", "new_confidence", "new_status")} for u in updates]},
        )
        primary = updates[0] if updates else None
        return AshaReportResult(
            **report.model_dump(), alert_id=primary["alert_id"] if primary else None,
            new_confidence=primary["new_confidence"] if primary else None, report_id=report_id,
            updates=updates, model=parsed.model, latency_ms=parsed.latency_ms,
        )

    def asha_visits(self, asha_id: str) -> list[dict[str, Any]]:
        asha = self.ref.asha_by_id(asha_id)
        if asha is None:
            raise NotFound("ASHA worker", asha_id)
        reported = {r["locality_id"] for r in self.store.list_asha_reports() if r["asha_id"] == asha_id}
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for approval in sorted(self.store.list_approvals(), key=lambda a: a["created_at"], reverse=True):
            if approval["action"] != "asha_visit_list":
                continue
            group = approval["alert_id"].rsplit("-", 1)[0]
            for visit in sorted(approval.get("visit_list", []), key=lambda v: v["priority"]):
                loc = self.ref.locality(visit["locality_id"])
                if not loc or loc["pin"] != asha["pin"] or visit["locality_id"] in seen:
                    continue
                seen.add(visit["locality_id"])
                out.append({**visit, "pin": loc["pin"], "alert_id": approval["alert_id"], "group": group,
                            "group_label": self.ref.group_label(group), "approved_by": approval["approved_by"],
                            "approved_at": approval["created_at"], "reported": visit["locality_id"] in reported})
        for rank, visit in enumerate(out, start=1):
            visit["priority"] = rank
        return out

    # ------------------------------------------------------- action approvals

    def approve_action(self, body: ActionApproveRequest) -> ActionApproved:
        self.signal.alert(body.alert_id)  # 404 if the alert no longer exists
        stored = self.store.get_explanation(body.alert_id)
        if stored is None:
            raise Conflict("Run the explanation for this alert first, so there is a draft to approve.")
        explanation = Explanation.model_validate(stored)
        visits: list[VisitItem] = []
        if body.action == "asha_visit_list":
            visits = explanation.actions.asha_visit_list
            original = "; ".join(f"{v.priority}. {v.name} ({v.landmark})" for v in visits)
        else:
            original = getattr(explanation.actions, body.action)
        final = (body.edited_text or "").strip() or original
        approval = ActionApproved(
            approval_id=new_id("apr"), alert_id=body.alert_id, action=body.action, approved_by=body.approved_by,
            created_at=utc_now(), text=final, edited=final != original, visit_list=visits,
        )
        self.store.add_approval(approval.model_dump())
        how = "after editing the draft" if approval.edited else "as drafted"
        self.store.add_audit(
            body.approved_by, "action_approved", body.alert_id,
            f"Approved {body.action.replace('_', ' ')} for {body.alert_id} {how}.",
            before={"text": original}, after={"text": final},
            detail={"action": body.action, "edited": approval.edited, "model": explanation.model},
        )
        return approval

    # ---------------------------------------------------------------- metrics

    def metrics(self) -> Metrics:
        log = self.store.parse_log()
        lines = sum(e["lines"] for e in log)

        def pct(n: float, d: float = lines) -> float:
            return round(100 * n / d, 1) if d else 0.0

        live = [e for e in log if not str(e["model"]).startswith("offline")] or log
        latencies = sorted(e["latency_ms"] for e in live)
        alerts = self.signal.alerts()
        decided = [a for a in alerts if a.asha_reports and a.status in {"confirmed", "dismissed"}]
        effects: dict[str, float] = {}
        for alert in alerts:
            for r in alert.reports:
                if abs(r.delta) >= abs(effects.get(r.report_id, 0.0)):
                    effects[r.report_id] = r.delta
        order_audits = [e for e in self.store.list_audit() if e["kind"] == "order_approved"]
        approved_lines = sum(e["detail"].get("lines", 0) for e in order_audits)
        edited_lines = sum(e["detail"].get("edited_lines", 0) for e in order_audits)
        saved = approved_lines / 10 * (MANUAL_MIN_PER_10_LINES - REVIEW_MIN_PER_10_LINES)
        return Metrics(
            orders_parsed=len(log), lines_parsed=lines,
            auto_matched_pct=pct(sum(e["matched"] for e in log)),
            uncertain_pct=pct(sum(e["uncertain"] for e in log)),
            unknown_pct=pct(sum(e["unknown"] for e in log)),
            avg_latency_ms=int(sum(e["latency_ms"] for e in log) / len(log)) if log else 0,
            latency_p50_ms=_percentile(latencies, 50), latency_p95_ms=_percentile(latencies, 95),
            asha_reports=len(self.store.list_asha_reports()),
            alerts_confirmed=sum(1 for a in alerts if a.status == "confirmed"),
            alerts_raised=sum(1 for a in alerts if a.level == "alert"),
            orders_approved=len(self.store.list_orders()),
            edit_rate_pct=pct(edited_lines, approved_lines),
            minutes_saved_est=round(saved, 1),
            alert_precision=(round(sum(1 for a in decided if a.status == "confirmed") / len(decided), 2)
                             if decided else None),
            reports_confirming=sum(1 for d in effects.values() if d > 0.2),
            reports_cancelling=sum(1 for d in effects.values() if d < -0.2),
            decoys_suppressed=len(self.signal.suppressed()),
            days_first_sign_to_action=self._days_to_action(alerts),
        )

    def _days_to_action(self, alerts: list[Alert]) -> float | None:
        """Mean days from an alert's first sign to its first approved action (wall-clock date of approval)."""
        started = {a.alert_id: date.fromisoformat(a.started) for a in alerts}
        first: dict[str, date] = {}
        for ap in sorted(self.store.list_approvals(), key=lambda x: x["created_at"]):
            if ap["alert_id"] in started and ap["alert_id"] not in first:
                first[ap["alert_id"]] = datetime.fromisoformat(ap["created_at"]).date()
        gaps = [max(0, (first[k] - started[k]).days) for k in first]
        return round(sum(gaps) / len(gaps), 1) if gaps else None


def _percentile(sorted_values: list[int], q: int) -> int:
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, max(0, math.ceil(q / 100 * len(sorted_values)) - 1))
    return int(sorted_values[idx])
