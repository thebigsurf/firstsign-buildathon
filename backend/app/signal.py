"""The demand signal: baselines, ratios, breadth, co-movement, alert clusters, confidence,
the ASHA confidence loop and the distributor stock radar.

Method, in plain words
----------------------
Baseline   For each (pin code, medicine group) and each day D, the baseline is the median daily
           units over the 28 days D-34 .. D-7 (so the most recent 7 days, where an outbreak would
           sit, are excluded). It is weekday-aware: the median is multiplied by a shrunk factor
           (median of the four same-weekday values / overall median, halfway to 1, clipped).
Recent     The last 3 days are compared with their baselines: ratio = (recent + 0.5) / (baseline + 0.5).
Chronic    BP and diabetes orders are the stable denominator. If a pin's chronic volume moved
           (a scheme, a holiday), the group ratio is divided by that factor (clipped 0.75-1.4).
z          Robust z: excess daily units over sigma/sqrt(3), sigma = max(1.4826*MAD, sqrt(median), 1).
Breadth    History stores how many chemists ordered a group per day (not who), so breadth is the share of
           the pin's not-yet-ordering chemists who are now ordering: (recent - normal) / (chemists - normal).
           One chemist bulk-buying gives breadth near 0, however large the volume.
Levels     alert  : ratio >= 1.7, z >= 2.5, breadth >= 0.25, >= 1 extra chemist, >= 30 recent units and a real
                    baseline (>= 15 units in the 3 baseline days; a group that is normally absent cannot alert alone)
           watch  : ratio >= 1.35, z >= 2, breadth >= 0.20, >= 15 recent units
           Co-movement: a cell with ratio >= 1.7, z >= 2.5 and chemist participation rising (breadth >= 0.05) that
           sits next to an alerting cell of the same group is promoted to alert. Believing a neighbour is how a
           weakly measured pin joins a real cluster.
           A big ratio with no wider participation is flagged "concentrated_volume" and stays normal (the ORS decoy).
Clusters   Alerting pins of the same group within 3 km of each other form one alert. Neighbouring
           watch-only pins (two or more) form a watch.
Confidence signal strength (ratio and z, capped) x breadth factor x co-movement bonus, then moved by
           ASHA reports in log-odds space: counts above the background rate raise it, near-zero counts lower it.
Status     confirmed : confidence >= 0.70 and at least one ASHA report above the background rate
           dismissed : two or more ASHA reports near zero and none above background
           open      : otherwise
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from .catalogue import Catalogue
from .config import Settings
from .errors import NotFound
from .models import (
    Alert,
    Cell,
    PinDetail,
    RadarItem,
    RadarSku,
    ReportSummary,
    SeriesPoint,
    SignalResponse,
    Suppressed,
)
from .store import Reference, Store

SERIES_DAYS = 60
RECENT_DAYS = 3
NEIGHBOUR_KM = 3.0


@dataclass(frozen=True)
class Thresholds:
    alert_ratio: float = 1.7
    alert_z: float = 2.5
    alert_breadth: float = 0.25
    alert_extra_chemists: float = 1.0
    alert_min_units: float = 30.0
    alert_min_baseline: float = 15.0
    watch_ratio: float = 1.35
    watch_z: float = 2.0
    watch_breadth: float = 0.20
    watch_min_units: float = 15.0
    comove_breadth: float = 0.05
    chronic_clip: tuple[float, float] = (0.9, 1.4)
    chronic_min_volume: float = 6.0


T = Thresholds()

# Groups that can co-move with each other (used for the co-movement bonus and the explanation).
RELATED_GROUPS: dict[str, tuple[str, ...]] = {
    "diarrhoea": ("fever",),
    "fever": ("diarrhoea", "respiratory"),
    "respiratory": ("allergy", "fever", "tb_watch"),
    "allergy": ("respiratory",),
    "heat": ("diarrhoea",),
}
# Which ASHA-report fields speak to which alert group, and the normal share of households affected.
ASHA_FIELDS: dict[str, tuple[str, ...]] = {
    "diarrhoea": ("diarrhoea",),
    "fever": ("fever",),
    "respiratory": ("cough", "breathing"),
    "allergy": ("rash",),
    "heat": ("fever", "rash"),
    "fungal": ("rash",),
    "tb_watch": ("cough",),
}
BACKGROUND_RATE: dict[str, float] = {
    "diarrhoea": 0.02, "fever": 0.05, "respiratory": 0.06, "allergy": 0.02,
    "heat": 0.04, "fungal": 0.02, "tb_watch": 0.03,
}
NON_SIGNAL_GROUPS = {"other"}
# First-line molecules per group, used to put the obvious stock first on the radar (substring match on molecule).
FIRST_LINE_MOLECULES: dict[str, tuple[str, ...]] = {
    "diarrhoea": ("rehydration", "zinc"),
    "fever": ("paracetamol",),
    "heat": ("glucose", "dextrose", "electrolyte", "rehydration"),
    "allergy": ("cetirizine", "fexofenadine"),
    "respiratory": ("salbutamol", "levocetirizine", "ambroxol", "montelukast"),
    "fungal": ("clotrimazole", "terbinafine"),
}
RADAR_WEIGHTS = (0.4, 0.3, 0.2, 0.1)  # share of the suggested group stock given to each ranked SKU
# Alert status rule (shown in the UI):
#   confirmed  when confidence >= CONFIRM_AT and at least two ASHA reports are above the background rate
#   dismissed  when at least DISMISS_REPORTS reports are near zero and none is above background
#   open       otherwise
CONFIRM_AT = 0.70
CONFIRM_REPORTS = 2   # one visit can raise confidence but never confirms an alert alone
DISMISS_REPORTS = 2
MAX_REPORT_DELTA = 1.0  # cap on the log-odds one report can add (about +0.2 to +0.4 in probability)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


# ------------------------------------------------------------------------ cells


@dataclass
class CellStats:
    pin: str
    group: str
    today: float
    baseline: float
    ratio: float
    ratio_raw: float
    z: float
    breadth: float
    level: str
    recent_units: float
    recent_baseline: float
    c_recent: float
    c_base: float
    started: date
    flags: list[str] = field(default_factory=list)
    series: list[tuple[date, float, float]] = field(default_factory=list)


@dataclass
class Snapshot:
    as_of: date
    cells: dict[tuple[str, str], CellStats]
    chronic_factor: dict[str, float]


@dataclass(frozen=True)
class LiveCount:
    pin: str
    group: str
    units: float
    chemist_id: str


def _baseline_row(m: np.ndarray, t: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Baseline, window median and window MAD for every column on day index t."""
    lo, hi = max(0, t - 34), t - 6
    cols = m.shape[1]
    if hi <= lo:
        zeros = np.zeros(cols)
        return zeros, zeros, zeros
    win = m[lo:hi]
    med = np.median(win, axis=0)
    mad = np.median(np.abs(win - med), axis=0)
    same = [t - 7 * j for j in range(1, 5) if t - 7 * j >= 0]
    weekday_med = np.median(m[same], axis=0) if same else med
    safe = np.where(med > 0, med, 1.0)
    factor = np.clip(1 + 0.5 * (np.where(med > 0, weekday_med / safe, 1.0) - 1), 0.6, 1.5)
    base = np.where(med > 0, med * factor, win.mean(axis=0))
    return base, med, mad


class SignalEngine:
    """Computes cells from history plus live orders. Pure maths; no I/O after construction."""

    def __init__(self, ref: Reference, settings: Settings) -> None:
        self.ref = ref
        history = ref.history
        if settings.demo_as_of:
            history = history[history["date"] <= settings.demo_as_of]
        self.dates = list(pd.date_range(history["date"].min(), history["date"].max()))
        groups = sorted({g["id"] for g in ref.groups} | set(history["group"]))
        pins = sorted({p["pin"] for p in ref.pincodes} | set(history["pin"]))
        self.groups, self.pins = groups, pins
        self.columns = [(p, g) for p in pins for g in groups]
        index = {c: i for i, c in enumerate(self.columns)}
        self._index = index
        n_days = len(self.dates)
        self.units = np.zeros((n_days, len(self.columns)))
        self.chem = np.zeros((n_days, len(self.columns)))
        day_pos = {d: i for i, d in enumerate(self.dates)}
        for row in history.itertuples(index=False):
            col, day = index.get((row.pin, row.group)), day_pos.get(row.date)
            if col is not None and day is not None:
                self.units[day, col] += row.units
                self.chem[day, col] += row.chemists_ordering
        self.chemists_per_pin: dict[str, int] = {}
        for c in ref.chemists:
            self.chemists_per_pin[c["pin"]] = self.chemists_per_pin.get(c["pin"], 0) + 1
        self.neighbours = self._neighbour_map()
        self.chronic_cols = {
            p: [index[(p, g["id"])] for g in ref.groups if g.get("is_chronic") and (p, g["id"]) in index]
            for p in pins
        }

    @property
    def as_of(self) -> date:
        return self.dates[-1].date()

    def _neighbour_map(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {p["pin"]: set() for p in self.ref.pincodes}
        pins = self.ref.pincodes
        for i, a in enumerate(pins):
            for b in pins[i + 1:]:
                if a["pin"] != b["pin"] and haversine_km(a["lat"], a["lng"], b["lat"], b["lng"]) < NEIGHBOUR_KM:
                    out[a["pin"]].add(b["pin"])
                    out[b["pin"]].add(a["pin"])
        return out

    def snapshot(self, live: list[LiveCount]) -> Snapshot:
        units, chem = self.units.copy(), self.chem.copy()
        last = len(self.dates) - 1
        live_chemists: dict[int, set[str]] = {}
        for item in live:
            col = self._index.get((item.pin, item.group))
            if col is None:
                continue
            units[last, col] += item.units
            live_chemists.setdefault(col, set()).add(item.chemist_id)
        for col, who in live_chemists.items():
            chem[last, col] += len(who)

        t0 = max(0, last - SERIES_DAYS - RECENT_DAYS)
        base_rows = {t: _baseline_row(units, t)[0] for t in range(t0, last + 1)}
        base_t, med_t, mad_t = _baseline_row(units, last)
        _, c_med, _ = _baseline_row(chem, last)
        win_lo = max(0, last - 34)
        c_win_max = chem[win_lo:max(win_lo + 1, last - 6)].max(axis=0)

        recent_u = units[last - RECENT_DAYS + 1:last + 1].sum(axis=0)
        recent_b = sum(base_rows[t] for t in range(last - RECENT_DAYS + 1, last + 1))
        c_recent = chem[last - RECENT_DAYS + 1:last + 1].mean(axis=0)

        chronic_factor: dict[str, float] = {}
        for pin, cols in self.chronic_cols.items():
            r, b = float(recent_u[cols].sum()), float(recent_b[cols].sum()) if cols else 0.0
            factor = 1.0
            if cols and b >= T.chronic_min_volume:
                factor = min(max((r + 1) / (b + 1), T.chronic_clip[0]), T.chronic_clip[1])
            chronic_factor[pin] = factor

        cells: dict[tuple[str, str], CellStats] = {}
        for (pin, group), col in self._index.items():
            factor = chronic_factor.get(pin, 1.0)
            ratio_raw = (recent_u[col] + 0.5) / (recent_b[col] + 0.5)
            ratio = ratio_raw / factor
            sigma = max(1.4826 * mad_t[col], math.sqrt(max(med_t[col], 1.0)), 1.0)
            z = ((recent_u[col] / RECENT_DAYS) / factor - recent_b[col] / RECENT_DAYS) / (sigma / math.sqrt(RECENT_DAYS))
            n_chem = self.chemists_per_pin.get(pin, 0)
            denom = max(n_chem, c_win_max[col], c_recent[col], 1.0)
            breadth = float(np.clip((c_recent[col] - c_med[col]) / max(denom - c_med[col], 1.0), 0, 1))
            level, flags = self._level(group, float(ratio), float(z), breadth, float(recent_u[col]),
                                       float(c_recent[col] - c_med[col]), float(recent_b[col]))
            series = [(self.dates[t].date(), float(units[t, col]), float(base_rows[t][col]))
                      for t in range(max(0, last - SERIES_DAYS + 1), last + 1)]
            cells[(pin, group)] = CellStats(
                pin=pin, group=group, today=float(units[last, col]), baseline=float(base_t[col]),
                ratio=float(ratio), ratio_raw=float(ratio_raw), z=float(z), breadth=breadth, level=level,
                recent_units=float(recent_u[col]), recent_baseline=float(recent_b[col]),
                c_recent=float(c_recent[col]), c_base=float(c_med[col]),
                started=self.as_of,
                flags=flags, series=series,
            )
        self._promote_by_comovement(cells)
        for key, cell in cells.items():
            if cell.level != "normal":
                cell.started = self._started(units, base_rows, self._index[key], last)
        return Snapshot(as_of=self.as_of, cells=cells, chronic_factor=chronic_factor)

    def _promote_by_comovement(self, cells: dict[tuple[str, str], CellStats]) -> None:
        """Promote strong cells with rising participation that touch an alerting neighbour (same group)."""
        alerting = {k for k, c in cells.items() if c.level == "alert"}
        for (pin, group), cell in cells.items():
            if cell.level == "alert" or group in NON_SIGNAL_GROUPS or self.ref.is_chronic(group):
                continue
            strong = (cell.ratio >= T.alert_ratio and cell.z >= T.alert_z and cell.breadth >= T.comove_breadth
                      and cell.c_recent > cell.c_base and cell.recent_units >= T.alert_min_units)
            if strong and any((n, group) in alerting for n in self.neighbours.get(pin, ())):
                cell.level = "alert"
                cell.flags = ["promoted_by_neighbour"]

    def _level(self, group: str, ratio: float, z: float, breadth: float, recent: float,
               extra_chemists: float, baseline: float) -> tuple[str, list[str]]:
        if group in NON_SIGNAL_GROUPS or self.ref.is_chronic(group):
            return "normal", []
        if (ratio >= T.alert_ratio and z >= T.alert_z and breadth >= T.alert_breadth
                and extra_chemists >= T.alert_extra_chemists and recent >= T.alert_min_units
                and baseline >= T.alert_min_baseline):
            return "alert", []
        if ratio >= T.watch_ratio and z >= T.watch_z and breadth >= T.watch_breadth and recent >= T.watch_min_units:
            return "watch", []
        if ratio >= T.alert_ratio and z >= T.watch_z and breadth < T.watch_breadth and recent >= T.alert_min_units:
            return "normal", ["concentrated_volume"]
        return "normal", []

    def _started(self, units: np.ndarray, base_rows: dict[int, np.ndarray], col: int, last: int) -> date:
        """First day of the unbroken run, ending today, where the 3-day ratio is at least the watch ratio."""
        first = last
        for t in range(last, max(min(base_rows), RECENT_DAYS) - 1, -1):
            u = units[t - RECENT_DAYS + 1:t + 1, col].sum()
            b = sum(base_rows[k][col] for k in range(t - RECENT_DAYS + 1, t + 1) if k in base_rows)
            if (u + 0.5) / (b + 0.5) >= T.watch_ratio:
                first = t
            else:
                break
        return self.dates[first].date()


# ------------------------------------------------------------------ ASHA loop


def relevant_cases(group: str, report: dict[str, Any]) -> int:
    return sum(int(report.get(f, 0)) for f in ASHA_FIELDS.get(group, ()))


def report_delta(group: str, report: dict[str, Any]) -> float:
    """Change in log-odds from one ASHA report for an alert of `group`.

    Counts above the household background rate push confidence up; near-zero counts push it down.
    Reports that cannot speak to the group (for example eye infections) change nothing.
    """
    if group not in ASHA_FIELDS:
        return 0.0
    households = max(int(report.get("households_visited", 0)), 10)
    expected = households * BACKGROUND_RATE[group]
    cases = relevant_cases(group, report)
    delta = max(-1.5, min(MAX_REPORT_DELTA, 0.8 * math.log((cases + 0.5) / (expected + 0.5))))
    if group == "diarrhoea" and report.get("water_issue_reported") and cases > expected:
        delta += 0.4
    return round(min(delta, MAX_REPORT_DELTA), 3)


def apply_reports(base: float, group: str, reports: list[dict[str, Any]]) -> tuple[float, str, list[float]]:
    """Fold reports into a base confidence. Returns (confidence, status, per-report deltas)."""
    logit, deltas = _logit(base), []
    for rep in reports:
        d = report_delta(group, rep)
        deltas.append(d)
        logit += d
    conf = min(max(_sigmoid(logit), 0.05), 0.98)
    raised_count = sum(1 for d in deltas if d > 0.2)
    raised = raised_count > 0
    near_zero = sum(1 for d in deltas if d < -0.2)
    status = "open"
    if raised_count >= CONFIRM_REPORTS and conf >= CONFIRM_AT:
        status = "confirmed"
    elif near_zero >= DISMISS_REPORTS and not raised:
        status = "dismissed"
    return round(conf, 3), status, deltas


# ------------------------------------------------------------------ alerts


def _components(nodes: set[str], neighbours: dict[str, set[str]]) -> list[list[str]]:
    seen: set[str] = set()
    out: list[list[str]] = []
    for start in sorted(nodes):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in neighbours.get(cur, set()) & nodes:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        out.append(sorted(comp))
    return out


def base_confidence(ratio: float, z: float, breadth: float, n_pins: int, related_up: int) -> float:
    """signal strength (ratio and z, capped) x breadth factor x co-movement bonus, capped at 0.9."""
    strength = 0.6 * min(max((ratio - 1) / 1.5, 0), 1) + 0.4 * min(max(z / 6, 0), 1)
    breadth_factor = 0.4 + 0.6 * min(max(breadth, 0), 1)
    bonus = 1 + 0.08 * min(max(n_pins - 1, 0), 3) + 0.05 * min(related_up, 2)
    return round(min(0.9, strength * breadth_factor * bonus), 3)


def _x(value: float) -> str:
    return f"{value:.1f}x"


if TYPE_CHECKING:
    from .extended import ExtendedData


class SignalService:
    """Everything the API needs from the signal: cells, alerts, radar. Recomputes when state changes."""

    def __init__(self, ref: Reference, store: Store, catalogue: Catalogue, settings: Settings,
                 extended: "ExtendedData | None" = None) -> None:
        self.ref, self.store, self.catalogue, self.settings = ref, store, catalogue, settings
        self.extended = extended
        self.engine = SignalEngine(ref, settings)
        self._lock = threading.Lock()
        self._cache_version = -1
        self._snapshot: Snapshot | None = None
        self._alerts: list[Alert] = []

    # ------------------------------------------------------------- live inputs

    def _live_counts(self) -> list[LiveCount]:
        out: list[LiveCount] = []
        for order in self.store.list_orders():
            for line in order.get("lines", []):
                if line.get("group") and line.get("sku_id"):
                    out.append(LiveCount(order["pin"], line["group"], float(line.get("qty", 1)), order["chemist_id"]))
        return out

    def _refresh(self) -> None:
        with self._lock:
            if self._snapshot is not None and self._cache_version == self.store.version:
                return
            version = self.store.version
            self._snapshot = self.engine.snapshot(self._live_counts())
            self._alerts = self._build_alerts(self._snapshot, self.store.list_asha_reports())
            self._cache_version = version

    @property
    def snapshot(self) -> Snapshot:
        self._refresh()
        assert self._snapshot is not None
        return self._snapshot

    # ----------------------------------------------------------------- signal

    def signal(self, days: int) -> SignalResponse:
        snap = self.snapshot
        days = max(1, min(days, SERIES_DAYS))
        cells = []
        for c in snap.cells.values():
            cells.append(Cell(
                pin=c.pin, group=c.group, today=round(c.today, 1), baseline=round(c.baseline, 2),
                ratio=round(c.ratio, 2), z=round(c.z, 2), breadth=round(c.breadth, 2), level=c.level,  # type: ignore[arg-type]
                series=[SeriesPoint(date=d.isoformat(), units=round(u, 1), baseline=round(b, 2)) for d, u, b in c.series[-days:]],
                ratio_raw=round(c.ratio_raw, 2), recent_units=round(c.recent_units, 1),
                recent_baseline=round(c.recent_baseline, 2), chemists_ordering=round(c.c_recent, 1),
                chemists_baseline=round(c.c_base, 1), flags=c.flags,
            ))
        cells.sort(key=lambda c: (-{"alert": 2, "watch": 1, "normal": 0}[c.level], -c.ratio))
        return SignalResponse(as_of=snap.as_of.isoformat(), cells=cells, suppressed=self.suppressed())

    def suppressed(self) -> list[Suppressed]:
        """Cells with a big rise but low breadth: shown so people can see the system declined to alert."""
        out = [
            Suppressed(pin=c.pin, area=self.ref.area(c.pin), group=c.group, ratio=round(c.ratio, 2),
                       breadth=round(c.breadth, 2),
                       why=f"High volume ({c.ratio:.1f}x normal) but only {round(c.breadth * 100)}% of chemists moved: "
                           "looks like one shop buying in bulk, not a wider rise. Not alerted.")
            for c in self.snapshot.cells.values() if "concentrated_volume" in c.flags
        ]
        return sorted(out, key=lambda s: -s.ratio)

    # ----------------------------------------------------------------- alerts

    def alerts(self) -> list[Alert]:
        self._refresh()
        return [a.model_copy(deep=True) for a in self._alerts]

    def alert(self, alert_id: str) -> Alert:
        for a in self.alerts():
            if a.alert_id == alert_id:
                return a
        raise NotFound("Alert", alert_id)

    def _build_alerts(self, snap: Snapshot, reports: list[dict[str, Any]]) -> list[Alert]:
        neighbours = self.engine.neighbours
        alerts: list[Alert] = []
        for group in self.engine.groups:
            if group in NON_SIGNAL_GROUPS or self.ref.is_chronic(group):
                continue
            by_level = {"alert": set(), "watch": set()}
            for pin in self.engine.pins:
                cell = snap.cells.get((pin, group))
                if cell and cell.level in by_level:
                    by_level[cell.level].add(pin)
            for pins in _components(by_level["alert"], neighbours):
                alerts.append(self._make_alert(snap, group, pins, "alert", reports))
            for pins in _components(by_level["watch"], neighbours):
                if len(pins) >= 2:
                    alerts.append(self._make_alert(snap, group, pins, "watch", reports))
        alerts.sort(key=lambda a: (a.level != "alert", -a.confidence, -a.ratio))
        return alerts

    def _make_alert(self, snap: Snapshot, group: str, pins: list[str], level: str,
                    reports: list[dict[str, Any]]) -> Alert:
        cells = [snap.cells[(p, group)] for p in pins]
        ratio = max(c.ratio for c in cells)
        z = max(c.z for c in cells)
        breadth = sum(c.breadth for c in cells) / len(cells)
        related_up, related_flat = self._related(snap, group, pins)
        base = base_confidence(ratio, z, breadth, len(pins), len(related_up))
        if level == "watch":
            base = round(base * 0.7, 3)
        mine = sorted((r for r in reports if r.get("pin") in pins), key=lambda r: r.get("created_at", ""))
        conf, status, deltas = apply_reports(base, group, mine)

        label = self.ref.group_label(group)
        areas = ", ".join(f"{self.ref.area(p)} ({p})" for p in pins)
        reasons = [
            f"{label} medicine orders are {_x(ratio)} their normal level across {len(pins)} neighbouring pin code"
            f"{'s' if len(pins) > 1 else ''}: {areas}.",
            f"About {round(breadth * 100)}% of the chemists in these pin codes who do not normally order this are "
            f"ordering it now, so it is not one shop (breadth {breadth:.2f}).",
            f"The rise is statistically strong: robust z-score {z:.1f} (3 or more is unusual).",
        ]
        if len(pins) > 1:
            reasons.append(f"Neighbouring pin codes within {NEIGHBOUR_KM:.0f} km are rising together, which points to a shared cause.")
        for rg, rpin, rratio in related_up:
            reasons.append(f"{self.ref.group_label(rg)} orders are also up {_x(rratio)} in {self.ref.area(rpin)} ({rpin}).")
        for rg in related_flat:
            reasons.append(f"{self.ref.group_label(rg)} orders are flat, which fits this pattern better than a general illness wave.")
        factors = [snap.chronic_factor.get(p, 1.0) for p in pins]
        reasons.append(
            f"Chronic medicines (BP, diabetes) are steady at about {sum(factors) / len(factors):.1f}x, "
            "so this is not just chemists ordering more of everything."
        )
        summaries: list[ReportSummary] = []
        for rep, delta in zip(mine, deltas, strict=True):
            effect = "raised" if delta > 0.2 else "lowered" if delta < -0.2 else "neutral"
            cases = relevant_cases(group, rep)
            where = rep.get("locality", rep.get("locality_id", ""))
            reasons.append(
                f"ASHA report from {where}: {cases} relevant case{'s' if cases != 1 else ''} among "
                f"{rep.get('households_visited', 0)} households "
                f"(normal is about {max(int(rep.get('households_visited', 0)), 10) * BACKGROUND_RATE.get(group, 0):.1f}); "
                f"this {effect if effect != 'neutral' else 'did not change'} the confidence."
            )
            summaries.append(ReportSummary(
                report_id=rep["report_id"], delta=delta, locality_id=rep.get("locality_id", ""), locality=str(where),
                created_at=rep.get("created_at", ""), effect=effect,  # type: ignore[arg-type]
                relevant_cases=cases, households_visited=int(rep.get("households_visited", 0)),
            ))
        reasons.insert(0, f"Confidence {round(conf * 100)}%: {'before ASHA reports ' + str(round(base * 100)) + '%' if mine else 'from order data only, awaiting ASHA verification'}.")

        return Alert(
            alert_id=f"{group}-{pins[0]}", pins=pins, group=group, level=level,  # type: ignore[arg-type]
            ratio=round(ratio, 2), breadth=round(breadth, 2), started=min(c.started for c in cells).isoformat(),
            confidence=conf, status=status,  # type: ignore[arg-type]
            asha_reports=len(mine), reasons=reasons, group_label=label, base_confidence=base,
            pin_details=[PinDetail(pin=c.pin, area=self.ref.area(c.pin), ratio=round(c.ratio, 2),
                                   breadth=round(c.breadth, 2), level=c.level, today=round(c.today, 1))  # type: ignore[arg-type]
                         for c in cells],
            reports=summaries, z=round(z, 2),
        )

    def _related(self, snap: Snapshot, group: str, pins: list[str]) -> tuple[list[tuple[str, str, float]], list[str]]:
        up: list[tuple[str, str, float]] = []
        flat: list[str] = []
        for rg in RELATED_GROUPS.get(group, ()):
            ratios = [(p, snap.cells[(p, rg)]) for p in pins if (p, rg) in snap.cells]
            risers = [(p, c) for p, c in ratios if c.ratio >= 1.3 and c.level != "normal"]
            if risers:
                best = max(risers, key=lambda pc: pc[1].ratio)
                up.append((rg, best[0], best[1].ratio))
            elif ratios and group == "fever" and rg == "respiratory" and all(c.ratio < 1.15 for _, c in ratios):
                flat.append(rg)
        return up, flat

    # ------------------------------------------------------------ explain context

    def explain_context(self, alert: Alert) -> dict[str, Any]:
        """Our own numbers for the agent: series, breadth, co-moving groups, decoy check, localities."""
        snap = self.snapshot
        per_pin = []
        for pin in alert.pins:
            cell = snap.cells[(pin, alert.group)]
            per_pin.append({
                "pin": pin, "area": self.ref.area(pin), "ratio_vs_normal": round(cell.ratio, 2),
                "z": round(cell.z, 1), "breadth": round(cell.breadth, 2),
                "units_last_14_days": [round(u, 1) for _, u, _ in cell.series[-14:]],
                "normal_units_per_day": round(cell.baseline, 1),
                "chemists_ordering_now": round(cell.c_recent, 1), "chemists_ordering_normally": round(cell.c_base, 1),
            })
        _, flat = self._related(snap, alert.group, alert.pins)
        co_moving = []
        for rg in RELATED_GROUPS.get(alert.group, ()):
            for pin in alert.pins:
                c = snap.cells.get((pin, rg))
                if c:
                    co_moving.append({"group": rg, "pin": pin, "ratio": round(c.ratio, 2)})
        decoys = [
            {"pin": c.pin, "group": c.group, "ratio": round(c.ratio, 2), "breadth": round(c.breadth, 2)}
            for c in snap.cells.values() if "concentrated_volume" in c.flags
        ]
        localities = [
            {"locality_id": x["locality_id"], "pin": x["pin"], "name": x["name"], "landmark": x["landmark"],
             "households": x["households"]}
            for x in self.ref.localities if x["pin"] in alert.pins
        ]
        return {
            "as_of": snap.as_of.isoformat(), "started": alert.started, "group": alert.group,
            "pins": per_pin, "co_moving_groups": co_moving, "related_groups_flat": flat,
            "decoy_check": {
                "concentrated_volume_cells_elsewhere": decoys,
                "this_alert_breadth": alert.breadth,
                "note": "Concentrated cells are single-shop bulk buying and were NOT alerted.",
            },
            "chronic_medicine_factor": {p: round(snap.chronic_factor.get(p, 1.0), 2) for p in alert.pins},
            "asha_reports": [r.model_dump() for r in alert.reports],
            "localities": localities,
        }

    # ------------------------------------------------------------------ radar

    def radar(self) -> list[RadarItem]:
        """Distributor stock radar for pins the distributor serves, from watch and alert cells."""
        snap = self.snapshot
        served = {c["pin"] for c in self.ref.chemists
                  if c["chemist_id"] in set(self.ref.distributor.get("chemist_ids", [c["chemist_id"]]))}
        live_sales = self._live_sku_volume()
        cover, asked = self._stock_context()
        alert_of: dict[tuple[str, str], str] = {}
        for a in self._alerts:
            for p in a.pins:
                alert_of[(p, a.group)] = a.alert_id
        items: list[RadarItem] = []
        for (pin, group), cell in snap.cells.items():
            if pin not in served or cell.level == "normal":
                continue
            skus = [s for s in self.catalogue.skus.values() if s.group == group]
            if not skus:
                continue
            # No per-SKU history in the data contract, so rank first-line molecules first, then live approved
            # volume, then how many spoken/written aliases chemists use for the item (a proxy for demand).
            first_line = FIRST_LINE_MOLECULES.get(group, ())
            # Stock-outs first: an item chemists here already asked for and could not get is the one to send.
            skus.sort(key=lambda s: (-asked.get((pin, s.sku_id), {}).get("chemists", 0) == 0,
                                     not any(k in s.molecule.lower() for k in first_line),
                                     -asked.get((pin, s.sku_id), {}).get("chemists", 0),
                                     -live_sales.get(s.sku_id, 0.0), -len(s.aliases)))
            top = skus[:4]
            weights = [w / sum(RADAR_WEIGHTS[: len(top)]) for w in RADAR_WEIGHTS[: len(top)]]
            recent_daily = cell.recent_units / RECENT_DAYS
            group_qty = recent_daily * self.settings.cover_days
            reason = (
                f"{self.settings.cover_days} days of cover at today's pace ({recent_daily:.0f} units a day across "
                f"the group, {_x(cell.ratio)} normal) in {self.ref.area(pin)}."
            )
            items.append(RadarItem(
                pin=pin, area=self.ref.area(pin), group=group, ratio=round(cell.ratio, 2),
                chemists_affected=int(round(cell.c_recent)), level=cell.level,  # type: ignore[arg-type]
                group_label=self.ref.group_label(group), alert_id=alert_of.get((pin, group)),
                skus=[self._radar_sku(s, w, group_qty, reason, pin, cover, asked)
                      for s, w in zip(top, weights, strict=True)],
            ))
        items.sort(key=lambda i: (i.level != "alert", -i.ratio))
        return items

    def _stock_context(self) -> tuple[dict[str, float], dict[tuple[str, str], dict[str, int]]]:
        """Days of cover per SKU at the distributor and who asked for what last week (simulated log plus live mentions)."""
        if self.extended is None:
            return {}, {}
        live = [{"pin": x.get("pin"), "chemist_id": x.get("chemist_id"), "sku_id": x.get("sku_id"),
                 "qty_wanted": x.get("qty_wanted", 0)} for x in self.store.list_stockouts()]
        return self.extended.cover_by_sku(), self.extended.asked_by_sku_pin(7, live)

    def _radar_sku(self, sku: Any, weight: float, group_qty: float, reason: str, pin: str,
                   cover: dict[str, float], asked: dict[tuple[str, str], dict[str, int]]) -> RadarSku:
        """One radar line. With stock and stock-out data the quantity adds the units already missed and the reason says why."""
        qty = max(1, math.ceil(group_qty * weight))
        brand = f"{sku.brand} {sku.strength}".strip()
        days = cover.get(sku.sku_id)
        ask = asked.get((pin, sku.sku_id))
        if days is None and ask is None:
            return RadarSku(sku_id=sku.sku_id, brand=brand, suggested_qty=qty, reason=reason)
        parts = []
        if days is not None:
            parts.append(f"{days:.0f} days of cover" if days >= 1 else "0 days of cover")
        if ask:
            n = ask["chemists"]
            parts.append(f"{n} {'chemist' if n == 1 else 'chemists'} in {self.ref.area(pin)} asked last week")
            qty += ask["short"]
        lead = ", ".join(parts)
        extra = f" plus {ask['short']} units already missed" if ask and ask["short"] else ""
        return RadarSku(sku_id=sku.sku_id, brand=brand, suggested_qty=qty,
                        reason=f"{lead[0].upper()}{lead[1:]}. {qty - (ask['short'] if ask else 0)} units cover "
                               f"{self.settings.cover_days} days at today's pace{extra}.")

    def _live_sku_volume(self) -> dict[str, float]:
        volume: dict[str, float] = {}
        for order in self.store.list_orders():
            for line in order.get("lines", []):
                if line.get("sku_id"):
                    volume[line["sku_id"]] = volume.get(line["sku_id"], 0.0) + float(line.get("qty", 1))
        return volume
