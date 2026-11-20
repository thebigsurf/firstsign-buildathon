import { Ban, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { pct } from "../../lib/format";
import { searchCatalogue } from "../../lib/order";
import type { Alternative, CatalogueItem } from "../../types";

interface Option {
  id: string;
  item: CatalogueItem | null;
  label: string;
  detail: string;
  score?: number;
  kind: "product" | "not_available";
}

interface ProductPickerProps {
  catalogue: CatalogueItem[];
  alternatives?: Alternative[];
  onPick: (item: CatalogueItem) => void;
  onMarkNotAvailable?: () => void;
  onClose: () => void;
  label?: string;
}

function describe(item: CatalogueItem): string {
  return [item.strength, item.form, item.pack].filter(Boolean).join(", ");
}

/** Combobox + listbox: suggestions from the AI first, then a catalogue search. Keyboard: arrows, Home/End, Enter, Escape. */
export function ProductPicker({ catalogue, alternatives = [], onPick, onMarkNotAvailable, onClose, label = "Search the catalogue" }: ProductPickerProps) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const options = useMemo<Option[]>(() => {
    const bySku = new Map(catalogue.map((c) => [c.sku_id, c]));
    const out: Option[] = [];
    if (!query.trim()) {
      for (const alt of [...alternatives].sort((a, b) => b.score - a.score).slice(0, 5)) {
        const item = bySku.get(alt.sku_id);
        if (item) out.push({ id: item.sku_id, item, label: item.brand, detail: describe(item), score: alt.score, kind: "product" });
      }
    }
    const seen = new Set(out.map((o) => o.id));
    const found = query.trim() ? searchCatalogue(catalogue, query, 8) : catalogue.slice(0, out.length ? 0 : 8);
    for (const item of found) {
      if (!seen.has(item.sku_id)) out.push({ id: item.sku_id, item, label: item.brand, detail: describe(item), kind: "product" });
    }
    if (onMarkNotAvailable) out.push({ id: "__na", item: null, label: "Mark not available", detail: "Asked for, but not in your stock list", kind: "not_available" });
    return out;
  }, [catalogue, alternatives, query, onMarkNotAvailable]);

  useEffect(() => setActive(0), [query]);

  const choose = (o: Option): void => {
    if (o.kind === "not_available") onMarkNotAvailable?.();
    else if (o.item) onPick(o.item);
  };

  const onKey = (e: React.KeyboardEvent): void => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(options.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      setActive(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActive(options.length - 1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (options[active]) choose(options[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      onClose();
    }
  };

  return (
    <div data-picker-root className="w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-border bg-surface p-2 shadow-2">
      <label className="relative block">
        <span className="sr-only">{label}</span>
        <Search size={16} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          ref={inputRef}
          role="combobox"
          aria-expanded="true"
          aria-controls={listId}
          aria-activedescendant={options[active] ? `${listId}-${active}` : undefined}
          aria-autocomplete="list"
          className="input pl-9"
          placeholder="Type a brand or medicine"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKey}
          onBlur={(e) => {
            if (!e.currentTarget.closest("[data-picker-root]")?.contains(e.relatedTarget as Node | null)) onClose();
          }}
        />
      </label>
      <ul id={listId} role="listbox" aria-label="Matching products" className="m-0 mt-2 max-h-64 list-none overflow-auto p-0">
        {options.length === 0 && <li className="px-3 py-2 text-sm text-muted">Nothing in the catalogue matches that.</li>}
        {options.map((o, i) => (
          <li
            key={o.id}
            id={`${listId}-${i}`}
            role="option"
            aria-selected={i === active}
            onMouseDown={(e) => {
              e.preventDefault();
              choose(o);
            }}
            onMouseEnter={() => setActive(i)}
            className={`flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-md px-3 py-1.5 text-sm ${
              i === active ? "bg-accentSoft" : ""
            } ${o.kind === "not_available" ? "mt-1 border-t border-border" : ""}`}
          >
            <span className="min-w-0">
              <span className="flex items-center gap-1.5 font-semibold">
                {o.kind === "not_available" && <Ban size={14} aria-hidden="true" />}
                {o.label}
              </span>
              <span className="block truncate text-muted">{o.detail}</span>
            </span>
            {o.score !== undefined && <span className="mono shrink-0 text-xs">{pct(o.score)}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
