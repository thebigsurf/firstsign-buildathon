import { ChevronDown, ClipboardList, Download, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { api } from "../api";
import { csvCell, downloadText, fmtDateTime, cx } from "../lib/format";
import { useAsync } from "../lib/hooks";
import type { AuditEntry } from "../types";
import { Button } from "./ui/Button";
import { EmptyState, ErrorPanel, Skeleton } from "./ui/States";

type TypeFilter = "all" | "orders" | "actions" | "asha";

const KIND_LABEL: Record<string, string> = {
  order_approved: "Order approved",
  line_edited: "Line edited",
  line_edit: "Line edited",
  line_added: "Line added",
  line_removed: "Line removed",
  uncertain_accepted: "Uncertain line accepted",
  action_approved: "Action approved",
  asha_report: "ASHA report",
};

export function kindLabel(kind: string): string {
  return KIND_LABEL[kind] ?? kind.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

export function kindGroup(kind: string): Exclude<TypeFilter, "all"> | "other" {
  if (kind.includes("order") || kind.includes("line") || kind.includes("uncertain")) return "orders";
  if (kind.includes("action")) return "actions";
  if (kind.includes("asha")) return "asha";
  return "other";
}

function count(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (Array.isArray(v)) return v.length;
  return null;
}

export const entryId = (e: AuditEntry): string => e.id ?? e.audit_id ?? `${e.ts ?? e.at}-${e.kind}`;
export const entryTime = (e: AuditEntry): string => e.ts ?? e.at ?? "";
export const entryRef = (e: AuditEntry): string => e.ref_id ?? e.ref ?? "";
export const entryWho = (e: AuditEntry): string => e.approved_by || e.actor;

/** One plain sentence about an entry: the backend's own summary, or one built only from what the log holds. */
export function headline(e: AuditEntry): string {
  if (e.summary) return e.summary;
  const d = e.detail ?? {};
  const parts: string[] = [];
  const lines = count(d.lines) ?? count(d.line_count);
  const edited = count(d.edited) ?? count(d.edited_lines) ?? count(d.edits) ?? count(d.lines_edited) ?? count(d.edited_lines);
  const na = count(d.not_available);
  if (lines !== null) parts.push(`${lines} ${lines === 1 ? "line" : "lines"}`);
  if (edited !== null) parts.push(`${edited} edited`);
  if (na !== null) parts.push(`${na} marked not available`);
  if (typeof d.action === "string") parts.push(kindLabel(d.action));
  if (typeof d.households_visited === "number") parts.push(`${d.households_visited} households`);
  if (typeof d.alert_id === "string") parts.push(`alert ${d.alert_id}`);
  return parts.join(", ") || "Recorded";
}

function DetailList({ entry }: { entry: AuditEntry }) {
  const rows = Object.entries({
    ...(entry.before ? { "AI read": entry.before } : {}),
    ...(entry.after ? { "Approved as": entry.after } : {}),
    ...(entry.detail ?? {}),
  });
  if (rows.length === 0) return <p className="text-sm text-muted">No extra detail.</p>;
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted">{k.replace(/_/g, " ")}</dt>
          <dd className="mono min-w-0 whitespace-pre-wrap break-words text-xs">
            {typeof v === "string" || typeof v === "number" || typeof v === "boolean" ? String(v) : JSON.stringify(v, null, 1)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function AuditLog() {
  const { data, error, loading, reload } = useAsync((s) => api.audit(s), []);
  const [type, setType] = useState<TypeFilter>("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...(data ?? [])]
      .sort((a, b) => entryTime(b).localeCompare(entryTime(a)))
      .filter((e) => type === "all" || kindGroup(e.kind) === type)
      .filter((e) => !q || entryWho(e).toLowerCase().includes(q) || entryRef(e).toLowerCase().includes(q));
  }, [data, type, query]);

  const exportCsv = (): void => {
    const head = ["time", "who", "what", "reference", "detail"];
    const body = rows.map((e) => [fmtDateTime(entryTime(e)), entryWho(e), kindLabel(e.kind), entryRef(e), headline(e)].map(csvCell).join(","));
    downloadText("firstsign-audit-log.csv", [head.join(","), ...body].join("\n"));
  };

  const filters: Array<[TypeFilter, string]> = [
    ["all", "All"],
    ["orders", "Orders"],
    ["actions", "Actions"],
    ["asha", "ASHA reports"],
  ];

  return (
    <div className="space-y-4">
      <p className="text-muted">Every approval and every edit, with who and when. Nothing here can be changed or deleted.</p>

      <div className="flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Filter by type" className="flex flex-wrap gap-2">
          {filters.map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={type === id}
              onClick={() => setType(id)}
              className={cx(
                "min-h-9 rounded-full px-3 text-sm font-medium",
                type === id ? "bg-accent text-accentFg" : "border border-borderStrong bg-surface text-text hover:bg-sunken",
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="relative ml-auto block">
          <span className="sr-only">Search by name</span>
          <Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input w-44 pl-9" placeholder="Search by name" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <Button variant="secondary" size="sm" icon={<Download size={16} aria-hidden="true" />} onClick={exportCsv} disabled={rows.length === 0}>
          Download log
        </Button>
      </div>

      {loading && !data ? (
        <div aria-busy="true" className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : error ? (
        <ErrorPanel error={error} message="We could not load the audit log." onRetry={reload} />
      ) : rows.length === 0 ? (
        <EmptyState icon={ClipboardList} title="Nothing logged yet" body="Approvals appear here as they happen." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-sunken text-xs uppercase tracking-wide text-muted">
                <th scope="col" className="px-3 py-2">Time (IST)</th>
                <th scope="col" className="px-3 py-2">Who</th>
                <th scope="col" className="px-3 py-2">What</th>
                <th scope="col" className="px-3 py-2">Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => {
                const id = entryId(e);
                const expanded = open === id;
                return (
                  <tr key={id} className="border-t border-border align-top">
                    <td className="mono whitespace-nowrap px-3 py-3 text-xs">{fmtDateTime(entryTime(e))}</td>
                    <td className="px-3 py-3">{entryWho(e)}</td>
                    <td className="px-3 py-3">
                      {kindLabel(e.kind)}
                      <div className="mono text-xs text-muted">{entryRef(e)}</div>
                    </td>
                    <td className="px-3 py-3">
                      <button
                        type="button"
                        aria-expanded={expanded}
                        onClick={() => setOpen(expanded ? null : id)}
                        className="inline-flex min-h-9 items-center gap-1 text-left text-accentText hover:underline"
                      >
                        {headline(e)}
                        <ChevronDown size={14} aria-hidden="true" className={expanded ? "rotate-180" : ""} />
                      </button>
                      {expanded && (
                        <div className="mt-2 rounded-md bg-sunken p-3">
                          <DetailList entry={e} />
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
