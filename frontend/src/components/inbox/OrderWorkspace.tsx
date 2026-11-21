import { ArrowLeft, BadgeCheck, Cpu, FileSearch, RefreshCw, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cx, fmtDate, fmtTime, langName, langOf, plural } from "../../lib/format";
import { countLines, highlightSegments, isActive, needsCheck, type EditableLine, type Work } from "../../lib/order";
import { useRefData } from "../../lib/refdata";
import type { CatalogueItem, MessageType } from "../../types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { ErrorPanel, Skeleton } from "../ui/States";
import { AddLine, OrderLines } from "./OrderLines";

export interface WorkspaceMessage {
  id: string;
  chemist_id: string;
  received_at: string;
  type: MessageType;
  text?: string | null;
  mediaUrl: string | null;
  local: boolean;
}

interface Props {
  message: WorkspaceMessage;
  work: Work;
  approvers: string[];
  approver: string;
  onApprover: (a: string) => void;
  approving: boolean;
  onUpdateLine: (key: string, fn: (l: EditableLine) => EditableLine) => void;
  onAddLine: (item: CatalogueItem) => void;
  onRestore: (key: string) => void;
  onDismissNA: (text: string) => void;
  onReread: () => void;
  onManual: () => void;
  onSkip: () => void;
  onApprove: () => void;
  onBack?: () => void;
}

const STEPS_VOICE = ["Listening", "Reading", "Matching to your catalogue"];
const STEPS_PHOTO = ["Looking at the photo", "Reading the handwriting", "Matching to your catalogue"];

function ParseProgress({ startedAt, type }: { startedAt: number; type: MessageType }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, []);
  const secs = (now - startedAt) / 1000;
  const steps = type === "photo" ? STEPS_PHOTO : STEPS_VOICE;
  const current = secs < 3 ? 0 : secs < 7 ? 1 : 2;
  return (
    <div role="status" aria-live="polite" className="space-y-4">
      <ol className="m-0 flex list-none flex-wrap items-center gap-x-6 gap-y-2 p-0">
        {steps.map((s, i) => (
          <li key={s} className={cx("flex items-center gap-2 text-sm", i === current ? "font-semibold text-text" : i < current ? "text-muted" : "text-muted")}>
            <span
              aria-hidden="true"
              className={cx("mono flex h-6 w-6 items-center justify-center rounded-full text-xs", i <= current ? "bg-accent text-accentFg" : "bg-sunken")}
            >
              {i + 1}
            </span>
            {s}
            {i === current && <span className="sr-only"> (now)</span>}
          </li>
        ))}
        <li className="mono ml-auto text-sm text-muted">{secs.toFixed(1)} s</li>
      </ol>
      {secs > 8 && <p className="m-0 text-sm text-muted">Still working. The AI can take a few seconds on voice notes.</p>}
      <div aria-hidden="true" className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    </div>
  );
}

function SourcePanel({ message, work, lang }: { message: WorkspaceMessage; work: Work; lang: string }) {
  const [zoom, setZoom] = useState(false);
  useEffect(() => {
    if (!zoom) return;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") setZoom(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [zoom]);

  const transcript = work.parsed?.transcript ?? "";
  const unsure = work.lines.filter(needsCheck).map((l) => l.line.raw_text);
  const segments = highlightSegments(transcript, unsure);

  return (
    <details open className="rounded-lg border border-border bg-surface">
      <summary className="flex min-h-11 cursor-pointer items-center px-4 text-sm font-semibold">
        {message.type === "voice" ? "Voice note and transcript" : message.type === "photo" ? "Photo of the list" : "Message text"}
      </summary>
      <div className="grid gap-4 border-t border-border p-4 xl:grid-cols-2">
        {message.type === "voice" && (
          <>
            {message.mediaUrl ? (
              <audio controls src={message.mediaUrl} className="w-full" aria-label="Play the voice note" />
            ) : (
              <p className="m-0 text-sm text-muted">The audio is not stored after it is read.</p>
            )}
            <div>
              <p className="label-xs mb-1">{langName(work.parsed?.language ?? lang)} transcript</p>
              {transcript ? (
                <p lang={langOf(work.parsed?.language ?? lang)} className="m-0 leading-relaxed">
                  {segments.map((s, i) =>
                    s.hit ? (
                      <mark key={i} className="bg-transparent text-text underline decoration-confUnc decoration-2 [text-decoration-style:dotted]">
                        {s.text}
                      </mark>
                    ) : (
                      <span key={i}>{s.text}</span>
                    ),
                  )}
                </p>
              ) : (
                <p className="m-0 text-sm text-muted">{work.phase === "parsing" ? "Listening..." : "No transcript."}</p>
              )}
              {unsure.length > 0 && <p className="mt-2 text-xs text-muted">Dotted underline marks words behind lines that need a check.</p>}
            </div>
          </>
        )}
        {message.type === "photo" && (
          <>
            {message.mediaUrl ? (
              <button
                type="button"
                onClick={() => setZoom((z) => !z)}
                aria-label={zoom ? "Shrink the photo" : "Zoom into the photo"}
                aria-pressed={zoom}
                className={cx("block overflow-auto rounded-lg border border-border", zoom ? "cursor-zoom-out" : "cursor-zoom-in")}
              >
                <img
                  src={message.mediaUrl}
                  alt="Photo of the chemist's handwritten medicine list"
                  className={cx("max-w-none", zoom ? "w-[200%]" : "w-full max-h-72 object-contain")}
                />
              </button>
            ) : (
              <p className="m-0 text-sm text-muted">The photo is not stored after it is read.</p>
            )}
            <div>
              <p className="label-xs mb-1">What the AI read from the photo</p>
              <p lang={langOf(work.parsed?.language ?? lang)} className="m-0 whitespace-pre-line leading-relaxed">
                {transcript || (work.phase === "parsing" ? "Reading..." : "No text was read.")}
              </p>
            </div>
          </>
        )}
        {message.type === "text" && (
          <blockquote lang={lang} className="m-0 rounded-md border-l-4 border-borderStrong bg-sunken p-3 xl:col-span-2">
            {message.text}
          </blockquote>
        )}
      </div>
    </details>
  );
}

function jumpToStatus(status: "uncertain" | "unknown"): void {
  const el = document.querySelector<HTMLElement>(`[data-line-status="${status}"] [data-first-control]`);
  el?.scrollIntoView({ block: "center", behavior: "smooth" });
  el?.focus({ preventScroll: true });
}

export function OrderWorkspace(props: Props) {
  const { message, work, approvers, approver, approving } = props;
  const { chemistById, areaOf, health, catalogue } = useRefData();
  const location = useLocation();
  const chemist = chemistById(message.chemist_id);
  const lang = chemist?.language ?? "hi";
  const readOnly = work.phase === "approved";
  const reasonId = useId();
  const approverId = useId();

  const counts = countLines(work.lines);
  const active = work.lines.filter(isActive).filter((l) => l.resolution !== "removed");
  const badQty = active.filter((l) => l.line.qty < 1).length;
  const noSku = active.filter((l) => !l.line.sku_id && !needsCheck(l)).length;
  const removed = work.lines.filter((l) => l.resolution === "removed");
  const naLines = work.lines.filter((l) => l.resolution === "not_available");
  const naApi = (work.parsed?.not_available ?? []).filter((t) => !work.dismissedNA.includes(t));

  const reason =
    counts.pending > 0
      ? `${plural(counts.pending, "line")} still ${counts.pending === 1 ? "needs" : "need"} a check.`
      : badQty > 0
        ? `${plural(badQty, "line")} ${badQty === 1 ? "has" : "have"} no quantity. Enter 1 or more.`
        : noSku > 0
          ? `${plural(noSku, "line")} ${noSku === 1 ? "has" : "have"} no product. Pick one or remove it.`
          : active.length === 0
            ? "Add at least one line before you approve."
            : "";
  const canApprove = reason === "" && !readOnly && work.phase === "ready" && !approving;

  const pendingUncertain = work.lines.filter((l) => needsCheck(l) && l.ai?.status === "uncertain").length;
  const pendingUnknown = work.lines.filter((l) => needsCheck(l) && l.ai?.status === "unknown").length;
  const matchedNow = counts.total - pendingUncertain - pendingUnknown;

  const summaryText =
    work.phase !== "ready"
      ? ""
      : counts.pending > 0
        ? `Check ${plural(counts.pending, "line")} before you approve.`
        : "Every line is checked. Ready to approve.";

  const model = work.parsed?.model;
  const latency = work.parsed ? (work.parsed.latency_ms / 1000).toFixed(1) : null;
  const auditLink = `${location.pathname}?${new URLSearchParams({ ...(message.id ? { msg: message.id } : {}), view: "audit" }).toString()}`;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 md:p-5">
        {(work.phase === "ready" || work.phase === "error") && !readOnly && (
          <button
            type="button"
            onClick={() => document.getElementById(approverId)?.focus()}
            className="sr-only focus:not-sr-only focus:inline-flex focus:min-h-11 focus:items-center focus:rounded-lg focus:bg-accent focus:px-4 focus:text-accentFg"
          >
            Skip to the approve bar
          </button>
        )}
        {props.onBack && (
          <button type="button" onClick={props.onBack} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-accentText">
            <ArrowLeft size={16} aria-hidden="true" /> Back to messages
          </button>
        )}

        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-h2">{chemist?.shop_name ?? message.chemist_id}</h2>
            <p className="m-0 mt-1 text-sm text-muted">
              {chemist?.owner_first_name} · <span className="mono">{chemist?.pin}</span> {chemist ? areaOf(chemist.pin) : ""} ·{" "}
              {langName(lang)} · {fmtDate(message.received_at)}, <span className="mono">{fmtTime(message.received_at)}</span>
              {chemist?.software && <span className="ml-2 rounded bg-sunken px-1.5 py-0.5 text-xs capitalize">{chemist.software}</span>}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {model && (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1">
                <Cpu size={14} aria-hidden="true" />
                <span className="mono text-xs">{model}</span>
                {latency && <span className="mono text-xs text-muted">Read in {latency} s</span>}
              </span>
            )}
            {health?.offline && <Badge className="bg-watchBg text-watch">Demo mode: results are pre-recorded</Badge>}
          </div>
        </header>

        {readOnly && (
          <div className="panel-ok flex flex-wrap items-center justify-between gap-2" role="status">
            <span className="flex items-center gap-2 font-semibold">
              <BadgeCheck size={20} aria-hidden="true" className="animate-draw motion-reduce:animate-none" />
              Approved by {work.approvedBy ?? "a clerk"}
              {work.approvedAt ? ` at ${fmtTime(work.approvedAt)}` : ""}
            </span>
            <Link to={auditLink} className="font-semibold underline">
              View audit
            </Link>
          </div>
        )}

        <SourcePanel message={message} work={work} lang={lang} />

        {work.phase === "parsing" && <ParseProgress startedAt={work.startedAt} type={message.type} />}

        {work.phase === "error" && (
          <div className="space-y-3">
            <ErrorPanel message="We could not read this message." detail={work.error?.detail || work.error?.message} />
            <div className="flex flex-wrap gap-2">
              <Button onClick={props.onReread} icon={<RefreshCw size={16} aria-hidden="true" />}>
                Try again
              </Button>
              <Button variant="secondary" onClick={props.onManual}>
                Enter manually
              </Button>
            </div>
          </div>
        )}

        {(work.phase === "ready" || work.phase === "approved") && (
          <>
            <section aria-labelledby="summary-h" className="space-y-3">
              <h2 id="summary-h" className="sr-only">Summary</h2>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                <li><span className="inline-flex min-h-9 items-center rounded-full bg-sunken px-3 text-sm font-medium">{plural(counts.total, "line")}</span></li>
                <li><span className="inline-flex min-h-9 items-center rounded-full bg-confHighBg px-3 text-sm font-semibold text-confHigh">{matchedNow} matched</span></li>
                {pendingUncertain > 0 && (
                  <li>
                    <button type="button" onClick={() => jumpToStatus("uncertain")} className="inline-flex min-h-9 items-center rounded-full bg-confUncBg px-3 text-sm font-semibold text-confUnc">
                      {pendingUncertain} check this
                    </button>
                  </li>
                )}
                {pendingUnknown > 0 && (
                  <li>
                    <button type="button" onClick={() => jumpToStatus("unknown")} className="inline-flex min-h-9 items-center rounded-full bg-confUnkBg px-3 text-sm font-semibold text-confUnk">
                      {pendingUnknown} not found
                    </button>
                  </li>
                )}
              </ul>
              {!readOnly && work.lines.length > 0 && <p className="m-0 text-lg font-medium" aria-live="polite">{summaryText}</p>}
              {!readOnly && work.lines.length === 0 && (
                <div className="rounded-lg border border-dashed border-borderStrong p-4">
                  <p className="m-0 font-semibold">No medicines found in this message.</p>
                  <p className="m-0 mt-1 text-sm text-muted">Add the lines yourself below, or try reading it again.</p>
                </div>
              )}
            </section>

            <OrderLines
              lines={work.lines}
              lang={lang}
              catalogue={catalogue}
              readOnly={readOnly}
              onUpdate={props.onUpdateLine}
            />

            {!readOnly && (
              <div className="flex flex-wrap items-start gap-3">
                <AddLine catalogue={catalogue} onAdd={props.onAddLine} />
              </div>
            )}

            {removed.length > 0 && !readOnly && (
              <details className="rounded-lg border border-border bg-surface px-4 py-2">
                <summary className="min-h-9 cursor-pointer text-sm font-semibold">Removed by you ({removed.length})</summary>
                <ul className="m-0 mt-2 list-none space-y-1 p-0">
                  {removed.map((l) => (
                    <li key={l.key} className="flex items-center justify-between gap-2 text-sm">
                      <span lang={lang}>{l.line.raw_text}</span>
                      <Button variant="ghost" size="sm" onClick={() => props.onRestore(l.key)}>
                        Restore
                      </Button>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            <section aria-labelledby="na-h" className="space-y-2">
              <h2 id="na-h" className="text-h3">
                Not available <span lang="hi" className="text-muted">/ नहीं है</span>
              </h2>
              {naLines.length + naApi.length === 0 ? (
                <p className="m-0 text-sm text-muted">Nothing here. Items you mark as not available will be listed.</p>
              ) : (
                <>
                  <p className="m-0 text-sm text-muted">These were asked for but are not in your stock list.</p>
                  <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                    {naApi.map((t) => (
                      <li key={`api-${t}`} className="inline-flex items-center gap-1 rounded-full border border-borderStrong bg-surface py-0.5 pl-3 text-sm">
                        <span lang={lang}>{t}</span>
                        {!readOnly && (
                          <button type="button" aria-label={`Dismiss ${t}`} onClick={() => props.onDismissNA(t)} className="flex min-h-9 min-w-9 items-center justify-center rounded-full hover:bg-sunken">
                            <X size={14} aria-hidden="true" />
                          </button>
                        )}
                      </li>
                    ))}
                    {naLines.map((l) => (
                      <li key={l.key} className="inline-flex items-center gap-1 rounded-full border border-borderStrong bg-surface py-0.5 pl-3 text-sm">
                        <span lang={lang}>{l.line.raw_text}</span>
                        {!readOnly && (
                          <button type="button" aria-label={`Put ${l.line.raw_text} back on the order`} onClick={() => props.onRestore(l.key)} className="flex min-h-9 min-w-9 items-center justify-center rounded-full hover:bg-sunken">
                            <X size={14} aria-hidden="true" />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>

            {work.parsed?.notes && (
              <p className="m-0 rounded-md bg-sunken p-3 text-sm text-muted">
                <span className="font-semibold text-text">Note from the AI: </span>
                {work.parsed.notes}
              </p>
            )}
          </>
        )}
      </div>

      {(work.phase === "ready" || work.phase === "error") && !readOnly && (
        <div className="sticky bottom-0 border-t border-border bg-surface p-3 md:px-5">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <p className="m-0 text-sm">
              <span className="mono">{counts.total}</span> lines, <span className="mono">{counts.edited}</span> changed by you,{" "}
              <span className="mono">{counts.notAvailable + naApi.length}</span> not available
            </p>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              {approvers.length > 1 ? (
                <>
                  <label htmlFor={approverId} className="text-sm font-medium">
                    Approving as
                  </label>
                  <select id={approverId} className="input w-auto" value={approver} onChange={(e) => props.onApprover(e.target.value)}>
                    {approvers.map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </>
              ) : (
                <p id={approverId} tabIndex={-1} className="m-0 text-sm">
                  Approving as <strong>{approver}</strong>
                </p>
              )}
              <Button variant="ghost" onClick={props.onSkip}>
                Skip
              </Button>
              <Button variant="secondary" onClick={props.onReread} icon={<FileSearch size={16} aria-hidden="true" />}>
                Re-read message
              </Button>
              <Button
                disabled={!canApprove}
                loading={approving}
                aria-describedby={reason ? reasonId : undefined}
                onClick={props.onApprove}
              >
                Approve and send to billing
              </Button>
            </div>
          </div>
          {reason && (
            <p id={reasonId} className="m-0 mt-2 text-right text-sm font-medium text-confUnc" role="status">
              {reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
