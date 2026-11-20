import { useId } from "react";
import { fmtShortDate } from "../../lib/format";
import type { Level, SeriesPoint } from "../../types";

const LEVEL_COLOR: Record<Level, string> = {
  normal: "var(--normal)",
  watch: "var(--watch)",
  alert: "var(--alert)",
};

interface SparklineProps {
  series: SeriesPoint[];
  level: Level;
  /** Full sentence for screen readers, e.g. "Fever orders in Kurla over the last 30 days: today 38 units, normal 15." */
  label: string;
  height?: number;
  showLegend?: boolean;
}

const W = 200;

/** Inline-SVG sparkline: orders as a line, baseline dashed, labelled end value. No chart library. */
export function Sparkline({ series, level, label, height = 56, showLegend = true }: SparklineProps) {
  const uid = useId();
  const color = LEVEL_COLOR[level];
  if (series.length < 2) {
    return <p className="text-sm text-muted">Not enough history to draw a chart yet.</p>;
  }

  const max = Math.max(...series.map((p) => Math.max(p.units, p.baseline)), 1);
  const padY = 8;
  const H = 56;
  const x = (i: number): number => (i / (series.length - 1)) * W;
  const y = (v: number): number => H - padY - (v / max) * (H - padY * 2);

  const line = series.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(p.units).toFixed(1)}`).join(" ");
  const base = series.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(p.baseline).toFixed(1)}`).join(" ");
  const area =
    line +
    " " +
    series
      .map((_, i) => series.length - 1 - i)
      .map((i) => `L${x(i).toFixed(1)} ${y(series[i].baseline).toFixed(1)}`)
      .join(" ") +
    " Z";

  const last = series[series.length - 1];
  const dotLeft = 100;
  const dotTop = (y(last.units) / H) * 100;
  const recent = series.slice(-14);

  return (
    <figure className="m-0">
      <div className="relative w-full" style={{ height }}>
        <svg
          role="img"
          aria-label={label}
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="h-full w-full overflow-visible"
        >
          <title id={uid}>{label}</title>
          <path d={area} fill={color} fillOpacity="0.12" />
          <path d={base} fill="none" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
          <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </svg>
        <span
          aria-hidden="true"
          className="absolute h-[7px] w-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ left: `${dotLeft}%`, top: `${dotTop}%`, background: color }}
        />
        <span
          aria-hidden="true"
          className="mono absolute -translate-y-full rounded bg-surface px-1 text-xs"
          style={{ right: 0, top: `calc(${dotTop}% - 6px)`, color }}
        >
          {Math.round(last.units)}
        </span>
      </div>
      {showLegend && (
        <figcaption className="mt-1 flex gap-4 text-xs text-muted" aria-hidden="true">
          <span>- - normal range</span>
          <span>-- orders</span>
        </figcaption>
      )}
      <div className="sr-only">
      <table>
        <caption>{label}</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Units</th>
            <th scope="col">Normal</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((p) => (
            <tr key={p.date}>
              <th scope="row">{fmtShortDate(p.date)}</th>
              <td>{Math.round(p.units)}</td>
              <td>{Math.round(p.baseline)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </figure>
  );
}
