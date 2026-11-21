import { api } from "../api";
import { channelShares } from "../lib/extended";
import { useAsync } from "../lib/hooks";
import { Badge } from "./ui/Badge";
import { FlaskConical } from "lucide-react";

const nf = new Intl.NumberFormat("en-IN");

interface Tile {
  label: string;
  value: string;
  hint?: string;
}

export function overviewTiles(o: {
  orders_30d: number;
  lines_30d: number;
  chemists_active: number;
  stockouts_14d: number;
  avg_clerk_minutes_saved_per_order: number;
  alerts_open: number;
  alerts_confirmed: number;
}): Tile[] {
  const tiles: Tile[] = [
    { label: "Orders, last 30 days", value: nf.format(o.orders_30d), hint: `${nf.format(o.lines_30d)} order lines` },
    { label: "Chemists ordering", value: nf.format(o.chemists_active) },
    { label: "Stock-outs logged, 14 days", value: nf.format(o.stockouts_14d), hint: "asked for, not available" },
    {
      label: "Clerk minutes saved per order",
      value: `~${Math.round(o.avg_clerk_minutes_saved_per_order * 10) / 10}`,
      hint: "estimate, not measured",
    },
    { label: "Alerts open", value: String(o.alerts_open) },
    { label: "Alerts confirmed", value: String(o.alerts_confirmed) },
  ];
  // A tile that is zero says nothing useful on a first look, so it is left out.
  return tiles.filter((t) => !/^~?0(\.0)?$/.test(t.value));
}

/** Landing-page numbers from /api/overview (history is simulated and says so). Hides itself if the call fails. */
export function OverviewTiles({ className = "" }: { className?: string }) {
  const { data } = useAsync((s) => api.overview(s), []);
  if (!data) return null;
  const tiles = overviewTiles(data).slice(0, 4);
  const shares = channelShares(data.share_by_channel ?? {}).slice(0, 4);
  if (tiles.length === 0) return null;
  return (
    <section aria-labelledby="ov-h" className={`space-y-3 ${className}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h2 id="ov-h" className="text-h3">The last 30 days at one distributor</h2>
        <Badge className="bg-watchBg text-watch" icon={FlaskConical}>Simulated history</Badge>
      </div>
      <dl className="m-0 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-lg border border-border bg-surface p-3">
            <dt className="text-sm text-muted">{t.label}</dt>
            <dd className="mono m-0 text-2xl font-semibold">{t.value}</dd>
            {t.hint && <dd className="m-0 text-xs text-muted">{t.hint}</dd>}
          </div>
        ))}
      </dl>
      {data.avg_clerk_minutes_saved_basis && <p className="m-0 text-xs text-muted">{data.avg_clerk_minutes_saved_basis}</p>}
      {shares.length > 0 && (
        <p className="m-0 text-sm text-muted">
          How orders arrive:{" "}
          {shares.map((c, i) => (
            <span key={c.key}>
              {i > 0 && ", "}
              <span className="font-medium text-text">{c.label}</span> <span className="mono">{c.pct}%</span>
            </span>
          ))}
          .
        </p>
      )}
    </section>
  );
}
