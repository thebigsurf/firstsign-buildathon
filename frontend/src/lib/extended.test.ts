import { describe, expect, it } from "vitest";
import {
  ashaSeries,
  channelShares,
  coverText,
  dayDiff,
  envSeries,
  eventMarkers,
  isProjected,
  leadSentence,
  noteText,
  sumDays,
} from "./extended";
import { overviewTiles } from "../components/OverviewTiles";
import { baseName, pickSamples } from "./chemistSamples";
import type { AshaDay, BacktestEvent, EnvDay, InboxMessage } from "../types";

const ev: BacktestEvent = {
  event: "E1_diarrhoea_waterborne",
  pin: 400022,
  group: "diarrhoea",
  signal_first: "2026-11-16",
  asha_rise: "2026-11-18",
  official_date: "2026-11-25",
  lead_days_vs_official: 9,
  lead_days_vs_asha: 2,
  data_status: "projected_sim",
};

describe("dayDiff", () => {
  it("counts whole days", () => expect(dayDiff("2026-11-16", "2026-11-25")).toBe(9));
  it("is null when a date is missing or bad", () => {
    expect(dayDiff(null, "2026-11-25")).toBeNull();
    expect(dayDiff("nope", "2026-11-25")).toBeNull();
  });
});

describe("eventMarkers", () => {
  it("puts the signal first and the official report last", () => {
    const m = eventMarkers(ev);
    expect(m.map((x) => x.key)).toEqual(["signal", "asha", "official"]);
    expect(m[0].pos).toBe(0);
    expect(m[2].pos).toBe(1);
    expect(m[1].offset).toBe(2);
  });
  it("skips dates that do not exist yet", () => {
    const m = eventMarkers({ ...ev, asha_rise: null, official_date: null });
    expect(m).toHaveLength(1);
    expect(m[0].key).toBe("signal");
  });
  it("returns nothing for an empty event", () => {
    expect(eventMarkers({ ...ev, signal_first: null, asha_rise: null, official_date: null })).toEqual([]);
  });
});

describe("leadSentence", () => {
  it("says before, after, same day and missing", () => {
    expect(leadSentence(9, "official report")).toBe("9 days before the official report");
    expect(leadSentence(1, "ASHA rise")).toBe("1 day before the ASHA rise");
    expect(leadSentence(-3, "ASHA rise")).toBe("3 days after the ASHA rise");
    expect(leadSentence(0, "ASHA rise")).toBe("Same day as the ASHA rise");
    expect(leadSentence(null, "official report")).toBe("No official report date yet");
  });
  it("marks projected leads as simulated", () => {
    expect(leadSentence(9, "official report", true)).toContain("projected, simulated");
    expect(isProjected(ev)).toBe(true);
    expect(isProjected({ ...ev, data_status: "observed_sim" })).toBe(false);
  });
});

describe("noteText", () => {
  it("reads whichever field the backend used", () => {
    expect(noteText("plain")).toBe("plain");
    expect(noteText({ what: "Citywide respiratory bump", why: "Bad-air week" })).toBe("Citywide respiratory bump. Bad-air week.");
    expect(noteText({ event: "typhoid", group: "fever" })).toBe("typhoid fever");
  });
});

describe("series helpers", () => {
  const env: EnvDay[] = [
    { date: "2026-11-02", temp_max: 33, temp_min: 24, precip_mm: 0, humidity: 60, pm25: 40, pm10: 80, source: "open-meteo" },
    { date: "2026-11-01", temp_max: 32, temp_min: 23, precip_mm: 2, humidity: 61, pm25: 38, pm10: 70, source: "open-meteo" },
  ];
  it("sorts weather oldest first", () => {
    const s = envSeries(env);
    expect(s.dates).toEqual(["2026-11-01", "2026-11-02"]);
    expect(s.temp[0].values).toEqual([32, 33]);
    expect(s.rain[0].values).toEqual([2, 0]);
  });
  const asha: AshaDay[] = [
    { date: "2026-11-01", households_visited: 10, fever: 1, diarrhoea: 2, cough: 0, referred: 1, reports: 1 },
    { date: "2026-11-02", households_visited: 12, fever: 0, diarrhoea: 3, cough: 1, referred: 0, reports: 2 },
  ];
  it("builds ASHA series and totals", () => {
    expect(ashaSeries(asha).series.map((s) => s.name)).toEqual(["Fever", "Diarrhoea", "Cough"]);
    expect(sumDays(asha)).toEqual({ households: 22, reports: 3, referred: 1 });
  });
});

describe("channelShares", () => {
  it("returns percents high to low and tolerates empty input", () => {
    const r = channelShares({ voice_note: 30, photo: 10, salesman: 60 });
    expect(r.map((x) => x.key)).toEqual(["salesman", "voice_note", "photo"]);
    expect(r[0].pct).toBe(60);
    expect(channelShares({})).toEqual([]);
  });
});

describe("cover text", () => {
  it("words days of cover", () => {
    expect(coverText(0)).toBe("0 days of cover");
    expect(coverText(2.46)).toBe("2.5 days of cover");
    expect(coverText(null)).toBeNull();
  });
});

describe("overviewTiles", () => {
  const base = {
    orders_30d: 4200,
    lines_30d: 16000,
    chemists_active: 90,
    stockouts_14d: 800,
    avg_clerk_minutes_saved_per_order: 3.24,
    alerts_open: 0,
    alerts_confirmed: 0,
  };
  it("never shows a zero tile and labels the estimate", () => {
    const t = overviewTiles(base);
    expect(t.some((x) => x.value === "0")).toBe(false);
    const saved = t.find((x) => x.label.includes("minutes"));
    expect(saved?.value).toBe("~3.2");
    expect(saved?.hint).toContain("estimate");
    expect(t[0].value).toBe("4,200");
  });
});

describe("pickSamples", () => {
  const msg = (id: string, type: InboxMessage["type"], media: string | null): InboxMessage => ({
    id,
    chemist_id: "CH001",
    received_at: "2026-11-20T07:12:00+05:30",
    type,
    media,
    status: "new",
  });
  it("takes at most 3 voice notes and 2 photos, skipping text", () => {
    const list = [
      msg("1", "voice", "samples/order_01.mp3"),
      msg("2", "voice", "samples/order_02.mp3"),
      msg("3", "voice", "samples/order_03.mp3"),
      msg("4", "voice", "samples/order_04.mp3"),
      msg("5", "photo", "samples/order_05.jpg"),
      msg("6", "photo", "samples/order_06.jpg"),
      msg("7", "photo", "samples/order_07.jpg"),
      msg("8", "text", null),
    ];
    const s = pickSamples(list, () => "Lifeline");
    expect(s.filter((x) => x.kind === "audio")).toHaveLength(3);
    expect(s.filter((x) => x.kind === "image")).toHaveLength(2);
    expect(s[0].label).toContain("Lifeline");
    expect(s[0].url).toBe("/api/inbox/1/media");
  });
  it("keeps the original file name so offline samples match", () => {
    expect(baseName("samples/order_01.mp3")).toBe("order_01.mp3");
  });
});
