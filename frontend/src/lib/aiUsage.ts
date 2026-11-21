import type { AiUsage } from "../types";

/** Plain-English names for the ledger's job keys. */
export const JOB_LABEL: Record<string, string> = {
  parse_audio: "Voice note to order",
  parse_image: "Handwritten photo to order",
  parse_text: "Typed message to order",
  asha_report: "ASHA voice report to counts",
  explain_grounded: "Web search for causes",
  explain_reason: "Explain and draft actions",
};

export function jobLabel(key: string): string {
  return JOB_LABEL[key] ?? key.replace(/_/g, " ");
}

/** Rupees with sensible precision: under 10 keeps two decimals, under 100 one, above none. */
export function inr(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return `₹${value < 10 ? value.toFixed(2) : value < 100 ? value.toFixed(1) : value.toFixed(0)}`;
}

export function pct(ratio: number): string {
  return `${Math.round((Number.isFinite(ratio) ? ratio : 0) * 100)}%`;
}

export function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Share of the prompt tokens that were served from Gemini's implicit cache, for one job. */
export function cachedShare(bucket: { prompt_tokens: number; cached_tokens: number }): number {
  return bucket.prompt_tokens > 0 ? bucket.cached_tokens / bucket.prompt_tokens : 0;
}

export function hasLiveCalls(u: AiUsage | undefined | null): boolean {
  return !!u && u.totals.calls > 0;
}
