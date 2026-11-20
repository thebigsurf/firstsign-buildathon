import { Ban, Check, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { confidenceWord, cx, pct } from "../../lib/format";
import {
  isEdited,
  productChanged,
  qtyChanged,
  needsCheck,
  uncertaintyReason,
  lineFromCatalogue,
  type EditableLine,
} from "../../lib/order";
import { useMediaQuery } from "../../lib/hooks";
import type { CatalogueItem } from "../../types";
import { EditedTag, LineStatusBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { ProductPicker } from "./ProductPicker";

interface Handlers {
  catalogue: CatalogueItem[];
  readOnly: boolean;
  onUpdate: (key: string, fn: (l: EditableLine) => EditableLine) => void;
}

function toneClass(row: EditableLine): string {
  if (!needsCheck(row)) return "";
  return row.ai?.status === "unknown"
    ? "bg-confUnkBg border-l-4 border-l-confUnk"
    : "bg-confUncBg border-l-4 border-l-confUnc";
}

function QtyInput({ row, readOnly, onUpdate }: { row: EditableLine } & Pick<Handlers, "readOnly" | "onUpdate">) {
  const [text, setText] = useState(String(row.line.qty));
  const invalid = row.line.qty < 1;
  const id = `qty-${row.key}`;
  const changed = qtyChanged(row);

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <label htmlFor={id} className="sr-only">
          Quantity for {row.line.raw_text}
        </label>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={1}
          value={text}
          disabled={readOnly}
          aria-invalid={invalid || undefined}
          aria-describedby={invalid ? `${id}-err` : undefined}
          onChange={(e) => {
            setText(e.target.value);
            const n = Math.floor(Number(e.target.value));
            onUpdate(row.key, (l) => ({ ...l, line: { ...l.line, qty: Number.isFinite(n) && n > 0 ? n : 0 } }));
          }}
          className="input mono w-24 text-right disabled:opacity-80"
        />
        {row.line.unit && <span className="text-sm text-muted">{row.line.unit}</span>}
      </div>
      {invalid && (
        <p id={`${id}-err`} className="text-sm text-alert">
          Enter 1 or more
        </p>
      )}
      {changed && row.ai && (
        <p className="mono text-xs text-muted">
          <span className="sr-only">edited by you, </span>was {row.ai.qty}
        </p>
      )}
    </div>
  );
}

function ConfidenceCell({ row }: { row: EditableLine }) {
  if (!row.ai) return <span className="text-sm text-muted">Added by you</span>;
  const c = row.ai.confidence;
  const word = confidenceWord(c);
  const color = c >= 0.75 ? "bg-confHigh" : c >= 0.45 ? "bg-confUnc" : "bg-confUnk";
  return (
    <div className="flex items-center gap-2" title={`AI confidence: ${pct(c)}, ${word.toLowerCase()}`}>
      <div
        role="meter"
        aria-label="AI confidence for this line"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(c * 100)}
        aria-valuetext={`${Math.round(c * 100)} percent, ${word.toLowerCase()}`}
        className="h-2 w-[52px] overflow-hidden rounded-full bg-sunken"
      >
        <div className={cx("h-2 rounded-full", color)} style={{ width: `${c * 100}%` }} />
      </div>
      <span className="mono text-sm">{pct(c)}</span>
    </div>
  );
}

function StatusCell({ row }: { row: EditableLine }) {
  if (needsCheck(row) && row.ai) return <LineStatusBadge status={row.ai.status} />;
  if (row.ai === null || row.resolution === "confirmed" || row.resolution === "changed") return <LineStatusBadge status="matched" confirmed />;
  return <LineStatusBadge status="matched" />;
}

function ProductCell({
  row,
  picking,
  setPicking,
  catalogue,
  readOnly,
  onUpdate,
}: { row: EditableLine; picking: boolean; setPicking: (b: boolean) => void } & Handlers) {
  const l = row.line;
  const flagged = needsCheck(row);
  const hasSku = Boolean(l.sku_id);
  const item = catalogue.find((c) => c.sku_id === l.sku_id);

  const apply = (picked: CatalogueItem): void => {
    onUpdate(row.key, (cur) => ({
      ...cur,
      line: { ...lineFromCatalogue(picked, cur.line.qty, cur.line.raw_text), alternatives: cur.line.alternatives },
      resolution: cur.ai && cur.ai.sku_id === picked.sku_id && cur.ai.status !== "unknown" ? "confirmed" : "changed",
    }));
    setPicking(false);
  };

  return (
    <div className="space-y-1.5">
      {hasSku ? (
        <div>
          <p className="m-0 font-semibold" data-first-control>
            {l.brand} {l.strength} {l.form}
          </p>
          <p className="m-0 text-sm text-muted">
            {item?.pack ? `${item.pack}` : ""}
            {item?.pack && l.molecule ? " · " : ""}
            {l.molecule}
          </p>
        </div>
      ) : (
        <p className="m-0 font-semibold text-confUnk">No match in your catalogue</p>
      )}
      {flagged && <p className="m-0 text-sm text-text">{uncertaintyReason(l)}</p>}
      {productChanged(row) && (
        <p className="m-0 flex flex-wrap items-center gap-2 text-sm">
          <EditedTag />
          <span className="text-muted line-through">
            AI read: {row.ai?.brand ? `${row.ai.brand} ${row.ai.strength ?? ""}`.trim() : "nothing found"}
          </span>
        </p>
      )}
      {!readOnly && (
        <div className="relative">
          {picking ? (
            <ProductPicker
              catalogue={catalogue}
              alternatives={l.alternatives}
              onPick={apply}
              onClose={() => setPicking(false)}
              onMarkNotAvailable={() => {
                onUpdate(row.key, (cur) => ({ ...cur, resolution: "not_available" }));
                setPicking(false);
              }}
            />
          ) : (
            <Button
              variant={hasSku ? "secondary" : "primary"}
              size="sm"
              icon={<Pencil size={14} aria-hidden="true" />}
              onClick={() => setPicking(true)}
              aria-label={`${hasSku ? "Change product" : "Pick product"} for ${l.raw_text}`}
              data-first-control={hasSku ? undefined : true}
            >
              {hasSku ? "Change" : "Pick product"}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function ActionsCell({ row, readOnly, onUpdate }: { row: EditableLine } & Pick<Handlers, "readOnly" | "onUpdate">) {
  if (readOnly) return null;
  const canConfirm = needsCheck(row) && row.ai?.status === "uncertain" && Boolean(row.line.sku_id);
  const label = row.line.raw_text;
  return (
    <div className="flex flex-wrap gap-1.5 lg:flex-col lg:items-stretch">
      {canConfirm && (
        <Button
          variant="primary"
          size="sm"
          icon={<Check size={14} aria-hidden="true" />}
          aria-label={`Confirm match for ${label}`}
          onClick={() => onUpdate(row.key, (l) => ({ ...l, resolution: "confirmed" }))}
        >
          Confirm
        </Button>
      )}
      <Button
        variant="secondary"
        size="sm"
        icon={<Ban size={14} aria-hidden="true" />}
        aria-label={`Mark not available: ${label}`}
        onClick={() => onUpdate(row.key, (l) => ({ ...l, resolution: "not_available" }))}
      >
        Not available
      </Button>
      <Button
        variant="ghost"
        size="sm"
        icon={<Trash2 size={14} aria-hidden="true" />}
        aria-label={`Remove line: ${label}`}
        onClick={() => onUpdate(row.key, (l) => ({ ...l, resolution: "removed" }))}
      >
        Remove
      </Button>
    </div>
  );
}

function AddedTag({ row }: { row: EditableLine }) {
  return isEdited(row) && row.ai === null ? <EditedTag /> : null;
}

function RawText({ row, lang }: { row: EditableLine; lang: string }) {
  return (
    <p lang={lang} className="m-0 rounded-md bg-sunken px-2 py-1 text-sm font-medium">
      {row.line.raw_text}
    </p>
  );
}

interface OrderLinesProps extends Handlers {
  lines: EditableLine[];
  lang: string;
}

export function OrderLines({ lines, lang, ...handlers }: OrderLinesProps) {
  const wide = useMediaQuery("(min-width: 1024px)");
  const [picking, setPicking] = useState<string | null>(null);
  const visible = lines.filter((l) => l.resolution !== "removed" && l.resolution !== "not_available");

  if (visible.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-borderStrong p-6 text-center text-muted">
        No lines on this order right now.
      </p>
    );
  }

  const productProps = (row: EditableLine) => ({
    row,
    picking: picking === row.key,
    setPicking: (b: boolean) => setPicking(b ? row.key : null),
    ...handlers,
  });

   if (!wide) {
    return (
      <ul className="m-0 list-none space-y-3 p-0" aria-label="Order lines">
        {visible.map((row) => (
          <li
            key={row.key}
            data-line-status={needsCheck(row) ? row.ai?.status : "ok"}
            className={cx("space-y-3 rounded-lg border border-border bg-surface p-3", toneClass(row))}
          >
            <div className="flex items-center justify-between gap-2">
              <StatusCell row={row} />
              <ConfidenceCell row={row} />
            </div>
            <RawText row={row} lang={lang} />
            <AddedTag row={row} />
            <ProductCell {...productProps(row)} />
            <QtyInput row={row} readOnly={handlers.readOnly} onUpdate={handlers.onUpdate} />
            <ActionsCell row={row} readOnly={handlers.readOnly} onUpdate={handlers.onUpdate} />
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full min-w-[860px] border-collapse text-left text-sm">
        <caption className="sr-only">Order lines read from the message</caption>
        <thead>
          <tr className="bg-sunken text-xs uppercase tracking-wide text-muted">
            <th scope="col" className="w-28 px-3 py-2">Status</th>
            <th scope="col" className="w-48 px-3 py-2">What they said</th>
            <th scope="col" className="px-3 py-2">Matched product</th>
            <th scope="col" className="w-36 px-3 py-2">Qty</th>
            <th scope="col" className="w-36 px-3 py-2">Confidence</th>
            <th scope="col" className="w-36 px-3 py-2">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => (
            <tr
              key={row.key}
              data-line-status={needsCheck(row) ? row.ai?.status : "ok"}
              className={cx("border-t border-border align-top", toneClass(row))}
            >
              <th scope="row" className="px-3 py-3 text-left font-normal">
                <StatusCell row={row} />
                <div className="mt-1"><AddedTag row={row} /></div>
              </th>
              <td className="px-3 py-3">
                <RawText row={row} lang={lang} />
              </td>
              <td className="px-3 py-3">
                <ProductCell {...productProps(row)} />
              </td>
              <td className="px-3 py-3">
                <QtyInput row={row} readOnly={handlers.readOnly} onUpdate={handlers.onUpdate} />
              </td>
              <td className="px-3 py-3">
                <ConfidenceCell row={row} />
              </td>
              <td className="px-3 py-3">
                <ActionsCell row={row} readOnly={handlers.readOnly} onUpdate={handlers.onUpdate} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AddLine({ catalogue, onAdd }: { catalogue: CatalogueItem[]; onAdd: (item: CatalogueItem) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      {open ? (
        <ProductPicker
          catalogue={catalogue}
          label="Search the catalogue to add a line"
          onPick={(item) => {
            onAdd(item);
            setOpen(false);
          }}
          onClose={() => setOpen(false)}
        />
      ) : (
        <Button variant="secondary" size="sm" icon={<Plus size={14} aria-hidden="true" />} onClick={() => setOpen(true)}>
          Add a line
        </Button>
      )}
    </div>
  );
}
