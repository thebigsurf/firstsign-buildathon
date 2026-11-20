import { Image as ImageIcon, Inbox as InboxIcon, MessageSquareText, Mic, Plus } from "lucide-react";
import { useRef } from "react";
import { cx, fmtTime, initials, langOf } from "../../lib/format";
import { useRefData } from "../../lib/refdata";
import type { MessageStatus, MessageType } from "../../types";
import { MessageStatusPill } from "../ui/Badge";
import { Button } from "../ui/Button";
import { EmptyState, ErrorPanel, Skeleton } from "../ui/States";
import type { ApiError } from "../../api";

export interface ListMessage {
  id: string;
  chemist_id: string;
  received_at: string;
  type: MessageType;
  text?: string | null;
  status: MessageStatus;
  hasFlags: boolean;
  local: boolean;
}

export type StatusFilter = "all" | MessageStatus;

const FILTERS: Array<[StatusFilter, string]> = [
  ["all", "All"],
  ["new", "New"],
  ["parsed", "Parsed"],
  ["approved", "Approved"],
];

const TYPE_ICON = { voice: Mic, photo: ImageIcon, text: MessageSquareText } as const;

function preview(m: ListMessage): string {
  if (m.type === "voice") return "Voice note";
  if (m.type === "photo") return "Photo of handwritten list";
  const t = m.text ?? "";
  return t.length > 40 ? `${t.slice(0, 40)}...` : t;
}

interface MessageListProps {
  messages: ListMessage[];
  loading: boolean;
  error: ApiError | null;
  onRetry: () => void;
  selectedId: string | null;
  onSelect: (id: string) => void;
  filter: StatusFilter;
  onFilter: (f: StatusFilter) => void;
  onNew: () => void;
}

export function MessageList({ messages, loading, error, onRetry, selectedId, onSelect, filter, onFilter, onNew }: MessageListProps) {
  const { chemistById } = useRefData();
  const listRef = useRef<HTMLUListElement>(null);
  const shown = messages.filter((m) => filter === "all" || m.status === filter);

  const onKeyDown = (e: React.KeyboardEvent): void => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const buttons = Array.from(listRef.current?.querySelectorAll<HTMLButtonElement>("button[data-msg]") ?? []);
    const idx = buttons.findIndex((b) => b === document.activeElement);
    if (idx === -1) return;
    e.preventDefault();
    buttons[Math.max(0, Math.min(buttons.length - 1, idx + (e.key === "ArrowDown" ? 1 : -1)))]?.focus();
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <div className="space-y-3 border-b border-border p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-h3">
            Messages
            <span className="mono rounded-full bg-sunken px-2 text-sm" aria-label={`${messages.length} messages`}>
              {messages.length}
            </span>
          </h2>
          <Button size="sm" variant="secondary" icon={<Plus size={16} aria-hidden="true" />} onClick={onNew}>
            New message
          </Button>
        </div>
        <div role="radiogroup" aria-label="Filter messages" className="flex flex-wrap gap-2">
          {FILTERS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="radio"
              aria-checked={filter === id}
              onClick={() => onFilter(id)}
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

      <div className="min-h-0 flex-1 overflow-y-auto" aria-busy={loading}>
        {loading && messages.length === 0 ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-[72px] w-full" />
            ))}
          </div>
        ) : error && messages.length === 0 ? (
          <div className="p-4">
            <ErrorPanel error={error} message="We could not load the messages." onRetry={onRetry} />
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            icon={InboxIcon}
            title={messages.length === 0 ? "No messages yet" : "Nothing in this filter"}
            body={messages.length === 0 ? "New orders from chemists appear here." : "Try another filter."}
          />
        ) : (
          <ul ref={listRef} onKeyDown={onKeyDown} className="m-0 list-none p-0" aria-label="Messages from chemists">
            {shown.map((m, idx) => {
              const chemist = chemistById(m.chemist_id);
              const name = chemist?.shop_name ?? m.chemist_id;
              const Icon = TYPE_ICON[m.type];
              const selected = m.id === selectedId;
              const tabStop = selected || (idx === 0 && !shown.some((x) => x.id === selectedId));
              return (
                <li key={m.id} className="border-b border-border">
                  <button
                    type="button"
                    data-msg={m.id}
                    tabIndex={tabStop ? 0 : -1}
                    aria-current={selected ? "true" : undefined}
                    aria-keyshortcuts="ArrowDown ArrowUp"
                    onClick={() => onSelect(m.id)}
                    className={cx(
                      "relative flex min-h-[72px] w-full items-center gap-3 px-4 py-2 text-left hover:bg-sunken",
                      selected && "bg-accentSoft hover:bg-accentSoft",
                    )}
                  >
                    {selected && <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] bg-accent" />}
                    <span aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sunken text-sm font-semibold uppercase">
                      {initials(name)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-baseline justify-between gap-2">
                        <span className="truncate font-semibold">{name}</span>
                        <span className="mono shrink-0 text-sm text-muted">{fmtTime(m.received_at)}</span>
                      </span>
                      <span className="flex items-center gap-1.5 text-sm text-muted">
                        <Icon size={14} aria-hidden="true" className="shrink-0" />
                        <span className="truncate">{preview(m)}</span>
                      </span>
                      <span className="mt-1 flex items-center gap-2">
                        <MessageStatusPill status={m.status} hasFlags={m.hasFlags} />
                        {m.local && <span className="text-xs text-muted">Added now</span>}
                        <span className="ml-auto flex items-center gap-1.5">
                          {chemist && <span className="mono text-xs text-muted">{chemist.pin}</span>}
                          <span className="rounded bg-sunken px-1.5 text-xs uppercase">{chemist ? langOf(chemist.language) : ""}</span>
                        </span>
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
