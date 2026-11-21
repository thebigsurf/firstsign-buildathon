/** Pure helpers for the extended-data panels (back-test, weather, ASHA history, stock-outs). */
import type { AshaDay, BacktestEvent, BacktestNote, EnvDay } from "../types";

const DAY_MS = 86_400_000;

/** Whole days from `from` to `to` (both YYYY-MM-DD or ISO). Null if either is missing or invalid. */
export function dayDiff(from: string | null | undefined, to: string | null | undefined): number | null {
  if (!from || !to) return null;
  const a = Date.parse(from.slice(0, 10));
  const b = Date.parse(to.slice(0, 10));
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.round((b - a) / DAY_MS);
}

export interface TimelineMarker {
  key: "signal" | "asha" | "official";
  label: string;
  date: string;
  /** Days after the first pharmacy signal. */
  offset: number;
  /** 0..1 position on the track. */
  pos: number;
}

/** Places the three dates of one event on a 0..1 track, signal first. Missing dates are skipped. */
export function eventMarkers(ev: BacktestEvent): TimelineMarker[] {
  const raw: Array<Omit<TimelineMarker, "pos" | "offset"> | null> = [
    ev.signal_first ? { key: "signal", label: "Pharmacy signal", date: ev.signal_first } : null,
    ev.asha_rise ? { key: "asha", label: "ASHA rise", date: ev.asha_rise } : null,
    ev.official_date ? { key: "official", label: "Official report", date: ev.official_date } : null,
  ];
  const present = raw.filter((m): m is Omit<TimelineMarker, "pos" | "offset"> => m !== null);
  if (present.length === 0) return [];
  const base = ev.signal_first ?? present[0].date;
  const withOffset = present.map((m) => ({ ...m, offset: dayDiff(base, m.date) ?? 0 }));
  const min = Math.min(...withOffset.map((m) => m.offset), 0);
  const max = Math.max(...withOffset.map((m) => m.offset), 1);
  const span = Math.max(1, max - min);
  return withOffset.map((m) => ({ ...m, pos: (m.offset - min) / span }));
}

/** One honest sentence about a lead time. */
export function leadSentence(days: number | null, versus: string, projected = false): string {
  if (days === null) return `No ${versus} date yet`;
  const tag = projected ? " (projected, simulated)" : "";
  if (days === 0) return `Same day as the ${versus}${tag}`;
  const n = Math.abs(days);
  const unit = n === 1 ? "day" : "days";
  return days > 0 ? `${n} ${unit} before the ${versus}${tag}` : `${n} ${unit} after the ${versus}${tag}`;
}

export function isProjected(ev: BacktestEvent): boolean {
  return (ev.data_status ?? "").includes("projected");
}

/** Text of a false-alarm or missed-event row, whatever field the backend used. */
export function noteText(n: BacktestNote | string): string {
  if (typeof n === "string") return n;
  const body = [n.what, n.summary, n.note, n.cause, n.why, n.why_missed, n.reason, n.verdict].filter((x): x is string => typeof x === "string" && x.length > 0);
  if (body.length === 0) return [n.event, n.group].filter(Boolean).join(" ");
  const stop = (t: string): string => (/[.!?'"]$/.test(t) ? t : `${t}.`);
  const cap = (t: string): string => t.charAt(0).toUpperCase() + t.slice(1);
  return [n.event && !body.includes(n.event) ? n.event : "", ...body].filter(Boolean).map((t) => stop(cap(t))).join(" ");
}

/** Many pins can share one false alarm; show it once with the pin codes listed. */
export function groupNotes(list: BacktestNote[]): Array<{ text: string; pins: string[] }> {
  const map = new Map<string, { text: string; pins: string[] }>();
  for (const n of list) {
    const text = noteText(n);
    const row = map.get(text) ?? { text, pins: [] };
    const pins = n.pins ?? (n.pin !== undefined ? [n.pin] : []);
    for (const p of pins) if (!row.pins.includes(String(p))) row.pins.push(String(p));
    map.set(text, row);
  }
  return [...map.values()];
}

export function eventTitle(ev: BacktestEvent): string {
  return ev.event.replace(/^E\d+_/, "").replace(/_/g, " ");
}

export interface Series {
  name: string;
  values: Array<number | null>;
  color: string;
  dash?: string;
}

/** Last `n` entries, oldest first, whatever order the API used. */
export function lastDays<T extends { date: string }>(rows: T[], n: number): T[] {
  return [...rows].sort((a, b) => a.date.localeCompare(b.date)).slice(-n);
}

export function envSeries(rows: EnvDay[]): { dates: string[]; temp: Series[]; rain: Series[]; air: Series[] } {
  const r = lastDays(rows, 30);
  return {
    dates: r.map((d) => d.date),
    temp: [
      { name: "Max temp (C)", values: r.map((d) => d.temp_max), color: "var(--alert)" },
      { name: "Min temp (C)", values: r.map((d) => d.temp_min), color: "var(--accent)", dash: "4 3" },
    ],
    rain: [{ name: "Rain (mm)", values: r.map((d) => d.precip_mm), color: "var(--accent)" }],
    air: [
      { name: "PM2.5", values: r.map((d) => d.pm25), color: "var(--watch)" },
      { name: "PM10", values: r.map((d) => d.pm10), color: "var(--muted)", dash: "4 3" },
    ],
  };
}

export function ashaSeries(rows: AshaDay[]): { dates: string[]; series: Series[] } {
  const r = lastDays(rows, 30);
  return {
    dates: r.map((d) => d.date),
    series: [
      { name: "Fever", values: r.map((d) => d.fever), color: "var(--alert)" },
      { name: "Diarrhoea", values: r.map((d) => d.diarrhoea), color: "var(--accent)", dash: "4 3" },
      { name: "Cough", values: r.map((d) => d.cough), color: "var(--watch)", dash: "1 3" },
    ],
  };
}

export function sumDays(rows: AshaDay[]): { households: number; reports: number; referred: number } {
  return rows.reduce(
    (a, d) => ({ households: a.households + d.households_visited, reports: a.reports + d.reports, referred: a.referred + d.referred }),
    { households: 0, reports: 0, referred: 0 },
  );
}

export const CHANNEL_LABEL: Record<string, string> = {
  voice_note: "Voice note",
  photo: "Photo of list",
  whatsapp_text: "WhatsApp text",
  salesman: "Salesman",
  phone_call: "Phone call",
  app: "App",
};

/** Channel shares sorted high to low, as whole percents that add to roughly 100. */
export function channelShares(share: Record<string, number>): Array<{ key: string; label: string; pct: number }> {
  const total = Object.values(share).reduce((a, b) => a + b, 0);
  if (total <= 0) return [];
  return Object.entries(share)
    .map(([key, v]) => ({ key, label: CHANNEL_LABEL[key] ?? key.replace(/_/g, " "), pct: Math.round((v / total) * 100) }))
    .sort((a, b) => b.pct - a.pct);
}

export function coverText(days: number | null | undefined): string | null {
  if (days === null || days === undefined || Number.isNaN(days)) return null;
  if (days <= 0) return "0 days of cover";
  return `${Math.round(days * 10) / 10} days of cover`;
}
