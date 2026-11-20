import type { Level } from "../types";

export const cx = (...parts: Array<string | false | null | undefined>): string => parts.filter(Boolean).join(" ");

const TZ = "Asia/Kolkata";

function toDate(iso: string): Date | null {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = toDate(iso);
  if (!d) return iso;
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: TZ });
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = toDate(iso.length === 10 ? `${iso}T00:00:00+05:30` : iso);
  if (!d) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: TZ });
}

export function fmtShortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = toDate(iso.length === 10 ? `${iso}T00:00:00+05:30` : iso);
  if (!d) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: TZ });
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = toDate(iso);
  if (!d) return iso;
  return `${fmtShortDate(iso)}, ${fmtTime(iso)}`;
}

export function daysSince(iso: string, asOf?: string): number {
  const a = toDate(iso.length === 10 ? `${iso}T00:00:00+05:30` : iso);
  const b = asOf ? toDate(asOf.length === 10 ? `${asOf}T00:00:00+05:30` : asOf) : new Date();
  if (!a || !b) return 0;
  return Math.max(0, Math.round((b.getTime() - a.getTime()) / 86_400_000));
}

export const pct = (v: number): string => `${Math.round(v * 100)}%`;
export const ratioText = (v: number): string => `${v.toFixed(1)}x`;
export const plural = (n: number, one: string, many = `${one}s`): string => `${n} ${n === 1 ? one : many}`;

export type ConfWord = "High" | "Moderate" | "Low";

export function confidenceWord(c: number): ConfWord {
  if (c >= 0.75) return "High";
  if (c >= 0.45) return "Moderate";
  return "Low";
}

export const LEVEL_RANK: Record<Level, number> = { alert: 2, watch: 1, normal: 0 };

export function initials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  return (words[0]?.[0] ?? "?") + (words[1]?.[0] ?? "");
}

export function langOf(code: string | undefined | null): "hi" | "mr" | "en" {
  return code === "mr" ? "mr" : code === "en" ? "en" : "hi";
}

export function langName(code: string | undefined | null): string {
  return { hi: "Hindi", mr: "Marathi", en: "English" }[langOf(code)];
}

export function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function isSafeHttpUrl(url: string): boolean {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export function downloadText(filename: string, text: string, mime = "text/csv"): void {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function csvCell(v: unknown): string {
  const s = typeof v === "string" ? v : JSON.stringify(v ?? "");
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function safeStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readStored(key: string): string | null {
  try {
    return safeStorage()?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string): void {
  try {
    safeStorage()?.setItem(key, value);
  } catch {
    /* storage unavailable: the setting just won't persist */
  }
}
