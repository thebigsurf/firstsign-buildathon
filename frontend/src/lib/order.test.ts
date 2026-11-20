import { describe, expect, it } from "vitest";
import {
  countLines,
  highlightSegments,
  needsCheck,
  searchCatalogue,
  toEditable,
  uncertaintyReason,
} from "./order";
import type { CatalogueItem, OrderLine, ParsedOrder } from "../types";

const line = (over: Partial<OrderLine>): OrderLine => ({
  raw_text: "dolo",
  sku_id: "SKU1",
  brand: "Dolo 650",
  strength: "650 mg",
  form: "tablet",
  molecule: "Paracetamol",
  group: "fever",
  qty: 10,
  unit: "strip",
  confidence: 0.9,
  status: "matched",
  alternatives: [],
  ...over,
});

const parsed = (lines: OrderLine[]): ParsedOrder => ({
  message_id: "m1",
  chemist_id: "CH1",
  language: "hi",
  transcript: "",
  lines,
  not_available: [],
  notes: "",
  model: "test",
  latency_ms: 1,
});

const cat = (id: string, brand: string, aliases = ""): CatalogueItem => ({
  sku_id: id,
  brand,
  strength: "40 mg",
  form: "tablet",
  pack: "15 tablets",
  molecule: "Pantoprazole",
  group: "other",
  unit: "strip",
  aliases,
});

describe("order lines", () => {
  it("flags uncertain and unknown lines until the clerk resolves them", () => {
    const lines = toEditable(
      parsed([line({}), line({ status: "uncertain", confidence: 0.5 }), line({ status: "unknown", sku_id: null, brand: null })]),
    );
    expect(lines.filter(needsCheck)).toHaveLength(2);
    const counts = countLines(lines);
    expect(counts).toMatchObject({ total: 3, matched: 1, uncertain: 1, unknown: 1, pending: 2 });
    lines[1].resolution = "confirmed";
    expect(countLines(lines).pending).toBe(1);
  });

  it("builds the reason sentence only from the alternatives it was given", () => {
    const l = line({
      status: "uncertain",
      raw_text: "pan di",
      alternatives: [
        { sku_id: "A", brand: "Pan-D 40", score: 0.8 },
        { sku_id: "B", brand: "Pantop-D 40", score: 0.7 },
      ],
    });
    expect(uncertaintyReason(l)).toBe('Heard "pan di": could be Pan-D 40 or Pantop-D 40.');
    expect(uncertaintyReason(line({ status: "unknown", alternatives: [] }))).toBe("Nothing in your catalogue matched this.");
  });
});

describe("catalogue search", () => {
  const items = [cat("1", "Pan-D 40", "pan d|pantop d"), cat("2", "Pantop 40"), cat("3", "Dolo 650")];
  it("finds by brand prefix, alias and loose letters", () => {
    expect(searchCatalogue(items, "pan")[0].sku_id).toBe("1");
    expect(searchCatalogue(items, "pantop d").map((i) => i.sku_id)).toContain("1");
    expect(searchCatalogue(items, "dlo").map((i) => i.sku_id)).toContain("3");
    expect(searchCatalogue(items, "zzzz")).toHaveLength(0);
  });
});

describe("transcript highlighting", () => {
  it("marks the words that belong to unsure lines", () => {
    const segs = highlightSegments("bhaiya pan di das strip aur dolo", ["pan di"]);
    expect(segs.find((s) => s.hit)?.text).toBe("pan di");
    expect(segs.map((s) => s.text).join("")).toBe("bhaiya pan di das strip aur dolo");
  });
});
