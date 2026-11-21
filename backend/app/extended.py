"""Extended simulated dataset (data/extended) behind the overview, back-test, environment, stock-out and ASHA-history
endpoints, and the sharper stock radar.

Everything loads lazily on first use and degrades honestly: a missing or unreadable file gives an empty result and a
plain-language note, never an exception. Only environment_daily.csv is real (Open-Meteo); the rest is SIMULATED and
is labelled that way in every response.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .config import MANUAL_MIN_PER_10_LINES, REVIEW_MIN_PER_10_LINES, Settings

log = logging.getLogger("firstsign.extended")

CHANNELS = ("voice_note", "photo", "whatsapp_text", "salesman", "phone_call", "app")
READ_BY_FIRSTSIGN = ("voice_note", "photo", "whatsapp_text")  # channels where Gemini replaces re-typing
SIM_NOTE = "Simulated data for the demo."
MISSING_NOTE = "Extended simulated data is not installed on this server (data/extended); showing live demo data only."


def _clean(value: Any) -> Any:
    """JSON-safe scalar: NaN and numpy types become None or plain Python."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


class ExtendedData:
    """Lazy, thread-safe access to data/extended/*.csv and backtest_summary.json."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.dir: Path = settings.data_dir / "extended"
        self._frames: dict[str, pd.DataFrame | None] = {}
        self._json: dict[str, Any] | None = None
        self._json_loaded = False
        self._lock = threading.RLock()
        self._as_of: date | None = None

    # ----------------------------------------------------------------- loading

    @property
    def available(self) -> bool:
        return self.dir.is_dir()

    def frame(self, name: str) -> pd.DataFrame | None:
        """A CSV as a DataFrame (strings kept as strings), or None if missing or unreadable."""
        with self._lock:
            if name not in self._frames:
                path = self.dir / f"{name}.csv"
                try:
                    frame = pd.read_csv(path, dtype={"pin": str, "sku_id": str, "chemist_id": str}, encoding="utf-8-sig")
                except (OSError, ValueError, pd.errors.ParserError) as exc:
                    log.warning("extended file %s.csv unavailable (%s)", name, type(exc).__name__)
                    frame = None
                self._frames[name] = frame
            return self._frames[name]

    def backtest_json(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._json_loaded:
                try:
                    self._json = json.loads((self.dir / "backtest_summary.json").read_text(encoding="utf-8-sig"))
                except (OSError, ValueError):
                    log.warning("backtest_summary.json unavailable")
                    self._json = None
                self._json_loaded = True
            return self._json

    @property
    def as_of(self) -> date:
        """The last day of the simulated window (the demo's 'today'), or DEMO_AS_OF if set."""
        with self._lock:
            if self._as_of is None:
                if self.settings.demo_as_of:
                    self._as_of = date.fromisoformat(self.settings.demo_as_of)
                else:
                    best: date | None = None
                    for name, col in (("orders", "received_at"), ("asha_reports", "date"), ("not_available_log", "date")):
                        frame = self.frame(name)
                        if frame is not None and len(frame):
                            best = date.fromisoformat(str(frame[col].max())[:10])
                            break
                    self._as_of = best or date.today()
            return self._as_of

    def _window(self, days: int) -> tuple[date, date]:
        end = self.as_of
        return end - timedelta(days=days - 1), end

    # ---------------------------------------------------------------- overview

    def overview(self, live_orders: list[dict[str, Any]], live_channel_of: dict[str, str], alerts_open: int,
                 alerts_confirmed: int) -> dict[str, Any]:
        """Landing-page tiles: 30 days of simulated history plus whatever has been approved live."""
        notes = [SIM_NOTE]
        counts = dict.fromkeys(CHANNELS, 0)
        orders_n = lines_n = 0
        chemists: set[str] = set()
        saved_total, saved_n = 0.0, 0

        orders, lines = self.frame("orders"), self.frame("order_lines")
        if orders is not None and lines is not None:
            start, end = self._window(30)
            day = orders["received_at"].astype(str).str[:10]
            sel = orders[(day >= start.isoformat()) & (day <= end.isoformat())]
            orders_n = len(sel)
            chemists |= set(sel["chemist_id"])
            per_order = lines[lines["order_id"].isin(set(sel["order_id"]))].groupby("order_id").size()
            lines_n = int(per_order.sum())
            for ch, n in sel["channel"].value_counts().items():
                if ch in counts:
                    counts[ch] += int(n)
            read = sel[sel["channel"].isin(READ_BY_FIRSTSIGN)]
            if len(read):
                review = per_order.reindex(read["order_id"]).fillna(0).to_numpy() / 10 * REVIEW_MIN_PER_10_LINES
                saved = read["clerk_minutes_estimate"].to_numpy() - review
                saved_total, saved_n = float(saved.sum()), len(read)
        else:
            notes.append(MISSING_NOTE)

        for order in live_orders:  # approved in this session, on top of the simulated history
            orders_n += 1
            lines_n += len(order.get("lines", []))
            chemists.add(order.get("chemist_id", ""))
            channel = live_channel_of.get(order.get("message_id") or "", "app")
            counts[channel] = counts.get(channel, 0) + 1

        total = sum(counts.values()) or 1
        return {
            "orders_30d": orders_n,
            "lines_30d": lines_n,
            "chemists_active": len(chemists - {""}),
            "share_by_channel": {ch: round(counts[ch] / total, 3) for ch in CHANNELS},
            "stockouts_14d": len(self._stockout_skus(14)),
            "stockout_events_14d": self._stockout_events(14),
            "avg_clerk_minutes_saved_per_order": round(saved_total / saved_n, 1) if saved_n else 0.0,
            "avg_clerk_minutes_saved_basis": (
                "Estimate: simulated manual re-typing minutes for voice, photo and text orders minus "
                f"{REVIEW_MIN_PER_10_LINES} min per 10 lines to review them (manual baseline "
                f"{MANUAL_MIN_PER_10_LINES} min per 10 lines)."),
            "alerts_open": alerts_open,
            "alerts_confirmed": alerts_confirmed,
            "window_days": 30,
            "as_of": self.as_of.isoformat(),
            "simulated": True,
            "note": " ".join(notes),
        }

    # ---------------------------------------------------------------- stock-outs

    def _not_available(self, days: int) -> pd.DataFrame | None:
        frame = self.frame("not_available_log")
        if frame is None:
            return None
        start, end = self._window(days)
        return frame[(frame["date"] >= start.isoformat()) & (frame["date"] <= end.isoformat())]

    def _stockout_skus(self, days: int) -> set[str]:
        sel = self._not_available(days)
        return set(sel["sku_id"]) if sel is not None else set()

    def _stockout_events(self, days: int) -> int:
        sel = self._not_available(days)
        return int(len(sel)) if sel is not None else 0

    def stockouts(self, days: int, live: list[dict[str, Any]], catalogue: Any) -> tuple[list[dict[str, Any]], str]:
        """Not-available lines by SKU: simulated log plus live 'not available' mentions that matched a catalogue item."""
        agg: dict[str, dict[str, Any]] = {}

        def bucket(sku_id: str) -> dict[str, Any] | None:
            sku = catalogue.get(sku_id)
            if sku is None:
                return None
            return agg.setdefault(sku_id, {"sku_id": sku_id, "brand": f"{sku.brand} {sku.strength}".strip(),
                                           "group": sku.group, "pins": set(), "chemist_ids": set(), "qty_wanted": 0})

        sel = self._not_available(days)
        note = SIM_NOTE
        if sel is None:
            note = MISSING_NOTE
        else:
            for sku_id, rows in sel.groupby("sku_id"):
                b = bucket(str(sku_id))
                if b is None:
                    continue
                b["pins"] |= set(rows["pin"].astype(str))
                b["chemist_ids"] |= set(rows["chemist_id"])
                b["qty_wanted"] += int(rows["qty_wanted"].sum())
        for item in live:
            b = bucket(item.get("sku_id") or "")
            if b is None:
                continue
            b["pins"].add(str(item.get("pin", "")))
            b["chemist_ids"].add(item.get("chemist_id", ""))
            b["qty_wanted"] += int(item.get("qty_wanted") or 0)

        cover = self.cover_by_sku()
        out = [{"sku_id": b["sku_id"], "brand": b["brand"], "group": b["group"], "pins": sorted(p for p in b["pins"] if p),
                "chemists": len(b["chemist_ids"] - {""}), "qty_wanted": b["qty_wanted"],
                "days_of_cover": cover.get(b["sku_id"])} for b in agg.values()]
        out.sort(key=lambda r: (-r["chemists"], -r["qty_wanted"], r["sku_id"]))
        return out, note

    def cover_by_sku(self) -> dict[str, float]:
        """Days of cover at the distributor on the last day of data, per SKU."""
        frame = self.frame("distributor_stock")
        if frame is None or not len(frame):
            return {}
        last = frame[frame["date"] == frame["date"].max()]
        return {str(r.sku_id): float(r.days_of_cover) for r in last.itertuples()}

    def asked_by_sku_pin(self, days: int, live: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, int]]:
        """(pin, sku) -> chemists who asked and units they were short of, over the last `days` days."""
        out: dict[tuple[str, str], dict[str, Any]] = {}
        sel = self._not_available(days)
        if sel is not None:
            for (pin, sku_id), rows in sel.groupby(["pin", "sku_id"]):
                out[(str(pin), str(sku_id))] = {"chemists": set(rows["chemist_id"]), "short": int(rows["qty_short"].sum())}
        for item in live:
            slot = out.setdefault((str(item.get("pin", "")), item.get("sku_id") or ""), {"chemists": set(), "short": 0})
            slot["chemists"].add(item.get("chemist_id", ""))
            slot["short"] += int(item.get("qty_wanted") or 0)
        return {k: {"chemists": len(v["chemists"]), "short": v["short"]} for k, v in out.items()}

    # --------------------------------------------------------------------- ASHA

    def asha_history(self, pin: str | None, days: int, live: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        """Daily ASHA totals for a pin (or all pins): simulated reports plus live ones filed in the app."""
        frame = self.frame("asha_reports")
        note = SIM_NOTE if frame is not None else MISSING_NOTE
        start, end = self._window(days)
        cols = ["households_visited", "fever", "diarrhoea", "cough", "referred"]
        daily: dict[str, dict[str, int]] = {}

        def add(day: str, row: dict[str, Any]) -> None:
            slot = daily.setdefault(day, {**dict.fromkeys(cols, 0), "reports": 0})
            for c in cols:
                slot[c] += int(row.get(c) or 0)
            slot["reports"] += 1

        if frame is not None:
            sel = frame[(frame["date"] >= start.isoformat()) & (frame["date"] <= end.isoformat())]
            if pin:
                sel = sel[sel["pin"].astype(str) == pin]
            for rec in sel.to_dict("records"):
                add(str(rec["date"])[:10], rec)
        last = end
        for report in live:
            if pin and str(report.get("pin")) != pin:
                continue
            day = str(report.get("created_at", ""))[:10]
            if day and day >= start.isoformat():
                add(day, report)
                last = max(last, date.fromisoformat(day))
        out = []
        cursor = start
        while cursor <= last:
            key = cursor.isoformat()
            out.append({"date": key, **daily.get(key, {**dict.fromkeys(cols, 0), "reports": 0})})
            cursor += timedelta(days=1)
        return out, note

    # -------------------------------------------------------------- environment

    def environment(self, pin: str, days: int, nearest_pin: Any) -> tuple[list[dict[str, Any]], str]:
        """REAL Open-Meteo weather and air quality for the pin's nearest grid point."""
        frame = self.frame("environment_daily")
        if frame is None:
            return [], "Real weather and air-quality file (Open-Meteo) is not installed on this server."
        have = set(frame["pin"].astype(str))
        use = pin if pin in have else nearest_pin(pin, have)
        if use is None:
            return [], "No weather data for this area."
        start, end = self._window(days)
        sel = frame[(frame["pin"].astype(str) == use) & (frame["date"] >= start.isoformat())
                    & (frame["date"] <= end.isoformat())].sort_values("date")
        rows = [{"date": str(r.date), "temp_max": _clean(r.temp_max_c), "temp_min": _clean(r.temp_min_c),
                 "precip_mm": _clean(r.precip_mm), "humidity": _clean(r.humidity_pct), "pm25": _clean(r.pm2_5),
                 "pm10": _clean(r.pm10), "source": str(r.source)} for r in sel.itertuples()]
        note = "Real data: Open-Meteo weather and air quality, nearest grid point."
        if use != pin:
            note += f" No grid row for {pin}; showing the nearest pin {use}."
        return rows, note

    # ----------------------------------------------------------------- back-test

    def backtest(self, pins: set[str] | None = None, group: str | None = None) -> dict[str, Any]:
        """The simulated back-test, flattened to one row per event and pin. Filtered to an alert's pins and group."""
        data = self.backtest_json()
        base = {"simulated": True, "note": "", "rule": "", "events": [], "false_alarms": [], "missed": [],
                "decoys": [], "median_lead_days_vs_official": None, "median_lead_days_vs_asha": None}
        if data is None:
            base["note"] = "Back-test file not found on this server. " + SIM_NOTE
            return base

        def keep(pin: str, grp: str) -> bool:
            return (pins is None or pin in pins) and (group is None or grp == group)

        events = []
        for ev in data.get("events", []):
            for p in ev.get("per_pin", []):
                pin = str(p.get("pin"))
                if not keep(pin, ev.get("group", "")):
                    continue
                events.append({
                    "event": ev.get("event"), "pin": pin, "area": p.get("area", ""), "group": ev.get("group"),
                    "signal_first": p.get("pharmacy_alert_date"), "asha_rise": p.get("asha_rise_date"),
                    "official_date": p.get("official_report_date"),
                    "lead_days_vs_official": p.get("lead_vs_official_report_date_days"),
                    "lead_days_vs_asha": p.get("lead_vs_asha_days"),
                    "data_status": "projected_sim" if p.get("official_projected") else "observed_sim",
                })
        fa = data.get("false_alarm") or {}
        false_alarms = [{
            "pin": str(p.get("pin")), "group": fa.get("group"), "alert_date": p.get("alert_date"),
            "official_elevated": p.get("official_elevated"), "asha_rise": p.get("asha_cough_rise_date"),
            "cause": fa.get("cause"), "verdict": fa.get("verdict"), "data_status": "observed_sim",
        } for p in fa.get("pins_alerting", []) if keep(str(p.get("pin")), fa.get("group", ""))]
        miss = data.get("missed_event")
        missed = []
        if miss:
            m = re.search(r"\b(\d{6})\b", str(miss.get("event", "")))
            pin = m.group(1) if m else ""
            if keep(pin, "fever"):
                missed.append({
                    "event": miss.get("event"), "pin": pin, "group": "fever",
                    "official_first_elevated_week_start": miss.get("official_first_elevated_week_start"),
                    "official_date": miss.get("official_report_date"),
                    "peak_typhoid_lab_positivity_pct": miss.get("peak_typhoid_lab_positivity_pct"),
                    "pharmacy_fever_peak_ratio": miss.get("pharmacy_fever_peak_ratio_in_window"),
                    "why_missed": miss.get("why_missed"), "data_status": "observed_sim",
                })
        decoy = data.get("decoy_ors_scheme")
        decoys = [{"pin": str(decoy.get("pin")), "chemist_id": decoy.get("chemist"), "scheme_id": decoy.get("scheme_id"),
                   "peak_7d_ratio": decoy.get("peak_7d_ratio"), "peak_breadth": decoy.get("peak_breadth"),
                   "alert_fired": decoy.get("alert_fired"), "note": decoy.get("note")}
                  ] if decoy and (pins is None or str(decoy.get("pin")) in pins) and group in (None, "fever", "diarrhoea") else []

        def median(values: list[int]) -> float | None:
            ordered = sorted(values)
            if not ordered:
                return None
            mid = len(ordered) // 2
            return float(ordered[mid]) if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2

        return {
            "simulated": True,
            "note": data.get("caveat") or SIM_NOTE,
            "rule": data.get("rule", ""),
            "events": events, "false_alarms": false_alarms, "missed": missed, "decoys": decoys,
            "median_lead_days_vs_official": median([e["lead_days_vs_official"] for e in events
                                                    if e["lead_days_vs_official"] is not None]),
            "median_lead_days_vs_asha": median([e["lead_days_vs_asha"] for e in events
                                                if e["lead_days_vs_asha"] is not None]),
        }


def nearest_pin_factory(pincodes: list[dict[str, Any]]) -> Any:
    """Return f(pin, candidates) -> the candidate pin closest to `pin` on the map, or None."""
    by_code = {p["pin"]: p for p in pincodes}

    def nearest(pin: str, candidates: set[str]) -> str | None:
        here = by_code.get(pin)
        if here is None:
            return None
        best = [(abs(here["lat"] - by_code[c]["lat"]) ** 2 + abs(here["lng"] - by_code[c]["lng"]) ** 2, c)
                for c in candidates if c in by_code]
        return min(best)[1] if best else None

    return nearest


__all__ = ["CHANNELS", "ExtendedData", "nearest_pin_factory"]
