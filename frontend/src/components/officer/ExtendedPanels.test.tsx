import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Backtest } from "../../types";
import { MiniChart } from "../ui/MiniChart";
import { AshaRecentTable, BacktestView, EventTimeline, RealBadge, SimulatedBadge } from "./ExtendedPanels";

const bt: Backtest = {
  simulated: true,
  note: "A replay of a simulated scenario.",
  rule: "7-day units over baseline.",
  events: [
    {
      event: "E1_diarrhoea_waterborne",
      pin: 400022,
      group: "diarrhoea",
      signal_first: "2026-11-16",
      asha_rise: "2026-11-18",
      official_date: "2026-11-25",
      lead_days_vs_official: 9,
      lead_days_vs_asha: 2,
      data_status: "projected_sim",
    },
  ],
  false_alarms: [{ what: "Citywide respiratory bump in the bad-air week." }],
  missed: [{ what: "Typhoid cluster in Dharavi." }],
};

describe("BacktestView", () => {
  const html = renderToStaticMarkup(<BacktestView data={bt} areaOf={() => "Sion"} />);
  it("shows the timeline, leads and the honest lines", () => {
    expect(html).toContain("Sion");
    expect(html).toContain("9 days before the official report");
    expect(html).toContain("projected");
    expect(html).toContain("False alarm in the scenario");
    expect(html).toContain("Missed event in the scenario");
  });
  it("has a text alternative for the drawing", () => {
    expect(html).toContain('role="img"');
    expect(html).toContain("Pharmacy signal 16 Nov");
  });
  it("copes with no events", () => {
    const empty = renderToStaticMarkup(<BacktestView data={{ ...bt, events: [], false_alarms: [], missed: [] }} areaOf={() => "x"} />);
    expect(empty).toContain("No back-test events");
  });
});

describe("EventTimeline", () => {
  it("says when ASHA has not risen yet", () => {
    const html = renderToStaticMarkup(
      <ul>
        <EventTimeline ev={{ ...bt.events[0], asha_rise: null, lead_days_vs_asha: null }} area="Sion" />
      </ul>,
    );
    expect(html).toContain("not visible yet");
  });
});

describe("badges", () => {
  it("label simulated and real data in words", () => {
    expect(renderToStaticMarkup(<SimulatedBadge />)).toContain("SIMULATED");
    expect(renderToStaticMarkup(<RealBadge />)).toContain("REAL (Open-Meteo)");
  });
});

describe("MiniChart", () => {
  const dates = ["2026-11-01", "2026-11-02", "2026-11-03"];
  it("renders a labelled chart with a hidden data table", () => {
    const html = renderToStaticMarkup(<MiniChart dates={dates} series={[{ name: "PM2.5", values: [10, 20, null], color: "var(--watch)" }]} label="Air test" />);
    expect(html).toContain('aria-label="Air test"');
    expect(html).toContain("<table>");
    expect(html).toContain("n/a");
  });
  it("says so when there is no data", () => {
    const html = renderToStaticMarkup(<MiniChart dates={dates} series={[{ name: "x", values: [null, null, null], color: "red" }]} label="x" />);
    expect(html).toContain("No data for this period");
  });
});

describe("AshaRecentTable", () => {
  it("lists days with Hindi column heads", () => {
    const html = renderToStaticMarkup(
      <AshaRecentTable
        rows={[{ date: "2026-11-19", households_visited: 12, fever: 2, diarrhoea: 1, cough: 0, referred: 0, reports: 1 }]}
        headers={{ day: "दिन", homes: "घर देखे", fever: "बुखार", diarrhoea: "दस्त", cough: "खाँसी" }}
      />,
    );
    expect(html).toContain("बुखार");
    expect(html).toContain("12");
  });
});
