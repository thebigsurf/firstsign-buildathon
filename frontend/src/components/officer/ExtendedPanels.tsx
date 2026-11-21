import { CloudSun, FlaskConical } from "lucide-react";
import { useState } from "react";
import { api } from "../../api";
import { fmtShortDate } from "../../lib/format";
import {
  ashaSeries,
  envSeries,
  eventMarkers,
  eventTitle,
  groupNotes,
  isProjected,
  leadSentence,
  sumDays,
  type TimelineMarker,
} from "../../lib/extended";
import { useAsync } from "../../lib/hooks";
import { useRefData } from "../../lib/refdata";
import type { AshaDay, Backtest, BacktestEvent } from "../../types";
import { Badge, PinChip } from "../ui/Badge";
import { MiniChart } from "../ui/MiniChart";
import { ErrorPanel, Skeleton } from "../ui/States";

export function SimulatedBadge() {
  return (
    <Badge className="bg-watchBg text-watch" icon={FlaskConical}>
      SIMULATED
    </Badge>
  );
}

export function RealBadge({ children = "REAL (Open-Meteo)" }: { children?: string }) {
  return (
    <Badge className="bg-normalBg text-normal" icon={CloudSun}>
      {children}
    </Badge>
  );
}

const MARK_STYLE: Record<TimelineMarker["key"], { fill: string; short: string }> = {
  signal: { fill: "var(--accent)", short: "Signal" },
  asha: { fill: "var(--watch)", short: "ASHA" },
  official: { fill: "var(--alert)", short: "Official" },
};

/** One event on a day-scale track: pharmacy signal first, then ASHA, then the official report. */
export function EventTimeline({ ev, area }: { ev: BacktestEvent; area: string }) {
  const marks = eventMarkers(ev);
  const projected = isProjected(ev);
  const label = `${eventTitle(ev)} in ${area}: ${marks.map((m) => `${m.label} ${fmtShortDate(m.date)}`).join(", ")}.`;
  return (
    <li className="rounded-lg border border-border bg-surface p-3">
      <p className="m-0 flex flex-wrap items-center gap-2 font-semibold">
        {area} <PinChip pin={String(ev.pin)} />
        <span className="font-normal capitalize text-muted">{eventTitle(ev)}</span>
      </p>
      {marks.length > 0 && (
        <div role="img" aria-label={label} className="relative mx-2 my-3 h-4">
          <span aria-hidden="true" className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 bg-borderStrong" />
          {marks.map((m) => (
            <span
              key={m.key}
              aria-hidden="true"
              className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface"
              style={{ left: `${m.pos * 100}%`, background: MARK_STYLE[m.key].fill }}
            />
          ))}
        </div>
      )}
      <ul className="m-0 grid list-none gap-1 p-0 text-sm sm:grid-cols-3">
        {(["signal", "asha", "official"] as const).map((k) => {
          const m = marks.find((x) => x.key === k);
          return (
            <li key={k} className="flex items-start gap-2">
              <span aria-hidden="true" className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: MARK_STYLE[k].fill, opacity: m ? 1 : 0.35 }} />
              <span className={m ? "" : "text-muted"}>
                <span className="font-semibold">{k === "signal" ? "Pharmacy signal" : k === "asha" ? "ASHA rise" : "Official report"}</span>
                <br />
                {m ? `${fmtShortDate(m.date)}${k === "official" && projected ? " (projected)" : ""}` : k === "asha" ? "not visible yet" : "none yet"}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="m-0 mt-2 text-sm">
        <strong>{leadSentence(ev.lead_days_vs_official, "official report", projected)}.</strong>{" "}
        <span className="text-muted">{leadSentence(ev.lead_days_vs_asha, "ASHA rise")}.</span>
      </p>
    </li>
  );
}

function NoteList({ data, heading }: { data: Pick<Backtest, "false_alarms" | "missed">; heading?: string }) {
  const fa = groupNotes(data.false_alarms);
  const ms = groupNotes(data.missed);
  if (fa.length === 0 && ms.length === 0) return null;
  return (
    <div className="space-y-2">
      {heading && <h3 className="label-xs">{heading}</h3>}
      <ul className="m-0 list-none space-y-2 p-0 text-sm">
        {fa.map((n, i) => (
          <li key={`fa-${i}`} className="panel-warn">
            <strong>False alarm in the scenario.</strong> {n.text}
            {n.pins.length > 0 && <> Fired in pin codes {n.pins.join(", ")}.</>}
          </li>
        ))}
        {ms.map((n, i) => (
          <li key={`ms-${i}`} className="panel-warn">
            <strong>Missed event in the scenario.</strong> {n.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BacktestView({ data, areaOf, elsewhere }: { data: Backtest; areaOf: (pin: string) => string; elsewhere?: Pick<Backtest, "false_alarms" | "missed"> }) {
  const leads = data.events.map((e) => e.lead_days_vs_official).filter((x): x is number => typeof x === "number");
  const own = data.false_alarms.length + data.missed.length > 0;
  return (
    <div className="space-y-3">
      <p className="m-0 text-sm text-muted">{data.note}</p>
      {data.events.length === 0 ? (
        <p className="m-0 text-sm">No back-test events for this alert in the simulated scenario.</p>
      ) : (
        <ul className="m-0 list-none space-y-3 p-0">
          {data.events.map((e) => (
            <EventTimeline key={`${e.event}-${e.pin}`} ev={e} area={e.area || areaOf(String(e.pin))} />
          ))}
        </ul>
      )}
      {leads.length > 0 && (
        <p className="m-0 text-xs text-muted">
          Leads vary by pin on purpose. In the simulated scenario the signal came {Math.min(...leads) === Math.max(...leads) ? Math.min(...leads) : `${Math.min(...leads)} to ${Math.max(...leads)}`} days before the official report.
        </p>
      )}
      <NoteList data={data} />
      {!own && elsewhere && <NoteList data={elsewhere} heading="Where the same rule was wrong (whole scenario)" />}
      <details className="text-sm">
        <summary className="min-h-9 cursor-pointer font-semibold">The rule that was tested</summary>
        <p className="m-0 mt-1 text-muted">{data.rule}</p>
      </details>
    </div>
  );
}

/** Back-test panel for one alert: a replay of a SIMULATED scenario, never presented as evidence. */
export function BacktestPanel({ alertId }: { alertId: string }) {
  const { areaOf } = useRefData();
  const q = useAsync((s) => api.backtest(alertId, s), [alertId]);
  const all = useAsync((s) => api.backtest(undefined, s), []);
  return (
    <section aria-labelledby="bt-h" className="card space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="bt-h" className="text-h3">Back-test (simulated scenario)</h2>
        <SimulatedBadge />
      </div>
      {q.loading && !q.data ? (
        <Skeleton className="h-32 w-full" />
      ) : q.error ? (
        q.error.status === 404 ? (
          <p className="m-0 text-sm text-muted">No back-test is available for this alert.</p>
        ) : (
          <ErrorPanel error={q.error} message="We could not load the back-test." onRetry={q.reload} />
        )
      ) : q.data ? (
        <BacktestView data={q.data} areaOf={areaOf} elsewhere={all.data ?? undefined} />
      ) : null}
    </section>
  );
}

/** Weather and air for the alert's pins. Real data from Open-Meteo (nearest grid point). */
export function EnvironmentPanel({ pins }: { pins: string[] }) {
  const { areaOf } = useRefData();
  const [pin, setPin] = useState(pins[0] ?? "");
  const active = pins.includes(pin) ? pin : (pins[0] ?? "");
  const q = useAsync((s) => api.environment(active, 30, s), [active]);
  const e = q.data ? envSeries(q.data) : null;
  const area = areaOf(active);
  return (
    <section aria-labelledby="env-h" className="card space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="env-h" className="text-h3">Weather and air, last 30 days</h2>
        <RealBadge />
      </div>
      {pins.length > 1 && (
        <label className="flex items-center gap-2 text-sm font-medium">
          Pin code
          <select className="input w-auto" value={active} onChange={(ev) => setPin(ev.target.value)}>
            {pins.map((p) => (
              <option key={p} value={p}>
                {areaOf(p)} ({p})
              </option>
            ))}
          </select>
        </label>
      )}
      {q.loading && !q.data ? (
        <Skeleton className="h-32 w-full" />
      ) : q.error || !e || e.dates.length === 0 ? (
        <p className="m-0 text-sm text-muted">No weather data for this pin code yet.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div>
            <h3 className="label-xs mb-1">Temperature (C)</h3>
            <MiniChart dates={e.dates} series={e.temp} label={`Daily maximum and minimum temperature in ${area}, last 30 days.`} />
          </div>
          <div>
            <h3 className="label-xs mb-1">Rain (mm per day)</h3>
            <MiniChart dates={e.dates} series={e.rain} kind="bar" label={`Daily rain in ${area}, last 30 days.`} />
          </div>
          <div>
            <h3 className="label-xs mb-1">Air: PM2.5 and PM10</h3>
            <MiniChart dates={e.dates} series={e.air} label={`Daily PM2.5 and PM10 in ${area}, last 30 days.`} />
          </div>
        </div>
      )}
      <p className="m-0 text-xs text-muted">Source: Open-Meteo weather and air-quality models, nearest grid point to the pin code. Real readings; they show context, not cause.</p>
    </section>
  );
}

/** What ASHAs in these pins reported, day by day. Simulated history plus any live reports. */
export function AshaHistoryPanel({ pins }: { pins: string[] }) {
  const { areaOf } = useRefData();
  const [pin, setPin] = useState(pins[0] ?? "");
  const active = pins.includes(pin) ? pin : (pins[0] ?? "");
  const q = useAsync((s) => api.ashaHistory(active, 30, s), [active]);
  const rows = q.data ?? [];
  const s = ashaSeries(rows);
  const total = sumDays(rows);
  return (
    <section aria-labelledby="ah-h" className="card space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="ah-h" className="text-h3">ASHA reports, last 30 days</h2>
        <SimulatedBadge />
      </div>
      {pins.length > 1 && (
        <label className="flex items-center gap-2 text-sm font-medium">
          Pin code
          <select className="input w-auto" value={active} onChange={(ev) => setPin(ev.target.value)}>
            {pins.map((p) => (
              <option key={p} value={p}>
                {areaOf(p)} ({p})
              </option>
            ))}
          </select>
        </label>
      )}
      {q.loading && !q.data ? (
        <Skeleton className="h-24 w-full" />
      ) : q.error || rows.length === 0 || total.reports === 0 ? (
        <p className="m-0 text-sm text-muted">No ASHA reports for this pin code yet.</p>
      ) : (
        <>
          <MiniChart dates={s.dates} series={s.series} label={`Households with fever, diarrhoea and cough reported by ASHAs in ${areaOf(active)}, last 30 days.`} />
          <p className="m-0 text-sm text-muted">
            <span className="mono">{total.reports}</span> reports, <span className="mono">{total.households}</span> households visited, <span className="mono">{total.referred}</span> referred.
          </p>
        </>
      )}
    </section>
  );
}

/** Table of the last N days for the ASHA's own pin (Hindi first). */
export function AshaRecentTable({ rows, headers }: { rows: AshaDay[]; headers: { day: string; homes: string; fever: string; diarrhoea: string; cough: string } }) {
  return (
    <table className="w-full text-left text-base">
      <thead>
        <tr className="text-sm text-muted">
          <th scope="col" className="py-1 pr-2 font-medium" lang="hi">{headers.day}</th>
          <th scope="col" className="px-1 py-1 text-right font-medium" lang="hi">{headers.homes}</th>
          <th scope="col" className="px-1 py-1 text-right font-medium" lang="hi">{headers.fever}</th>
          <th scope="col" className="px-1 py-1 text-right font-medium" lang="hi">{headers.diarrhoea}</th>
          <th scope="col" className="py-1 pl-1 text-right font-medium" lang="hi">{headers.cough}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.date} className="border-t border-border">
            <th scope="row" className="py-2 pr-2 font-normal">{fmtShortDate(r.date)}</th>
            <td className="mono px-1 py-2 text-right">{r.households_visited}</td>
            <td className="mono px-1 py-2 text-right">{r.fever}</td>
            <td className="mono px-1 py-2 text-right">{r.diarrhoea}</td>
            <td className="mono py-2 pl-1 text-right">{r.cough}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
