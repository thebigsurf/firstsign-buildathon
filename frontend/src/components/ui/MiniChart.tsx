import { fmtShortDate } from "../../lib/format";
import type { Series } from "../../lib/extended";

interface MiniChartProps {
  dates: string[];
  series: Series[];
  /** Full sentence for screen readers. */
  label: string;
  kind?: "line" | "bar";
  height?: number;
  unit?: string;
}

const W = 200;
const H = 60;
const PAD = 5;

function fmt(n: number): string {
  return Math.abs(n) >= 100 ? String(Math.round(n)) : String(Math.round(n * 10) / 10);
}

/** Small inline-SVG chart (lines or bars) with a legend and a hidden data table. No chart library. */
export function MiniChart({ dates, series, label, kind = "line", height = 72, unit = "" }: MiniChartProps) {
  const all = series.flatMap((s) => s.values).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  if (dates.length < 2 || all.length === 0) {
    return <p className="m-0 text-sm text-muted">No data for this period.</p>;
  }
  const lo = kind === "bar" ? 0 : Math.min(...all);
  const hi = Math.max(...all, lo + 1e-6);
  const x = (i: number): number => (i / (dates.length - 1)) * W;
  const y = (v: number): number => H - PAD - ((v - lo) / (hi - lo)) * (H - PAD * 2);
  const recent = dates.map((d, i) => ({ d, i })).slice(-7);

  return (
    <figure className="m-0">
      <div className="flex items-stretch gap-1.5">
        <div className="mono flex flex-col justify-between py-0.5 text-[11px] leading-none text-muted" aria-hidden="true">
          <span>{fmt(hi)}{unit}</span>
          <span>{fmt(lo)}{unit}</span>
        </div>
        <svg role="img" aria-label={label} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full overflow-visible" style={{ height }}>
          <title>{label}</title>
          <line x1="0" x2={W} y1={H - PAD} y2={H - PAD} stroke="var(--border-strong)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          {kind === "bar"
            ? series[0].values.map((v, i) =>
                typeof v === "number" ? (
                  <rect key={dates[i]} x={x(i) - 1.4} width="2.8" y={y(v)} height={Math.max(0.5, H - PAD - y(v))} fill={series[0].color} />
                ) : null,
              )
            : series.map((s) => {
                const d = s.values
                  .map((v, i) => (typeof v === "number" ? `${i === 0 || typeof s.values[i - 1] !== "number" ? "M" : "L"}${x(i).toFixed(1)} ${y(v).toFixed(1)}` : ""))
                  .join(" ");
                return <path key={s.name} d={d} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />;
              })}
        </svg>
      </div>
      <figcaption className="mt-1 flex flex-wrap items-center justify-between gap-x-4 gap-y-0.5 text-xs text-muted">
        <span aria-hidden="true">{fmtShortDate(dates[0])} to {fmtShortDate(dates[dates.length - 1])}</span>
        <span className="flex flex-wrap gap-x-3" aria-hidden="true">
          {series.map((s) => (
            <span key={s.name} className="inline-flex items-center gap-1">
              <svg width="18" height="6" aria-hidden="true">
                <line x1="0" x2="18" y1="3" y2="3" stroke={s.color} strokeWidth="2.5" strokeDasharray={s.dash} />
              </svg>
              {s.name}
            </span>
          ))}
        </span>
      </figcaption>
      <div className="sr-only">
        <table>
          <caption>{label}</caption>
          <thead>
            <tr>
              <th scope="col">Date</th>
              {series.map((s) => (
                <th key={s.name} scope="col">{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map(({ d, i }) => (
              <tr key={d}>
                <th scope="row">{fmtShortDate(d)}</th>
                {series.map((s) => (
                  <td key={s.name}>{s.values[i] ?? "n/a"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
