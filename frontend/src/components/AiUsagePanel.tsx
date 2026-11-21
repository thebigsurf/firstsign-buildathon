import { Gauge } from "lucide-react";
import { api } from "../api";
import { cachedShare, hasLiveCalls, inr, jobLabel, pct, seconds } from "../lib/aiUsage";
import { useAsync } from "../lib/hooks";
import { ErrorPanel, Skeleton } from "./ui/States";

/** Live view of the usage ledger: what the AI costs and how it behaves, in plain English. */
export function AiUsagePanel() {
  const usage = useAsync((s) => api.aiUsage(s), []);
  const u = usage.data;

  return (
    <section aria-labelledby="usage-h" className="space-y-3">
      <h2 id="usage-h" className="flex items-center gap-2 text-h2">
        <Gauge size={20} strokeWidth={1.75} aria-hidden="true" /> AI usage and cost
      </h2>
      <p className="text-muted">
        Every Gemini call is logged with its tokens, time and cost. This is the live ledger of this server since it started. Rupee amounts use a
        stated exchange rate and Google&rsquo;s list prices; they are estimates, not an invoice.
      </p>
      {usage.loading && !u ? (
        <Skeleton className="h-40 w-full" />
      ) : usage.error ? (
        <ErrorPanel error={usage.error} message="We could not read the AI usage ledger." onRetry={usage.reload} />
      ) : u && !hasLiveCalls(u) && u.totals.labelled_fallbacks === 0 && u.totals.disk_cache_hits === 0 ? (
        <p className="panel-info text-sm" data-testid="usage-empty">
          {u.limits.offline
            ? "This server is in demo mode, so no live Gemini calls have been made."
            : "No Gemini calls yet. Parse an order or explain an alert and the numbers appear here."}
        </p>
      ) : u ? (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="AI usage summary">
            {[
              ["Live Gemini calls", String(u.totals.calls)],
              ["Cost per order read", inr(u.cost_per_order_inr)],
              ["Prompt served from cache", pct(u.cache.implicit_cached_token_share)],
              ["Answered from saved copy", pct(u.cache.disk_hit_rate)],
              ["Fallback rate", pct(u.fallback_rate)],
              ["Typical wait (median)", seconds(u.latency_ms.p50)],
              ["Slow wait (95th pct)", seconds(u.latency_ms.p95)],
              ["Spent today", `${inr(u.budget.spent_today_inr)} of ${inr(u.budget.daily_inr)}`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border bg-surface p-3">
                <dt className="text-sm text-muted">{label}</dt>
                <dd className="mono text-xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>

          {u.budget.exceeded && (
            <p className="panel-warn text-sm" role="status">
              The daily AI budget is used up. New requests are answered from saved, labelled results until tomorrow.
            </p>
          )}

          <div className="overflow-x-auto rounded-lg border border-border bg-surface">
            <table className="w-full text-left">
              <caption className="sr-only">Average tokens, time and cost per kind of Gemini job</caption>
              <thead>
                <tr className="bg-sunken text-xs uppercase tracking-wide text-muted">
                  <th scope="col" className="px-3 py-2">Job</th>
                  <th scope="col" className="px-3 py-2 text-right">Calls</th>
                  <th scope="col" className="px-3 py-2 text-right">Tokens in</th>
                  <th scope="col" className="px-3 py-2 text-right">Cached</th>
                  <th scope="col" className="px-3 py-2 text-right">Tokens out</th>
                  <th scope="col" className="px-3 py-2 text-right">Thinking</th>
                  <th scope="col" className="px-3 py-2 text-right">Time</th>
                  <th scope="col" className="px-3 py-2 text-right">Cost each</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(u.by_job).map(([job, b]) => (
                  <tr key={job} className="border-t border-border">
                    <th scope="row" className="px-3 py-2 text-left text-sm font-medium">{jobLabel(job)}</th>
                    <td className="mono px-3 py-2 text-right text-sm">{b.calls}</td>
                    <td className="mono px-3 py-2 text-right text-sm">{b.avg_prompt_tokens.toLocaleString("en-IN")}</td>
                    <td className="mono px-3 py-2 text-right text-sm">{pct(cachedShare(b))}</td>
                    <td className="mono px-3 py-2 text-right text-sm">{b.avg_output_tokens.toLocaleString("en-IN")}</td>
                    <td className="mono px-3 py-2 text-right text-sm">{b.avg_thought_tokens.toLocaleString("en-IN")}</td>
                    <td className="mono px-3 py-2 text-right text-sm whitespace-nowrap">{seconds(b.avg_latency_ms)}</td>
                    <td className="mono px-3 py-2 text-right text-sm">{inr(b.avg_cost_inr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="m-0 flex list-none flex-wrap gap-2 p-0 text-sm text-muted" aria-label="Calls per model">
            {Object.entries(u.by_model).map(([model, b]) => (
              <li key={model} className="rounded-md border border-border bg-surface px-2 py-1">
                <span className="mono">{model}</span>: {b.calls} calls, {inr(b.cost_inr)}
              </li>
            ))}
          </ul>

          <p className="text-sm text-muted">
            Protection: {u.limits.gemini_max_concurrency} Gemini calls at once, {u.limits.rate_limit_per_min_per_ip} requests per minute per device,
            uploads up to {u.limits.max_upload_mb} MB, a daily spend cap, and a labelled saved result whenever a model is busy or the cap is reached.
            Rates assume 1 USD = {"₹"}{u.assumptions.usd_inr}.
          </p>
        </>
      ) : null}
    </section>
  );
}
