import { api } from "../api";
import { useAsync } from "../lib/hooks";

/** Live numbers from /api/metrics. If the call fails the strip quietly hides itself. */
export function MetricsStrip({ className = "" }: { className?: string }) {
  const { data } = useAsync((s) => api.metrics(s), []);
  if (!data) return null;
  // Only show tiles that have something to say; a row of zeros on a fresh start reads as "nothing works".
  const items: Array<[string, number, string]> = [
    ["Orders read", data.orders_parsed, String(data.orders_parsed)],
    ["Matched on first read", Math.round(data.auto_matched_pct), `${Math.round(data.auto_matched_pct)}%`],
    ["Alerts raised from live orders", data.alerts_raised ?? 0, String(data.alerts_raised ?? 0)],
    ["Single-shop spikes ignored", data.decoys_suppressed ?? 0, String(data.decoys_suppressed ?? 0)],
    ["ASHA reports", data.asha_reports, String(data.asha_reports)],
    ["Alerts confirmed", data.alerts_confirmed, String(data.alerts_confirmed)],
  ].filter(([, n]) => (n as number) > 0).slice(0, 4) as Array<[string, number, string]>;
  if (items.length === 0) return null;
  return (
    <dl aria-label="Live numbers" className={`grid grid-cols-2 gap-4 sm:grid-cols-4 ${className}`}>
      {items.map(([label, , value]) => (
        <div key={label} className="rounded-lg border border-border bg-surface p-3">
          <dt className="text-sm text-muted">{label}</dt>
          <dd className="mono text-2xl font-semibold">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
