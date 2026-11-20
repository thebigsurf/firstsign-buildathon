import type {
  Locality,
  ActionApproved,
  ActionName,
  Alert,
  Asha,
  AshaReportResult,
  AshaVisit,
  AuditEntry,
  CatalogueItem,
  Chemist,
  Distributor,
  Explanation,
  Group,
  Health,
  InboxMessage,
  Metrics,
  OrderLine,
  OrderRecord,
  ParsedOrder,
  Pincode,
  RadarItem,
  SignalResponse,
  Telemetry,
  VisitItem,
} from "./types";

const BASE = "/api";

/** An error from the API (or from reaching it), with a plain-English message. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, message: string, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function messageFromBody(body: unknown): string {
  if (typeof body === "string") return body;
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (typeof b.message === "string") return b.message;
    if (typeof b.detail === "string") return b.detail;
    if (b.error && typeof b.error === "object") {
      const e = b.error as Record<string, unknown>;
      if (typeof e.message === "string") return e.message;
    }
    if (Array.isArray(b.detail)) {
      return b.detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join("; ");
    }
  }
  return "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "We could not reach the server.", err instanceof Error ? err.message : String(err));
  }
  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    const detail = messageFromBody(body) || res.statusText;
    const friendly =
      res.status === 404
        ? "We could not find that."
        : res.status >= 500
          ? "The server had a problem. Please try again."
          : detail || "That request was not accepted.";
    throw new ApiError(res.status, friendly, `${res.status} ${detail}`.trim());
  }
  if (typeof body === "string") {
    throw new ApiError(res.status, "The server sent something we did not expect.", body.slice(0, 200));
  }
  return body as T;
}

function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal });
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

function postForm<T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { method: "POST", body: form, signal });
}

export interface ParseInput {
  chemistId: string;
  messageId?: string | null;
  file?: Blob | null;
  fileName?: string;
  text?: string;
}

export interface OrderPayload {
  chemist_id: string;
  message_id: string | null;
  lines: OrderLine[];
  approved_by: string;
  /** Lines exactly as the AI read them, so the log can show every edit. */
  original_lines?: OrderLine[];
}

export interface ReportInput {
  ashaId: string;
  localityId: string;
  file?: Blob | null;
  fileName?: string;
  text?: string;
}

export const api = {
  health: (signal?: AbortSignal) => get<Health>("/health", signal),
  telemetry: (signal?: AbortSignal) => get<Telemetry>("/telemetry", signal),
  catalogue: (signal?: AbortSignal) => get<CatalogueItem[]>("/catalogue", signal),
  groups: (signal?: AbortSignal) => get<Group[]>("/groups", signal),
  pincodes: (signal?: AbortSignal) => get<Pincode[]>("/pincodes", signal),
  chemists: (signal?: AbortSignal) => get<Chemist[]>("/chemists", signal),
  distributor: (signal?: AbortSignal) => get<Distributor>("/distributor", signal),
  ashas: (signal?: AbortSignal) => get<Asha[]>("/asha", signal),
  inbox: (signal?: AbortSignal) => get<InboxMessage[]>("/inbox", signal),
  metrics: (signal?: AbortSignal) => get<Metrics>("/metrics", signal),
  orders: (signal?: AbortSignal) => get<OrderRecord[]>("/orders?limit=200", signal),
  audit: (signal?: AbortSignal) => get<AuditEntry[]>("/audit", signal),
  signal: (days = 30, signal?: AbortSignal) => get<SignalResponse>(`/signal?days=${days}`, signal),
  alerts: (signal?: AbortSignal) => get<Alert[]>("/alerts", signal),
  alert: (id: string, signal?: AbortSignal) => get<Alert>(`/alerts/${encodeURIComponent(id)}`, signal),
  radar: (signal?: AbortSignal) => get<RadarItem[]>("/radar", signal),
  localities: (pin: string, signal?: AbortSignal) => get<Locality[]>(`/localities?pin=${encodeURIComponent(pin)}`, signal),
  ashaVisits: (ashaId: string, signal?: AbortSignal) =>
    get<AshaVisit[]>(`/asha/visits?asha_id=${encodeURIComponent(ashaId)}`, signal),

  parseOrder(input: ParseInput, signal?: AbortSignal): Promise<ParsedOrder> {
    const form = new FormData();
    form.append("chemist_id", input.chemistId);
    if (input.messageId) form.append("message_id", input.messageId);
    if (input.file) form.append("file", input.file, input.fileName ?? "upload");
    if (input.text) form.append("text", input.text);
    return postForm<ParsedOrder>("/orders/parse", form, signal);
  },

  saveOrder: (payload: OrderPayload) => postJson<{ order_id: string }>("/orders", payload),

  explain: (alertId: string, refresh = false, signal?: AbortSignal) =>
    postJson<Explanation>("/agent/explain", { alert_id: alertId, refresh }, signal),

  approveAction: (body: {
    alert_id: string;
    action: ActionName;
    approved_by: string;
    edited_text?: string;
    /** The visit list in the order the officer left it (see docs/CONTRACT_REQUESTS.md). */
    visit_list?: VisitItem[];
  }) => postJson<ActionApproved>("/actions/approve", body),

  ashaReport(input: ReportInput, signal?: AbortSignal): Promise<AshaReportResult> {
    const form = new FormData();
    form.append("asha_id", input.ashaId);
    form.append("locality_id", input.localityId);
    if (input.file) form.append("file", input.file, input.fileName ?? "report.webm");
    if (input.text) form.append("text", input.text);
    return postForm<AshaReportResult>("/asha/report", form, signal);
  },

  /** Where to fetch the sample media for an inbox message. */
  mediaUrl(message: InboxMessage): string | null {
    if (message.media_url) return message.media_url;
    return message.media ? `${BASE}/inbox/${encodeURIComponent(message.id)}/media` : null;
  },
};
