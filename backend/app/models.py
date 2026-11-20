"""Pydantic models: the API types from ARCHITECTURE.md section 5 plus the schemas
we hand to Gemini as structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LineStatus = Literal["matched", "uncertain", "unknown"]
Level = Literal["normal", "watch", "alert"]
AlertStatus = Literal["open", "confirmed", "dismissed"]
ActionName = Literal["distributor_note", "officer_note", "asha_visit_list"]


# --------------------------------------------------------------------------- orders


class Alternative(BaseModel):
    sku_id: str
    brand: str
    score: float


class OrderLine(BaseModel):
    """One line of an order. `reason` says in plain words why a line is not certain."""

    raw_text: str
    sku_id: str | None = None
    brand: str | None = None
    strength: str | None = None
    form: str | None = None
    molecule: str | None = None
    group: str | None = None
    qty: int = Field(default=1, ge=1, le=10000)
    unit: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    status: LineStatus = "unknown"
    alternatives: list[Alternative] = Field(default_factory=list)
    reason: str | None = None


class ParsedOrder(BaseModel):
    message_id: str | None = None
    chemist_id: str
    language: str = "hi"
    transcript: str = ""
    lines: list[OrderLine] = Field(default_factory=list)
    not_available: list[str] = Field(default_factory=list)
    notes: str = ""
    model: str = ""
    latency_ms: int = 0
    cached: bool = False


class OrderCreate(BaseModel):
    chemist_id: str
    message_id: str | None = None
    lines: list[OrderLine]
    approved_by: str = Field(min_length=1, max_length=80)
    original_lines: list[OrderLine] | None = Field(
        default=None, description="The lines as Gemini returned them. If omitted, the stored parse is used."
    )


class OrderRecord(BaseModel):
    order_id: str
    chemist_id: str
    pin: str
    message_id: str | None
    lines: list[OrderLine]
    approved_by: str
    created_at: str


class OrderCreated(BaseModel):
    order_id: str


# ---------------------------------------------------- Gemini output schemas (parsing)


class ModelOrderLine(BaseModel):
    """What we ask Gemini to return for one order line."""

    raw_text: str = Field(description="The chemist's own words for this line.")
    sku_id: str | None = Field(default=None, description="Exact sku_id from the catalogue, or null.")
    raw_text_latin: str | None = Field(
        default=None,
        description="The medicine name in Latin (English) letters, as it would be spelt on a pack. Required whenever "
                    "raw_text is in Devanagari or another script; otherwise null.")
    brand: str | None = Field(default=None, description="Brand as heard or written, if different from raw_text.")
    strength: str | None = None
    qty: int | None = Field(default=None, description="Quantity as stated; null if not stated.")
    unit: str | None = Field(default=None, description="strip, box, bottle, sachet, tube or vial.")
    confidence: float = Field(default=0.7, description="Your own confidence from 0 to 1.")


class ModelOrderOut(BaseModel):
    language: str = Field(default="hi", description="hi, mr or en.")
    transcript: str = ""
    lines: list[ModelOrderLine] = Field(default_factory=list)
    not_available: list[str] = Field(default_factory=list)
    unplaced: list[str] = Field(
        default_factory=list,
        description="Words or numbers you heard or read that look like part of an order but that you could not "
                    "turn into a line. Empty if everything was placed.")
    notes: str = ""


class AshaStructured(BaseModel):
    """Structured ASHA visit observation (counts only, never names)."""

    model_config = ConfigDict(extra="ignore")

    language: str = "hi"
    transcript: str = ""
    households_visited: int = Field(default=0, ge=0)
    fever: int = Field(default=0, ge=0)
    diarrhoea: int = Field(default=0, ge=0)
    cough: int = Field(default=0, ge=0)
    breathing: int = Field(default=0, ge=0)
    rash: int = Field(default=0, ge=0)
    children_affected: int = Field(default=0, ge=0)
    referred: int = Field(default=0, ge=0)
    water_issue_reported: bool = False
    notes: str = ""


class AshaReportResult(AshaStructured):
    alert_id: str | None = None
    new_confidence: float | None = None
    report_id: str = ""
    updates: list[dict] = Field(default_factory=list)
    model: str = ""
    latency_ms: int = 0


# ---------------------------------------------------------------------------- signal


class SeriesPoint(BaseModel):
    date: str
    units: float
    baseline: float


class Cell(BaseModel):
    pin: str
    group: str
    today: float
    baseline: float
    ratio: float
    z: float
    breadth: float
    level: Level
    series: list[SeriesPoint]
    ratio_raw: float = 0.0
    recent_units: float = 0.0
    recent_baseline: float = 0.0
    chemists_ordering: float = 0.0
    chemists_baseline: float = 0.0
    flags: list[str] = Field(default_factory=list)


class Suppressed(BaseModel):
    """High volume but not broad: deliberately not alerted (for example one shop bulk-buying)."""

    pin: str
    area: str
    group: str
    ratio: float
    breadth: float
    why: str


class SignalResponse(BaseModel):
    as_of: str
    cells: list[Cell]
    suppressed: list[Suppressed] = Field(default_factory=list)
    simulated: bool = True
    note: str = "Simulated history for demo. Live approved orders add to today."


class PinDetail(BaseModel):
    pin: str
    area: str
    ratio: float
    breadth: float
    level: Level
    today: float


class ReportSummary(BaseModel):
    report_id: str
    delta: float = 0.0
    locality_id: str
    locality: str
    created_at: str
    effect: Literal["raised", "lowered", "neutral"]
    relevant_cases: int
    households_visited: int


class Alert(BaseModel):
    alert_id: str
    pins: list[str]
    group: str
    level: Literal["watch", "alert"]
    ratio: float
    breadth: float
    started: str
    confidence: float
    status: AlertStatus
    asha_reports: int
    reasons: list[str]
    group_label: str = ""
    base_confidence: float = 0.0
    pin_details: list[PinDetail] = Field(default_factory=list)
    reports: list[ReportSummary] = Field(default_factory=list)
    z: float = 0.0


class RadarSku(BaseModel):
    sku_id: str
    brand: str
    suggested_qty: int
    reason: str


class RadarItem(BaseModel):
    pin: str
    area: str
    group: str
    skus: list[RadarSku]
    ratio: float
    chemists_affected: int
    level: Level = "alert"
    group_label: str = ""
    alert_id: str | None = None


# ---------------------------------------------------------------------------- agent


class LikelyCause(BaseModel):
    cause: str
    evidence: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class VisitItem(BaseModel):
    locality_id: str
    name: str = ""
    landmark: str = ""
    priority: int = Field(default=1, ge=1)
    reason: str = ""


class Source(BaseModel):
    title: str
    url: str


class AgentActions(BaseModel):
    distributor_note: str
    officer_note: str
    asha_visit_list: list[VisitItem]


class Explanation(BaseModel):
    alert_id: str = ""
    summary: str
    likely_causes: list[LikelyCause]
    sources: list[Source]
    actions: AgentActions
    model: str = ""
    latency_ms: int = 0
    grounded: bool = False
    cached: bool = False
    search_note: str = ""
    search_queries: list[str] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    alert_id: str
    refresh: bool = False


class ModelCause(BaseModel):
    cause: str
    evidence: str
    confidence: float


class ModelVisit(BaseModel):
    locality_id: str
    priority: int
    reason: str


class ModelExplain(BaseModel):
    """Schema for the reasoning call."""

    summary: str
    likely_causes: list[ModelCause]
    distributor_note: str
    officer_note: str
    asha_visit_list: list[ModelVisit]


class ActionApproveRequest(BaseModel):
    alert_id: str
    action: ActionName
    approved_by: str = Field(min_length=1, max_length=80)
    edited_text: str | None = Field(default=None, max_length=4000)


class ActionApproved(BaseModel):
    approval_id: str
    alert_id: str
    action: ActionName
    approved_by: str
    created_at: str
    text: str
    edited: bool
    visit_list: list[VisitItem] = Field(default_factory=list)


# ----------------------------------------------------------------------------- misc


class AuditEntry(BaseModel):
    """Who did what and when. `before` and `after` hold the AI reading versus the approved value."""

    id: str
    ts: str
    actor: str
    approved_by: str
    kind: str
    ref_id: str
    summary: str
    before: dict | None = None
    after: dict | None = None
    detail: dict = Field(default_factory=dict)


class Metrics(BaseModel):
    orders_parsed: int
    lines_parsed: int
    auto_matched_pct: float
    uncertain_pct: float
    avg_latency_ms: int
    asha_reports: int
    alerts_confirmed: int
    orders_approved: int = 0
    unknown_pct: float = 0.0
    latency_p50_ms: int = 0
    latency_p95_ms: int = 0
    edit_rate_pct: float = 0.0
    minutes_saved_est: float = 0.0
    alert_precision: float | None = None
    reports_confirming: int = 0
    reports_cancelling: int = 0
    decoys_suppressed: int = 0
    alerts_raised: int = 0
    days_first_sign_to_action: float | None = None


class Health(BaseModel):
    status: str
    model_fast: str
    model_reason: str
    storage: str
    signal_backend: str
    offline: bool
    version: str = ""
    data_loaded: bool = True


class Telemetry(BaseModel):
    """Gemini usage since the server started."""

    calls: int
    by_model: dict[str, int]
    fallbacks: int
    errors: int
    avg_latency_ms: int
    grounded_sources_total: int
    cache_hits: int
    offline: bool
