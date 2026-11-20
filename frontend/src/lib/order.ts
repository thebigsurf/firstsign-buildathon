import type { CatalogueItem, LineStatus, OrderLine, ParsedOrder } from "../types";

export type Resolution = "none" | "confirmed" | "changed" | "not_available" | "removed";

/** One order line while the clerk works on it. `ai` is what the AI read, untouched. */
export interface EditableLine {
  key: string;
  line: OrderLine;
  ai: OrderLine | null;
  resolution: Resolution;
}

let counter = 0;
const nextKey = (): string => `ln-${Date.now().toString(36)}-${counter++}`;

export function toEditable(parsed: ParsedOrder): EditableLine[] {
  return parsed.lines.map((line) => ({
    key: nextKey(),
    line: { ...line },
    ai: { ...line, alternatives: [...line.alternatives] },
    resolution: "none" as Resolution,
  }));
}

export function lineFromCatalogue(item: CatalogueItem, qty: number, rawText: string): OrderLine {
  return {
    raw_text: rawText,
    sku_id: item.sku_id,
    brand: item.brand,
    strength: item.strength,
    form: item.form,
    molecule: item.molecule,
    group: item.group,
    qty,
    unit: item.unit,
    confidence: 1,
    status: "matched",
    alternatives: [],
  };
}

export function addedLine(item: CatalogueItem, qty = 1): EditableLine {
  return {
    key: nextKey(),
    line: lineFromCatalogue(item, qty, "Added by clerk"),
    ai: null,
    resolution: "changed",
  };
}

/** The AI was unsure (or found nothing) and the clerk has not dealt with it yet. */
export function needsCheck(l: EditableLine): boolean {
  if (l.resolution !== "none") return false;
  return l.ai !== null && l.ai.status !== "matched";
}

export function isActive(l: EditableLine): boolean {
  return l.resolution !== "removed" && l.resolution !== "not_available";
}

export function qtyChanged(l: EditableLine): boolean {
  return l.ai !== null && l.line.qty !== l.ai.qty;
}

export function productChanged(l: EditableLine): boolean {
  return l.ai !== null && l.line.sku_id !== l.ai.sku_id;
}

export function isEdited(l: EditableLine): boolean {
  return l.ai === null || qtyChanged(l) || productChanged(l);
}

export interface LineCounts {
  total: number;
  matched: number;
  uncertain: number;
  unknown: number;
  pending: number;
  edited: number;
  notAvailable: number;
}

export function countLines(lines: EditableLine[]): LineCounts {
  const c: LineCounts = { total: 0, matched: 0, uncertain: 0, unknown: 0, pending: 0, edited: 0, notAvailable: 0 };
  for (const l of lines) {
    if (l.resolution === "removed") continue;
    if (l.resolution === "not_available") {
      c.notAvailable += 1;
      continue;
    }
    c.total += 1;
    const status: LineStatus = l.ai ? l.ai.status : "matched";
    if (status === "matched") c.matched += 1;
    else if (status === "uncertain") c.uncertain += 1;
    else c.unknown += 1;
    if (needsCheck(l)) c.pending += 1;
    if (isEdited(l)) c.edited += 1;
  }
  return c;
}

/** One plain sentence built from the API's own alternatives; nothing is invented. */
export function uncertaintyReason(line: OrderLine): string {
  if (line.reason) return line.reason;
  if (line.note) return line.note;
  const alts = [...line.alternatives].sort((a, b) => b.score - a.score).slice(0, 2);
  if (line.status === "unknown") {
    return alts.length ? `Nothing matched well. Closest: ${alts.map((a) => a.brand).join(" or ")}.` : "Nothing in your catalogue matched this.";
  }
  if (alts.length >= 2) return `Heard "${line.raw_text}": could be ${alts[0].brand} or ${alts[1].brand}.`;
  if (alts.length === 1) return `Heard "${line.raw_text}": best guess is ${alts[0].brand}.`;
  return `Heard "${line.raw_text}": not sure which product this is.`;
}

function norm(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/** Higher is better; 0 means no match. Substring and token matches, then loose subsequence. */
export function searchScore(item: CatalogueItem, query: string): number {
  const q = norm(query);
  if (!q) return 0.01;
  const brand = norm(item.brand);
  const hay = norm(`${item.brand} ${item.strength} ${item.molecule} ${(item.aliases ?? "").replace(/\|/g, " ")}`);
  if (brand.startsWith(q)) return 3;
  if (hay.includes(q)) return 2;
  const tokens = q.split(" ");
  if (tokens.every((t) => hay.includes(t))) return 1.5;
  const compact = q.replace(/ /g, "");
  let i = 0;
  for (const ch of norm(item.brand).replace(/ /g, "")) {
    if (ch === compact[i]) i += 1;
  }
  return i === compact.length && compact.length >= 3 ? 1 : 0;
}

export function searchCatalogue(items: CatalogueItem[], query: string, limit = 8): CatalogueItem[] {
  return items
    .map((item) => ({ item, score: searchScore(item, query) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score || a.item.brand.localeCompare(b.item.brand))
    .slice(0, limit)
    .map((r) => r.item);
}

export function productLabel(line: OrderLine): string {
  if (!line.brand) return "";
  return [line.brand, line.strength, line.form].filter(Boolean).join(" ");
}

export interface Segment {
  text: string;
  hit: boolean;
}

/** Split a transcript into plain text and the stretches that belong to lines the AI was unsure of. */
export function highlightSegments(text: string, phrases: string[]): Segment[] {
  const wanted = phrases.map((p) => p.trim()).filter((p) => p.length >= 3);
  if (!text || wanted.length === 0) return [{ text, hit: false }];
  const escaped = wanted.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return parts
    .filter((p) => p !== "")
    .map((p) => ({ text: p, hit: wanted.some((w) => w.toLowerCase() === p.toLowerCase()) }));
}

/** An approved order shown read-only: every line is final, nothing is flagged. */
export function editableFromRecord(lines: OrderLine[]): EditableLine[] {
  return lines.map((line) => ({ key: nextKey(), line, ai: { ...line, status: "matched" as LineStatus }, resolution: "none" as Resolution }));
}

export interface Work {
  phase: "parsing" | "ready" | "error" | "approved";
  parsed: ParsedOrder | null;
  lines: EditableLine[];
  dismissedNA: string[];
  error: { message: string; detail: string } | null;
  startedAt: number;
  approvedBy?: string;
  approvedAt?: string;
}
