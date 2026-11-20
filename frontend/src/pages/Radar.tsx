import { ChevronDown, ClipboardCopy, Radar as RadarIcon, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { GroupChip, LevelBadge, PinChip } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { EmptyState, ErrorPanel, Skeleton } from "../components/ui/States";
import { Sparkline } from "../components/ui/Sparkline";
import { useToast } from "../components/ui/Toast";
import { cx, fmtDate, LEVEL_RANK, plural, ratioText } from "../lib/format";
import { toApiError, useAsync, useDocumentTitle } from "../lib/hooks";
import { useRefData } from "../lib/refdata";
import type { Cell, Level, RadarItem } from "../types";

type Sort = "urgency" | "rise" | "area";

function levelOf(item: RadarItem): Level {
  return item.level ?? "alert";
}

function sortItems(items: RadarItem[], sort: Sort): RadarItem[] {
  const copy = [...items];
  if (sort === "area") return copy.sort((a, b) => a.area.localeCompare(b.area) || a.group.localeCompare(b.group));
  if (sort === "rise") return copy.sort((a, b) => b.ratio - a.ratio);
  return copy.sort((a, b) => LEVEL_RANK[levelOf(b)] - LEVEL_RANK[levelOf(a)] || b.ratio - a.ratio);
}

function RadarCard({ item, rank, cell }: { item: RadarItem; rank: number; cell: Cell | undefined }) {
  const { groupById, catalogue } = useRefData();
  const toast = useToast();
  const [all, setAll] = useState(false);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const group = groupById(item.group);
  const groupLabel = item.group_label || group?.label || item.group;
  const level = levelOf(item);
  const skus = all ? item.skus : item.skus.slice(0, 3);
  const unitOf = (id: string): string => catalogue.find((c) => c.sku_id === id)?.unit ?? "unit";

  const copy = async (): Promise<void> => {
    const chosen = picked.size > 0 ? item.skus.filter((s) => picked.has(s.sku_id)) : item.skus;
    const text = [
      `Reorder list: ${groupLabel} rising in ${item.area} (${item.pin}), ${ratioText(item.ratio)} normal`,
      ...chosen.map((s) => `- ${s.brand}: ${s.suggested_qty} ${unitOf(s.sku_id)}s`),
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      toast.show("success", "Reorder list copied");
    } catch {
      toast.show("error", "Could not copy. Select the list and copy it by hand.");
    }
  };

  const label = cell
    ? `${groupLabel} orders in ${item.area} over the last 30 days: today ${Math.round(cell.today)} units, normal ${Math.round(cell.baseline)}.`
    : "";

  return (
    <article className="card flex flex-col gap-4" aria-labelledby={`radar-${item.pin}-${item.group}`}>
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="mono pt-1 text-sm text-muted" aria-label={`Rank ${rank}`}>{rank}</span>
          <div>
            <h2 id={`radar-${item.pin}-${item.group}`} className="text-h3">{item.area}</h2>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <PinChip pin={item.pin} />
              <GroupChip label={groupLabel} labelHi={group?.label_hi} color={group?.color_hint} />
            </div>
          </div>
        </div>
        <LevelBadge level={level} />
      </header>

      <div>
        <p className="m-0 flex items-baseline gap-2">
          <span className="mono text-num-lg">{ratioText(item.ratio)}</span>
          <span className="text-muted">normal</span>
        </p>
        <p className="m-0 text-sm text-muted">{plural(item.chemists_affected, "chemist")} ordering above normal</p>
      </div>

      {cell ? <Sparkline series={cell.series} level={level} label={label} /> : <p className="m-0 text-sm text-muted">No chart for this area yet.</p>}

      <div>
        <h3 className="label-xs mb-2">Suggested stock</h3>
        {item.skus.length === 0 ? (
          <p className="m-0 text-sm text-muted">No stock suggestion for this group yet.</p>
        ) : (
          <ul className="m-0 list-none space-y-2 p-0">
            {skus.map((s) => (
              <li key={s.sku_id} className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id={`pick-${item.pin}-${item.group}-${s.sku_id}`}
                  checked={picked.has(s.sku_id)}
                  onChange={(e) =>
                    setPicked((cur) => {
                      const next = new Set(cur);
                      if (e.target.checked) next.add(s.sku_id);
                      else next.delete(s.sku_id);
                      return next;
                    })
                  }
                  className="mt-1 h-5 w-5 accent-[var(--accent)]"
                />
                <label htmlFor={`pick-${item.pin}-${item.group}-${s.sku_id}`} className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="font-semibold">{s.brand}</span>
                    <span className="mono shrink-0 text-sm">
                      +{s.suggested_qty} {unitOf(s.sku_id)}s
                    </span>
                  </span>
                  <span className="block text-sm text-muted">{s.reason}</span>
                  <span className="sr-only">Add to my reorder list</span>
                </label>
              </li>
            ))}
          </ul>
        )}
        {item.skus.length > 3 && (
          <Button variant="ghost" size="sm" className="mt-2" onClick={() => setAll((v) => !v)} aria-expanded={all} icon={<ChevronDown size={14} aria-hidden="true" className={cx(all && "rotate-180")} />}>
            {all ? "Show fewer" : `Show all ${item.skus.length}`}
          </Button>
        )}
      </div>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
        {item.alert_id ? (
          <Link to={`/officer/alert/${encodeURIComponent(item.alert_id)}?from=distributor`} className="inline-flex min-h-11 max-w-full items-center font-semibold text-accentText underline">
            Why is this rising?
          </Link>
        ) : (
          <span className="text-sm text-muted">No alert for this area.</span>
        )}
        <Button variant="secondary" size="sm" icon={<ClipboardCopy size={14} aria-hidden="true" />} onClick={() => void copy()} disabled={item.skus.length === 0}>
          Copy reorder list
        </Button>
      </footer>
    </article>
  );
}

export function Radar() {
  useDocumentTitle("Stock radar");
  const { groups } = useRefData();
  const radar = useAsync((s) => api.radar(s), []);
  const signal = useAsync((s) => api.signal(30, s), []);
  const [sort, setSort] = useState<Sort>("urgency");
  const [filter, setFilter] = useState<Set<string>>(new Set());

  const cells = useMemo(() => new Map((signal.data?.cells ?? []).map((c) => [`${c.pin}|${c.group}`, c])), [signal.data]);
  const items = useMemo(() => {
    const all = radar.data ?? [];
    const shown = filter.size === 0 ? all : all.filter((i) => filter.has(i.group));
    return sortItems(shown, sort);
  }, [radar.data, filter, sort]);

  const alertAreas = (radar.data ?? []).filter((i) => levelOf(i) === "alert").length;
  const watchAreas = (radar.data ?? []).filter((i) => levelOf(i) === "watch").length;
  const present = new Set((radar.data ?? []).map((i) => i.group));
  const suppressed = signal.data?.suppressed ?? [];
  const { areaOf, groupLabel } = useRefData();

  const toggle = (id: string): void =>
    setFilter((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className="mx-auto max-w-[1440px] space-y-5 px-4 py-6 md:px-6 xl:px-8">
      <header className="space-y-1">
        <h1 className="text-h1">
          Stock radar <span lang="hi" className="text-muted">/ स्टॉक रडार</span>
        </h1>
        <p className="m-0 text-muted">Medicine groups rising in your area compared with normal. Simulated history for demo.</p>
      </header>

      <div className="flex flex-wrap items-center gap-2" aria-live="polite">
        <span className="rounded-full bg-alertBg px-3 py-1 text-sm font-semibold text-alert">Pin codes on alert: <span className="mono">{alertAreas}</span></span>
        <span className="rounded-full bg-watchBg px-3 py-1 text-sm font-semibold text-watch">Pin codes on watch: <span className="mono">{watchAreas}</span></span>
        {signal.data && <span className="rounded-full bg-sunken px-3 py-1 text-sm">Data as of {fmtDate(signal.data.as_of)}</span>}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div role="group" aria-label="Filter by medicine group" className="flex flex-wrap gap-2">
          {groups
            .filter((g) => present.has(g.id))
            .map((g) => (
              <button
                key={g.id}
                type="button"
                aria-pressed={filter.has(g.id)}
                onClick={() => toggle(g.id)}
                className={cx(
                  "min-h-9 rounded-full px-3 text-sm font-medium",
                  filter.has(g.id) ? "bg-accent text-accentFg" : "border border-borderStrong bg-surface hover:bg-sunken",
                )}
              >
                {g.label} <span lang="hi" className="opacity-80">{g.label_hi}</span>
              </button>
            ))}
        </div>
        <label className="flex items-center gap-2 text-sm font-medium">
          Sort by
          <select className="input w-auto" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            <option value="urgency">Urgency</option>
            <option value="rise">Biggest rise</option>
            <option value="area">Area name</option>
          </select>
        </label>
      </div>

      {radar.loading && !radar.data ? (
        <div aria-busy="true" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-96 w-full" />
          ))}
        </div>
      ) : radar.error ? (
        <ErrorPanel error={toApiError(radar.error)} message="We could not load the stock radar." onRetry={radar.reload} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={RadarIcon}
          title={filter.size > 0 ? "Nothing rising in these groups" : "Nothing is rising right now"}
          body={filter.size > 0 ? "Clear the group filter to see every area." : "We check every time an order is approved."}
          action={filter.size > 0 ? <Button variant="secondary" onClick={() => setFilter(new Set())}>Clear filter</Button> : undefined}
        />
      ) : (
        <ul className="m-0 grid list-none grid-cols-1 gap-4 p-0 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item, i) => (
            <li key={`${item.pin}-${item.group}`} className="flex">
              <div className="w-full">
                <RadarCard item={item} rank={i + 1} cell={cells.get(`${item.pin}|${item.group}`)} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {suppressed.length > 0 && (
        <details className="card">
          <summary className="flex min-h-11 cursor-pointer items-center gap-2 font-semibold">
            <ShieldCheck size={18} aria-hidden="true" className="text-normal" />
            Ignored: single-shop spikes ({suppressed.length})
          </summary>
          <p className="mt-2 text-sm text-muted">High volume from very few shops is not a wider rise, so FirstSign did not raise an alert.</p>
          <ul className="m-0 mt-3 list-none space-y-2 p-0">
            {suppressed.map((s) => (
              <li key={`${s.pin}-${s.group}`} className="rounded-md bg-sunken p-3 text-sm">
                <p className="m-0 flex flex-wrap items-center gap-2 font-semibold">
                  {areaOf(s.pin)} <PinChip pin={s.pin} /> {groupLabel(s.group)} <LevelBadge level="normal" />
                </p>
                <p className="m-0 mt-1">{s.why || `${ratioText(s.ratio)} normal, but only ${Math.round(s.breadth * 100)}% of shops moved.`}</p>
                <p className="m-0 mt-1 text-muted">Not a wider rise, so no alert was raised.</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
