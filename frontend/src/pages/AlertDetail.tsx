import { ArrowLeft, Check, CircleX, Cpu, ExternalLink, RefreshCw, SearchX } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../lib/AuthContext";
import { OFFICERS, TextActionCard, VisitListCard, type ApprovedState } from "../components/officer/ActionCards";
import { alertTitle } from "../components/officer/AlertCard";
import { AshaHistoryPanel, BacktestPanel, EnvironmentPanel } from "../components/officer/ExtendedPanels";
import { AlertStatusChip, Badge, LevelBadge, PinChip } from "../components/ui/Badge";
import { Button, ButtonLink } from "../components/ui/Button";
import { ConfidenceMeter } from "../components/ui/ConfidenceMeter";
import { EmptyState, ErrorPanel, Skeleton } from "../components/ui/States";
import { Sparkline } from "../components/ui/Sparkline";
import { useToast } from "../components/ui/Toast";
import { daysSince, domainOf, fmtDateTime, fmtShortDate, isSafeHttpUrl, plural } from "../lib/format";
import { toApiError, useAsync, useDocumentTitle, usePolling } from "../lib/hooks";
import { useRefData } from "../lib/refdata";
import type { ActionName, Alert, Cell, Explanation, VisitItem } from "../types";

const STAGES = ["Checking order data", "Searching for outbreak reports", "Writing the explanation"];

function ExplainProgress() {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setSecs((s) => s + 0.5), 500);
    return () => window.clearInterval(id);
  }, []);
  const current = secs < 3 ? 0 : secs < 9 ? 1 : 2;
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <ol className="m-0 flex list-none flex-wrap gap-x-5 gap-y-2 p-0 text-sm">
        {STAGES.map((s, i) => (
          <li key={s} className={i === current ? "font-semibold" : "text-muted"}>
            <span className="mono mr-1.5">{i + 1}.</span>
            {s}
            {i === current && <span className="sr-only"> (now)</span>}
          </li>
        ))}
        <li className="mono ml-auto text-muted">{secs.toFixed(0)} s</li>
      </ol>
      <div aria-hidden="true" className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

function zWord(z: number): string {
  if (z >= 4) return "far above usual";
  if (z >= 2.5) return "well above usual";
  return "above usual";
}

interface DataCheck {
  ok: boolean;
  text: string;
}

function dataChecks(alert: Alert, cells: Cell[]): DataCheck[] {
  const out: DataCheck[] = [
    { ok: alert.breadth >= 0.25, text: `Many shops: about ${Math.round(alert.breadth * 100)}% of chemists in these pin codes are ordering above normal` },
    { ok: alert.pins.length >= 2, text: alert.pins.length >= 2 ? "Several neighbouring pins moving together" : "Only one pin code is moving, so it may be local" },
  ];
  if (alert.group !== "respiratory") {
    const resp = cells.filter((c) => c.group === "respiratory" && alert.pins.includes(c.pin));
    if (resp.length > 0) {
      const flat = resp.every((c) => c.ratio < 1.3);
      out.push({ ok: flat, text: flat ? "Respiratory orders flat, so not a general bad-air week" : "Respiratory orders are also up, so air quality could be part of this" });
    }
  }
  return out;
}

export function AlertDetail() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const fromDistributor = params.get("from") === "distributor";
  const toast = useToast();
  const { groupLabel, areaOf } = useRefData();

  const alertQ = useAsync((s) => api.alert(id, s), [id]);
  const signalQ = useAsync((s) => api.signal(30, s), []);
  const auditQ = useAsync((s) => api.audit(s), [id]);
  const explainQ = useAsync((s) => api.explain(id, false, s), [id]);
  usePolling(alertQ.reload, 20000);

  const alert = alertQ.data;
  const [regenerating, setRegenerating] = useState(false);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [regenError, setRegenError] = useState<string | null>(null);
  const { user } = useAuth();
  const [approver, setApprover] = useState(user && user.roleId !== "founder" ? user.approverLabel : OFFICERS[0]);
  const [busy, setBusy] = useState<ActionName | null>(null);
  const [localApprovals, setLocalApprovals] = useState<Partial<Record<ActionName, ApprovedState>>>({});
  const [showAllPins, setShowAllPins] = useState(false);
  const [announce, setAnnounce] = useState("");
  const seenReports = useRef<Set<string> | null>(null);

  useDocumentTitle(alert ? alertTitle(alert, groupLabel, areaOf) : "Alert");

  const shownExplanation = explanation ?? explainQ.data;

  // Approvals that already happened (before this page was opened) come from the audit log.
  const approvals = useMemo(() => {
    const map: Partial<Record<ActionName, ApprovedState>> = {};
    const rows = [...(auditQ.data ?? [])].sort((a, b) => (a.ts ?? a.at ?? "").localeCompare(b.ts ?? b.at ?? ""));
    for (const e of rows) {
      const ref = e.ref_id ?? e.ref;
      const action = (e.detail?.action ?? "") as string;
      if (e.kind === "action_approved" && ref === id && ["distributor_note", "officer_note", "asha_visit_list"].includes(action)) {
        map[action as ActionName] = {
          by: e.approved_by || e.actor,
          at: e.ts ?? e.at ?? "",
          text: String(e.detail?.approved_text ?? ""),
        };
      }
    }
    return { ...map, ...localApprovals };
  }, [auditQ.data, localApprovals, id]);

  // New ASHA reports slide in and are announced once.
  const newReportIds = useMemo(() => {
    const ids = new Set((alert?.reports ?? []).map((r) => r.report_id));
    if (seenReports.current === null) return new Set<string>();
    return new Set([...ids].filter((x) => !seenReports.current?.has(x)));
  }, [alert?.reports]);
  useEffect(() => {
    const ids = (alert?.reports ?? []).map((r) => r.report_id);
    if (seenReports.current !== null && ids.some((x) => !seenReports.current?.has(x)) && alert) {
      setAnnounce(`New ASHA report: alert confidence now ${Math.round(alert.confidence * 100)}%`);
    }
    seenReports.current = new Set(ids);
  }, [alert?.reports, alert]);

  const regenerate = async (): Promise<void> => {
    setRegenerating(true);
    setRegenError(null);
    try {
      setExplanation(await api.explain(id, true));
    } catch (err) {
      setRegenError(toApiError(err).message);
    } finally {
      setRegenerating(false);
    }
  };

  const approve = async (action: ActionName, editedText: string | undefined, visits?: VisitItem[]): Promise<void> => {
    setBusy(action);
    try {
      const res = await api.approveAction({ alert_id: id, action, approved_by: approver, edited_text: editedText, visit_list: visits });
      setLocalApprovals((cur) => ({ ...cur, [action]: { by: res.approved_by, at: res.created_at, text: res.text } }));
      auditQ.reload();
      toast.show("success", `Approved by ${res.approved_by}. Logged in the audit log.`);
    } catch (err) {
      toast.show("error", `Could not approve. ${toApiError(err).message}`);
    } finally {
      setBusy(null);
    }
  };

  if (alertQ.error && !alert) {
    const notFound = alertQ.error.status === 404;
    return (
      <div className="mx-auto max-w-xl px-4 py-12">
        <h1 className="sr-only">Alert</h1>
        {notFound ? (
          <EmptyState icon={SearchX} title="We could not find this alert" body="It may have been cleared." action={<ButtonLink to="/officer">Back to all alerts</ButtonLink>} />
        ) : (
          <ErrorPanel error={alertQ.error} message="We could not load this alert." onRetry={alertQ.reload} />
        )}
      </div>
    );
  }

  if (!alert) {
    return (
      <div aria-busy="true" className="mx-auto max-w-[1440px] space-y-4 px-4 py-6 md:px-6 xl:px-8">
        <h1 className="sr-only">Alert</h1>
        <Skeleton className="h-10 w-96 max-w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const cells = (signalQ.data?.cells ?? []).filter((c) => c.group === alert.group && alert.pins.includes(c.pin));
  const visiblePins = showAllPins ? cells : cells.slice(0, 3);
  const dismissed = alert.status === "dismissed";
  const readOnly = fromDistributor || dismissed;
  const days = daysSince(alert.started, signalQ.data?.as_of);
  const auditHref = `/officer/alert/${encodeURIComponent(id)}?view=audit`;
  const checks = dataChecks(alert, signalQ.data?.cells ?? []);
  const approvedTimes = Object.values(approvals).map((a) => a.at).filter(Boolean).sort();
  const reports = [...(alert.reports ?? [])].sort((a, b) => a.created_at.localeCompare(b.created_at));

  const timeline: Array<[string, string, boolean]> = [
    ["First sign in orders", `${fmtShortDate(alert.started)}`, true],
    ["Actions approved", approvedTimes[0] ? fmtShortDate(approvedTimes[0]) : "Not yet", Boolean(approvedTimes[0])],
    ["First ASHA report", reports[0] ? fmtShortDate(reports[0].created_at) : "Waiting", Boolean(reports[0])],
    ["Confirmed on the ground", alert.status === "confirmed" ? "Confirmed" : alert.status === "dismissed" ? "Dismissed" : "Open", alert.status !== "open"],
  ];

  return (
    <div className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 md:px-6 xl:px-8">
      <Link to={fromDistributor ? "/distributor/radar" : "/officer"} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accentText">
        <ArrowLeft size={16} aria-hidden="true" /> {fromDistributor ? "Back to stock radar" : "All alerts"}
      </Link>

      {fromDistributor && <p className="panel-warn m-0 text-sm">You are reading this as a distributor. It is read-only: only the health officer approves actions.</p>}
      {dismissed && <p className="panel-warn m-0 text-sm">This alert was dismissed after ASHA reports showed little illness. It is read-only.</p>}

      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <LevelBadge level={alert.level} />
          <AlertStatusChip status={alert.status} />
          {alert.pins.map((p) => (
            <PinChip key={p} pin={p} />
          ))}
        </div>
        <h1 className="text-h1">
          {alert.group_label || groupLabel(alert.group)} rising in {alert.pins.map(areaOf).join(", ")}
        </h1>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <ConfidenceMeter value={alert.confidence} label="Alert confidence" width="w-40" />
          <span className="text-sm text-muted">
            Rising since {fmtShortDate(alert.started)} ({plural(days, "day")})
          </span>
        </div>
        <dl className="m-0 grid max-w-2xl grid-cols-3 gap-3">
          <div className="rounded-lg border border-border bg-surface p-3">
            <dt className="text-sm text-muted">Orders vs normal</dt>
            <dd className="mono m-0 text-num-lg">{alert.ratio.toFixed(1)}x</dd>
          </div>
          <div className="rounded-lg border border-border bg-surface p-3">
            <dt className="text-sm text-muted">Shops moving</dt>
            <dd className="mono m-0 text-num-lg">{Math.round(alert.breadth * 100)}%</dd>
          </div>
          <div className="rounded-lg border border-border bg-surface p-3" title={`z-score ${(alert.z ?? 0).toFixed(1)}`}>
            <dt className="text-sm text-muted">Size of rise</dt>
            <dd className="m-0 pt-1 font-display text-h3">{zWord(alert.z ?? 0)}</dd>
            <dd className="mono m-0 text-xs text-muted">z = {(alert.z ?? 0).toFixed(1)}</dd>
          </div>
        </dl>
      </header>

      <ol aria-label="Timeline of this alert" className="m-0 grid list-none grid-cols-2 gap-3 p-0 md:grid-cols-4">
        {timeline.map(([label, when, done], i) => (
          <li key={label} className="rounded-lg border border-border bg-surface p-3 text-sm">
            <span className="flex items-center gap-2 font-semibold">
              <span className={`mono flex h-6 w-6 items-center justify-center rounded-full text-xs ${done ? "bg-normal text-surface" : "bg-sunken text-muted"}`} aria-hidden="true">
                {done ? <Check size={14} /> : i + 1}
              </span>
              {label}
            </span>
            <span className="mt-1 block text-muted">{when}</span>
          </li>
        ))}
      </ol>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-7">
          <section aria-labelledby="chart-h" className="card space-y-3">
            <h2 id="chart-h" className="text-h3">Orders vs normal, last 30 days</h2>
            {signalQ.loading && !signalQ.data ? (
              <Skeleton className="h-48 w-full" />
            ) : signalQ.error ? (
              <ErrorPanel error={signalQ.error} message="We could not load the order history." onRetry={signalQ.reload} />
            ) : cells.length === 0 ? (
              <p className="m-0 text-muted">No order history for these pin codes.</p>
            ) : (
              <>
                <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
                  {visiblePins.map((c) => (
                    <div key={c.pin}>
                      <p className="m-0 mb-1 flex items-center gap-2 text-sm font-semibold">
                        {areaOf(c.pin)} <PinChip pin={c.pin} />
                      </p>
                      <Sparkline
                        series={c.series}
                        level={c.level}
                        height={200}
                        label={`${groupLabel(c.group)} orders in ${areaOf(c.pin)} over the last 30 days: today ${Math.round(c.today)} units, normal ${Math.round(c.baseline)}.`}
                      />
                    </div>
                  ))}
                </div>
                {cells.length > 3 && (
                  <Button variant="ghost" size="sm" onClick={() => setShowAllPins((v) => !v)}>
                    {showAllPins ? "Show fewer" : `Show all ${cells.length}`}
                  </Button>
                )}
              </>
            )}
          </section>

          <section aria-labelledby="why-h" className="space-y-3">
            <h2 id="why-h" className="text-h2">Why we think this</h2>
            <div className="panel-info space-y-4" aria-busy={explainQ.loading || regenerating}>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-semibold">{shownExplanation?.grounded ? "Explained by Gemini with Google Search" : "Explained by Gemini from our order data"}</span>
                {shownExplanation?.model && (
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-0.5">
                    <Cpu size={14} aria-hidden="true" />
                    <span className="mono text-xs">{shownExplanation.model}</span>
                    <span className="mono text-xs text-muted">{(shownExplanation.latency_ms / 1000).toFixed(1)} s</span>
                  </span>
                )}
                {shownExplanation?.cached && !regenerating && <span className="rounded-md bg-surface px-2 py-0.5 text-xs">Saved from earlier</span>}
                {shownExplanation && (
                  <Button variant="secondary" size="sm" className="ml-auto" loading={regenerating} onClick={() => void regenerate()} icon={<RefreshCw size={14} aria-hidden="true" />}>
                    Regenerate
                  </Button>
                )}
              </div>

              {(explainQ.loading && !shownExplanation) || regenerating ? (
                <ExplainProgress />
              ) : explainQ.error && !shownExplanation ? (
                <ErrorPanel error={explainQ.error} message="We could not write the explanation." onRetry={explainQ.reload} />
              ) : shownExplanation ? (
                <div className="animate-slideIn space-y-5 motion-reduce:animate-none">
                  {regenError && <p role="alert" className="panel-error m-0 text-sm">{regenError}</p>}
                  <p className="m-0 max-w-[65ch] text-body">{shownExplanation.summary}</p>

                  <div>
                    <h3 className="text-h3">Likely causes</h3>
                    <ol className="m-0 mt-2 list-none space-y-3 p-0">
                      {shownExplanation.likely_causes.map((c, i) => (
                        <li key={`${c.cause}-${i}`} className="max-w-[65ch] space-y-1">
                          <p className="m-0 font-semibold">
                            {i + 1}. {c.cause}
                          </p>
                          <p className="m-0 text-sm">{c.evidence}</p>
                          <p className="m-0 text-xs font-semibold text-muted">
                            {shownExplanation.sources.length === 0
                              ? "Hypothesis, no outside source"
                              : "Hypothesis, not tied to a source (searched context below is not proof)"}
                          </p>
                          <div className="flex flex-wrap items-center gap-x-2">
                            <ConfidenceMeter value={c.confidence} label={`Rough estimate of confidence in: ${c.cause}`} width="w-24" />
                            <span className="text-xs text-muted">rough estimate</span>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div>
                    <h3 className="text-h3">What our data shows</h3>
                    <ul className="m-0 mt-2 list-none space-y-1 p-0 text-sm">
                      {checks.map((c) => (
                        <li key={c.text} className={`flex items-start gap-2 ${c.ok ? "" : "text-muted"}`}>
                          {c.ok ? <Check size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-normal" /> : <CircleX size={16} aria-hidden="true" className="mt-0.5 shrink-0" />}
                          <span>
                            <span className="sr-only">{c.ok ? "Yes: " : "No: "}</span>
                            {c.text}
                          </span>
                        </li>
                      ))}
                    </ul>
                    {alert.reasons.length > 0 && (
                      <details className="mt-2 text-sm">
                        <summary className="min-h-9 cursor-pointer font-semibold">How the confidence was worked out</summary>
                        <ul className="m-0 mt-1 list-disc pl-6">
                          {alert.reasons.map((r) => (
                            <li key={r}>{r}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>

                  <div>
                    <h3 className="text-h3">Searched context for this area (Google Search)</h3>
                    <p className="m-0 mt-1 text-sm text-muted">Web results the search returned for the area and dates (searched context). They are not proof of this alert; the demo order history is simulated.</p>
                    {shownExplanation.sources.length === 0 ? (
                      <p className="m-0 mt-1 text-sm">
                        No outside sources found. The explanation uses our order data only.
                        {shownExplanation.search_note ? ` ${shownExplanation.search_note}` : ""}
                      </p>
                    ) : (
                      <ul className="m-0 mt-2 list-none space-y-1.5 p-0">
                        {shownExplanation.sources
                          .filter((s) => isSafeHttpUrl(s.url))
                          .map((s) => (
                            <li key={s.url}>
                              <a href={s.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-2 font-medium text-accentText underline">
                                {s.title || domainOf(s.url)}
                                <ExternalLink size={14} aria-hidden="true" />
                                <span className="sr-only">(opens in a new tab)</span>
                              </a>{" "}
                              <span className="mono text-xs text-muted">{domainOf(s.url)}</span>
                            </li>
                          ))}
                      </ul>
                    )}
                    {shownExplanation.search_queries && shownExplanation.search_queries.length > 0 && (
                      <p className="m-0 mt-2 text-xs text-muted">Searches run: {shownExplanation.search_queries.join("; ")}</p>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </section>

          <BacktestPanel alertId={id} />
          <EnvironmentPanel pins={alert.pins} />
          <AshaHistoryPanel pins={alert.pins} />

          <section aria-labelledby="reports-h" className="space-y-3">
            <h2 id="reports-h" className="text-h2">ASHA reports</h2>
            <p className="sr-only" role="status" aria-live="polite">{announce}</p>
            {reports.length === 0 ? (
              <p className="m-0 rounded-lg border border-dashed border-borderStrong p-4 text-muted">No reports yet.</p>
            ) : (
              <ul className="m-0 list-none space-y-2 p-0">
                {[...reports].reverse().map((r) => (
                  <li key={r.report_id} className={`card text-sm ${newReportIds.has(r.report_id) ? "animate-slideIn motion-reduce:animate-none" : ""}`}>
                    <p className="m-0 flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{r.locality}</span>
                      <span className="text-muted">{fmtDateTime(r.created_at)}</span>
                      <Badge className={r.effect === "raised" ? "bg-alertBg text-alert" : r.effect === "lowered" ? "bg-normalBg text-normal" : "bg-sunken text-text"}>
                        {r.effect === "raised" ? "Raised the alert" : r.effect === "lowered" ? "Lowered the alert" : "No change"}
                      </Badge>
                    </p>
                    <p className="m-0 mt-1">
                      <span className="mono">{r.households_visited}</span> households visited, <span className="mono">{r.relevant_cases}</span> with matching symptoms
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="space-y-4 lg:col-span-5" aria-labelledby="actions-h" id="actions">
          <h2 id="actions-h" className="text-h2">Drafted actions</h2>
          {explainQ.loading && !shownExplanation ? (
            <div aria-busy="true" className="space-y-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-40 w-full" />
              ))}
            </div>
          ) : !shownExplanation ? (
            <p className="m-0 text-muted">Actions are drafted once the explanation is ready.</p>
          ) : (
            <>
              <TextActionCard
                action="distributor_note"
                draft={shownExplanation.actions.distributor_note}
                approved={approvals.distributor_note ?? null}
                approver={approver}
                onApprover={setApprover}
                readOnly={readOnly}
                busy={busy === "distributor_note"}
                auditHref={auditHref}
                onApprove={(a, t) => void approve(a, t)}
              />
              <TextActionCard
                action="officer_note"
                draft={shownExplanation.actions.officer_note}
                approved={approvals.officer_note ?? null}
                approver={approver}
                onApprover={setApprover}
                readOnly={readOnly}
                busy={busy === "officer_note"}
                auditHref={auditHref}
                onApprove={(a, t) => void approve(a, t)}
              />
              <VisitListCard
                draft={shownExplanation.actions.asha_visit_list}
                approved={approvals.asha_visit_list ?? null}
                approver={approver}
                onApprover={setApprover}
                readOnly={readOnly}
                busy={busy === "asha_visit_list"}
                auditHref={auditHref}
                onApprove={(a, t, v) => void approve(a, t, v)}
              />
              <p className="m-0 text-sm text-muted">Nothing is sent until you approve it. Every approval is logged.</p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
