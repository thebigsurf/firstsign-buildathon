import { describe, expect, it } from "vitest";
import { cachedShare, inr, jobLabel, pct, seconds } from "./aiUsage";

describe("aiUsage helpers", () => {
  it("formats rupees with two decimals under 10 and one above", () => {
    expect(inr(0.2516)).toBe("₹0.25");
    expect(inr(12.34)).toBe("₹12.3");
    expect(inr(Number.NaN)).toBe("-");
  });
  it("formats percentages, seconds and labels", () => {
    expect(pct(0.7036)).toBe("70%");
    expect(pct(Number.NaN)).toBe("0%");
    expect(seconds(5757)).toBe("5.8 s");
    expect(jobLabel("parse_audio")).toBe("Voice note to order");
    expect(jobLabel("some_new_job")).toBe("some new job");
  });
  it("computes the cached share of prompt tokens", () => {
    expect(cachedShare({ prompt_tokens: 8000, cached_tokens: 6000 })).toBe(0.75);
    expect(cachedShare({ prompt_tokens: 0, cached_tokens: 0 })).toBe(0);
  });
});
