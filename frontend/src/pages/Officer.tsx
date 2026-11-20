import { CheckCircle2, List, ListOrdered, Map as MapIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { AlertCard } from "../components/officer/AlertCard";
import AlertMap from "../components/officer/AlertMap";
import { Badge } from "../components/ui/Badge";
import { EmptyState, ErrorPanel, Skeleton } from "../components/ui/States";
import { cx, fmtDate, LEVEL_RANK } from "../lib/format";
import { toApiError, useAsync, useDocumentTitle, useMediaQuery, usePolling } from "../lib/hooks";
import { useRefData } from "../lib/refdata";
import type { Alert, AlertStatus, AshaVisit } from "../types";

type StatusFilter = AlertStatus | "all";

const FILTERS: Array<[StatusFilter, string]> = [
  ["open", "Open"],
  ["confirmed", "Confirmed"],
  ["dismissed", "Dismissed"],
  ["all", "All"],
];

function VisitNext() {
  const { ashas, areaOf } = useRefData();
  const visits = useAsync(
    async (signal) => {
      const settled = await Promise.allSettled(ashas.map((a) => api.ashaVisits(a.asha_id, signal)));
      const merged = new Map<string, AshaVisit>();
      for (const r of settled) {
        if (r.status !== "fulfilled") continue;
        for (const v of r.value) if (!merged.has(v.locality_id)) merged.set(v.locality_id, v);
      }
      return [...merged.values()].sort((a, b) => (b.approved_at ?? "").localeCompare(a.approved_at ?? "") || a.priority - b.priority);
    },
    [ashas.length],
  );
  usePolling(visits.reload, 20000);

  return (
    <section aria-labelledby="visit-next-h" className="card space-y-3">
      <h2 id="visit-next-h" className="flex items-center gap-2 text-h3">
        <ListOrdered size={18} aria-hidden="true" /> Visit next <span lang="hi" className="font-normal text-muted">/ अगला दौरा</span>
      </h2>
      {visits.loading && !visits.data ? (
        <Skeleton className="h-16 w-full" />
      ) : visits.error ? (
        <p className="m-0 text-sm text-muted">We could not load the visit list. It will retry on its own.</p>
      ) : (visits.data ?? []).length === 0 ? (
        <p className="m-0 text-sm text-muted">No visit list yet. Open an alert and approve one.</p>
      ) : (
        <ol className="m-0 list-none space-y-2 p-0">
          {(visits.data ?? []).slice(0, 8).map((v, i) => (
            <li key={v.locality_id} className="flex items-start gap-3 text-sm">
              <span className="mono flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accentSoft text-accentText" aria-hidden="true">
                {i + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="font-semibold">{v.name}</span>{" "}
                <span className="text-muted">
                  {v.pin ? areaOf(v.pin) : ""} · {v.landmark}
                </span>
                {v.reason && <span className="block text-muted">{v.reason}</span>}
              </span>
              {v.reported ? <Badge className="bg-normalBg text-normal">Reported</Badge> : <Badge className="border border-borderStrong text-text">Waiting</Badge>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function Officer() {
  useDocumentTitle("Map and alerts");
  const { pincodes, groups, chemists } = useRefData();
  const signal = useAsync((s) => api.signal(30, s), []);
  const alerts = useAsync((s) => api.alerts(s), []);
  const lg = useMediaQuery("(min-width: 1024px)");
  const [view, setView] = useState<"list" | "map">("list");
  const [filter, setFilter] = useState<StatusFilter>("open");
  const [group, setGroup] = useState("all");
  const [selectedPin, setSelectedPin] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [pulsePins, setPulsePins] = useState<Set<string>>(new Set());
  const prev = useRef(new Map<string, number>());
  const cardRefs = useRef(new Map<string, HTMLLIElement>());

  usePolling(alerts.reload, 20000);

  // One subtle pulse on the circles of any alert whose confidence just changed.
  useEffect(() => {
    if (!alerts.data) return;
    const changed = new Set<string>();
    for (const a of alerts.data) {
      const before = prev.current.get(a.alert_id);
      if (before !== undefined && Math.abs(before - a.confidence) > 0.001) a.pins.forEach((p) => changed.add(p));
      prev.current.set(a.alert_id, a.confidence);
    }
    if (changed.size === 0) return;
    setPulsePins(changed);
    const id = window.setTimeout(() => setPulsePins(new Set()), 900);
    return () => window.clearTimeout(id);
  }, [alerts.data]);

  const shown = useMemo<Alert[]>(() => {
    const all = alerts.data ?? [];
    return all
      .filter((a) => filter === "all" || a.status === filter)
      .sort((a, b) => LEVEL_RANK[b.level] - LEVEL_RANK[a.level] || b.confidence - a.confidence);
  }, [alerts.data, filter]);

  const selectedAlertId = useMemo(() => {
    if (hovered) return hovered;
    if (!selectedPin) return null;
    const cands = shown.filter((a) => a.pins.includes(selectedPin));
    return (group === "all" ? cands[0] : cands.find((a) => a.group === group) ?? cands[0])?.alert_id ?? null;
  }, [hovered, selectedPin, shown, group]);

  const highlightPin = useMemo(() => {
    const a = (alerts.data ?? []).find((x) => x.alert_id === selectedAlertId);
    return a?.pins[0] ?? selectedPin;
  }, [alerts.data, selectedAlertId, selectedPin]);

  const onSelectPin = (pin: string): void => {
    setSelectedPin(pin);
    const target = shown.find((a) => a.pins.includes(pin));
    if (target) cardRefs.current.get(target.alert_id)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    if (!lg) setView("list");
  };

  const openCount = (alerts.data ?? []).filter((a) => a.status === "open").length;
  const confirmedCount = (alerts.data ?? []).filter((a) => a.status === "confirmed").length;
  const showMap = lg || view === "map";
  const showList = lg || view === "list";

  const kpis: Array<[string, string]> = [
    ["Open alerts", String(openCount)],
    ["Confirmed by ASHAs", String(confirmedCount)],
    ["Chemists covered", String(chemists.length)],
    ["Data as of", signal.data ? fmtDate(signal.data.as_of) : "..."],
  ];

  return (
    <div className="mx-auto max-w-[1440px] space-y-4 px-4 py-4 md:px-6 xl:px-8">
      <h1 className="sr-only">Map and alerts</h1>
      <dl aria-label="Summary" className="m-0 grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-border bg-surface px-3 py-2">
            <dt className="text-sm text-muted">{label}</dt>
            <dd className="mono m-0 text-xl font-semibold">{value}</dd>
          </div>
        ))}
      </dl>

      {!lg && (
        <div role="radiogroup" aria-label="Show list or map" className="inline-flex rounded-lg bg-sunken p-1">
          {([["list", "List", List], ["map", "Map", MapIcon]] as const).map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={view === id}
              onClick={() => setView(id)}
              className={cx("inline-flex min-h-9 items-center gap-1.5 rounded-md px-4 text-sm font-medium", view === id ? "bg-surface shadow-1" : "text-muted")}
            >
              <Icon size={16} aria-hidden="true" /> {label}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-4 xl:h-[calc(100dvh-var(--shell-h)-170px)] xl:min-h-[520px] xl:grid-cols-[3fr_2fr]">
        {showMap && (
          <div className="h-[45dvh] min-h-[320px] xl:h-full">
            {pincodes.length === 0 && signal.loading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              <AlertMap
                className="h-full"
                pincodes={pincodes}
                cells={signal.data?.cells ?? []}
                group={group}
                groups={groups}
                selectedPin={highlightPin ?? null}
                pulsePins={pulsePins}
                onSelectPin={onSelectPin}
                onGroupChange={setGroup}
              />
            )}
          </div>
        )}

        {showList && (
          <div className="space-y-4 xl:h-full xl:overflow-y-auto xl:pr-1">
            <VisitNext />
            <section aria-labelledby="alerts-h" className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 id="alerts-h" className="text-h3">
                  Alerts <span lang="hi" className="font-normal text-muted">/ चेतावनियाँ</span>{" "}
                  <span className="mono text-sm text-muted">({shown.length})</span>
                </h2>
                <div role="radiogroup" aria-label="Filter alerts" className="flex flex-wrap gap-1.5">
                  {FILTERS.map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      role="radio"
                      aria-checked={filter === id}
                      onClick={() => setFilter(id)}
                      className={cx(
                        "min-h-9 rounded-full px-3 text-sm font-medium",
                        filter === id ? "bg-accent text-accentFg" : "border border-borderStrong bg-surface hover:bg-sunken",
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {alerts.loading && !alerts.data ? (
                <div aria-busy="true" className="space-y-3">
                  {[0, 1, 2].map((i) => (
                    <Skeleton key={i} className="h-40 w-full" />
                  ))}
                </div>
              ) : alerts.error && !alerts.data ? (
                <ErrorPanel error={toApiError(alerts.error)} message="We could not load the alerts." onRetry={alerts.reload} />
              ) : shown.length === 0 ? (
                <EmptyState
                  icon={CheckCircle2}
                  title={filter === "open" ? "No alerts" : "Nothing in this filter"}
                  body={filter === "open" ? "All areas look normal today." : "Try another filter."}
                />
              ) : (
                <ul className="m-0 list-none space-y-3 p-0">
                  {shown.map((a) => (
                    <AlertCard
                      key={a.alert_id}
                      ref={(el) => {
                        if (el) cardRefs.current.set(a.alert_id, el);
                        else cardRefs.current.delete(a.alert_id);
                      }}
                      alert={a}
                      selected={selectedAlertId === a.alert_id}
                      asOf={signal.data?.as_of}
                      onHover={(id) => {
                        setHovered(id);
                        if (id) setSelectedPin(null);
                      }}
                    />
                  ))}
                </ul>
              )}
              {signal.data && (
                <p className="m-0 text-xs text-muted">{signal.data.note ?? "Simulated history for demo."}</p>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
