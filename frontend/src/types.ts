/** API types. Mirrors ARCHITECTURE.md section 5 and backend/app/models.py. */

export type LineStatus = "matched" | "uncertain" | "unknown";
export type Level = "normal" | "watch" | "alert";
export type AlertStatus = "open" | "confirmed" | "dismissed";
export type ActionName = "distributor_note" | "officer_note" | "asha_visit_list";
export type Lang = "hi" | "mr" | "en";

export interface Alternative {
  sku_id: string;
  brand: string;
  score: number;
}

export interface OrderLine {
  raw_text: string;
  sku_id: string | null;
  brand: string | null;
  strength: string | null;
  form: string | null;
  molecule: string | null;
  group: string | null;
  qty: number;
  unit: string | null;
  confidence: number;
  status: LineStatus;
  alternatives: Alternative[];
  note?: string | null;
  reason?: string | null;
}

export interface ParsedOrder {
  message_id: string | null;
  chemist_id: string;
  language: string;
  transcript: string;
  lines: OrderLine[];
  not_available: string[];
  notes: string;
  model: string;
  latency_ms: number;
  cached?: boolean;
}

export interface CatalogueItem {
  sku_id: string;
  brand: string;
  strength: string;
  form: string;
  pack: string;
  molecule: string;
  group: string;
  unit: string;
  aliases?: string;
}

export interface Group {
  id: string;
  label: string;
  label_hi: string;
  color_hint: string;
  is_chronic: boolean;
}

export interface Pincode {
  pin: string;
  area: string;
  ward: string;
  lat: number;
  lng: number;
  population: number;
}

export interface Chemist {
  chemist_id: string;
  shop_name: string;
  owner_first_name: string;
  pin: string;
  lat: number;
  lng: number;
  language: Lang;
  software: string;
}

export interface Distributor {
  name: string;
  area_served?: string;
  chemist_ids: string[];
}

export interface Asha {
  asha_id: string;
  first_name: string;
  pin: string;
  language: Lang;
}

export type MessageType = "voice" | "photo" | "text";
export type MessageStatus = "new" | "parsed" | "approved";

export interface InboxMessage {
  id: string;
  chemist_id: string;
  received_at: string;
  type: MessageType;
  text?: string | null;
  media?: string | null;
  media_url?: string | null;
  status: MessageStatus;
  parsed?: ParsedOrder | null;
  approved_by?: string | null;
  approved_at?: string | null;
  order_id?: string | null;
  chemist?: { shop_name?: string | null; owner_first_name?: string | null; pin?: string | null; language?: string | null } | null;
}

export interface OrderRecord {
  order_id: string;
  chemist_id: string;
  pin: string;
  message_id: string | null;
  lines: OrderLine[];
  approved_by: string;
  created_at: string;
}

export interface SeriesPoint {
  date: string;
  units: number;
  baseline: number;
}

export interface Cell {
  pin: string;
  group: string;
  today: number;
  baseline: number;
  ratio: number;
  z: number;
  breadth: number;
  level: Level;
  series: SeriesPoint[];
  flags?: string[];
}

export interface SignalResponse {
  as_of: string;
  cells: Cell[];
  simulated?: boolean;
  note?: string;
  suppressed?: Suppressed[];
}

export interface Suppressed {
  pin: string;
  group: string;
  ratio: number;
  breadth: number;
  why: string;
}

export interface PinDetail {
  pin: string;
  area: string;
  ratio: number;
  breadth: number;
  level: Level;
  today: number;
}

export interface ReportSummary {
  report_id: string;
  locality_id: string;
  locality: string;
  created_at: string;
  effect: "raised" | "lowered" | "neutral";
  relevant_cases: number;
  households_visited: number;
}

export interface Alert {
  alert_id: string;
  pins: string[];
  group: string;
  level: "watch" | "alert";
  ratio: number;
  breadth: number;
  started: string;
  confidence: number;
  status: AlertStatus;
  asha_reports: number;
  reasons: string[];
  group_label?: string;
  base_confidence?: number;
  pin_details?: PinDetail[];
  reports?: ReportSummary[];
  z?: number;
}

export interface RadarSku {
  sku_id: string;
  brand: string;
  suggested_qty: number;
  reason: string;
  /** Distributor stock cover (days) when the backend knows it. */
  days_of_cover?: number | null;
}

export interface RadarItem {
  pin: string;
  area: string;
  group: string;
  skus: RadarSku[];
  ratio: number;
  chemists_affected: number;
  level?: Level;
  group_label?: string;
  alert_id?: string | null;
}

export interface LikelyCause {
  cause: string;
  evidence: string;
  confidence: number;
}

export interface Source {
  title: string;
  url: string;
}

export interface VisitItem {
  locality_id: string;
  name: string;
  landmark: string;
  priority: number;
  reason: string;
}

export interface Explanation {
  alert_id?: string;
  summary: string;
  likely_causes: LikelyCause[];
  sources: Source[];
  actions: {
    distributor_note: string;
    officer_note: string;
    asha_visit_list: VisitItem[];
  };
  model: string;
  latency_ms: number;
  grounded?: boolean;
  cached?: boolean;
  search_note?: string;
  search_queries?: string[];
}

export interface ActionApproved {
  approval_id: string;
  alert_id: string;
  action: ActionName;
  approved_by: string;
  created_at: string;
  text: string;
  edited: boolean;
  visit_list?: VisitItem[];
}

export interface AshaVisit extends VisitItem {
  pin?: string;
  alert_id?: string;
  group?: string;
  group_label?: string;
  approved_by?: string;
  approved_at?: string;
  reported?: boolean;
}

export interface AlertUpdate {
  alert_id: string;
  group: string;
  group_label?: string;
  old_confidence: number;
  new_confidence: number;
  old_status?: AlertStatus;
  new_status?: AlertStatus;
  delta?: number;
}

export interface AshaReportResult {
  language: string;
  transcript: string;
  households_visited: number;
  fever: number;
  diarrhoea: number;
  cough: number;
  breathing: number;
  rash: number;
  children_affected: number;
  referred: number;
  water_issue_reported: boolean;
  notes: string;
  alert_id: string | null;
  new_confidence: number | null;
  report_id?: string;
  updates?: AlertUpdate[];
  model?: string;
  latency_ms?: number;
}

/** Audit rows as the backend sends them; older field names are accepted too. */
export interface AuditEntry {
  id?: string;
  audit_id?: string;
  ts?: string;
  at?: string;
  actor: string;
  approved_by?: string;
  kind: string;
  ref_id?: string;
  ref?: string;
  summary?: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  detail?: Record<string, unknown>;
}

export interface Metrics {
  orders_parsed: number;
  lines_parsed: number;
  auto_matched_pct: number;
  uncertain_pct: number;
  avg_latency_ms: number;
  asha_reports: number;
  alerts_confirmed: number;
  orders_approved?: number;
  unknown_pct?: number;
  edit_rate_pct?: number;
  latency_p50_ms?: number;
  latency_p95_ms?: number;
  minutes_saved_est?: number;
  reports_confirming?: number;
  reports_cancelling?: number;
  decoys_suppressed?: number;
  alerts_raised?: number;
}

export interface Locality {
  pin: string;
  locality_id: string;
  name: string;
  landmark: string;
}

export interface Health {
  status: string;
  model_fast: string;
  model_reason: string;
  storage: string;
  signal_backend: string;
  offline: boolean;
  version?: string;
}

export interface Telemetry {
  calls: number;
  by_model: Record<string, number>;
  fallbacks: number;
  avg_latency_ms: number;
  errors?: number;
  offline?: boolean;
  grounded_sources_total: number;
  cache_hits: number;
}

// ---------------------------------------------------------------- extended data (mini contract)

export interface Overview {
  orders_30d: number;
  lines_30d: number;
  chemists_active: number;
  share_by_channel: Record<string, number>;
  stockouts_14d: number;
  avg_clerk_minutes_saved_per_order: number;
  avg_clerk_minutes_saved_basis?: string;
  alerts_open: number;
  alerts_confirmed: number;
  simulated: boolean;
}

export interface BacktestEvent {
  event: string;
  area?: string;
  pin: string | number;
  group: string;
  signal_first: string | null;
  asha_rise: string | null;
  official_date: string | null;
  lead_days_vs_official: number | null;
  lead_days_vs_asha: number | null;
  data_status?: string;
}

export interface BacktestNote {
  event?: string;
  pin?: string | number;
  pins?: Array<string | number>;
  group?: string;
  what?: string;
  note?: string;
  why?: string;
  reason?: string;
  summary?: string;
  cause?: string;
  verdict?: string;
  why_missed?: string;
}

export interface Backtest {
  simulated: boolean;
  note: string;
  rule: string;
  events: BacktestEvent[];
  false_alarms: BacktestNote[];
  missed: BacktestNote[];
}

export interface EnvDay {
  date: string;
  temp_max: number | null;
  temp_min: number | null;
  precip_mm: number | null;
  humidity: number | null;
  pm25: number | null;
  pm10: number | null;
  source: string;
}

export interface Stockout {
  sku_id: string;
  brand: string;
  group: string;
  pins: Array<string | number>;
  chemists: number;
  qty_wanted: number;
  days_of_cover?: number | null;
}

export interface AshaDay {
  date: string;
  households_visited: number;
  fever: number;
  diarrhoea: number;
  cough: number;
  referred: number;
  reports: number;
}

export interface ChemistSendResult {
  message_id: string;
  status: string;
}
