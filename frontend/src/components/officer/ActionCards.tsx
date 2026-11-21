import { ArrowDown, ArrowUp, BadgeCheck, ClipboardList, FileText, Pencil, Send, Trash2, Truck, type LucideIcon } from "lucide-react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../lib/AuthContext";
import { fmtTime } from "../../lib/format";
import type { ActionName, VisitItem } from "../../types";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";

export const OFFICERS = ["Dr. Meera (district officer)", "Dr. Kapoor (district officer)"];

export interface ApprovedState {
  by: string;
  at: string;
  text: string;
}

interface FrameProps {
  title: string;
  titleHi?: string;
  icon: LucideIcon;
  approved: ApprovedState | null;
  edited: boolean;
  children: ReactNode;
  footer: ReactNode;
  auditHref: string;
}

function Frame({ title, titleHi, icon: Icon, approved, edited, children, footer, auditHref }: FrameProps) {
  return (
    <section className="card space-y-3" aria-label={title}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-h3">
          <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
          {title}
          {titleHi && (
            <span lang="hi" className="font-normal text-muted">
              / {titleHi}
            </span>
          )}
        </h3>
        {approved ? (
          <Badge className="bg-normalBg text-normal normal-case" icon={BadgeCheck}>
            Approved by {approved.by} at {fmtTime(approved.at)}
          </Badge>
        ) : (
          <Badge className="bg-watchBg text-watch normal-case">Drafted by AI, not sent</Badge>
        )}
      </header>
      {edited && !approved && <Badge className="bg-sunken text-text border border-borderStrong" icon={Pencil}>Edited by you</Badge>}
      {children}
      {approved ? (
        <Link to={auditHref} className="inline-flex min-h-11 items-center text-sm font-semibold text-accentText underline">
          View in audit log
        </Link>
      ) : (
        footer
      )}
    </section>
  );
}

interface ApproverRowProps {
  approver: string;
  onApprover: (a: string) => void;
  onApprove: () => void;
  busy: boolean;
  disabled: boolean;
  note?: string;
}

function ApproverRow({ approver, onApprover, onApprove, busy, disabled, note }: ApproverRowProps) {
  const id = useId();
  const { user } = useAuth();
  const isFounder = user?.roleId === "founder";
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        {isFounder ? (
          <>
            <label htmlFor={id} className="text-sm font-medium">
              Approving as
            </label>
            <select id={id} className="input w-auto" value={approver} onChange={(e) => onApprover(e.target.value)}>
              {OFFICERS.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </>
        ) : (
          <p className="m-0 text-sm">
            Approving as <strong>{approver}</strong>
          </p>
        )}
        <Button className="ml-auto" icon={<Send size={16} aria-hidden="true" />} loading={busy} disabled={disabled} onClick={onApprove}>
          Approve action
        </Button>
      </div>
      {note && <p className="m-0 text-sm text-muted">{note}</p>}
    </div>
  );
}

interface TextCardProps {
  action: Exclude<ActionName, "asha_visit_list">;
  draft: string;
  approved: ApprovedState | null;
  approver: string;
  onApprover: (a: string) => void;
  readOnly: boolean;
  busy: boolean;
  auditHref: string;
  onApprove: (action: ActionName, text: string | undefined) => void;
}

const TEXT_META: Record<TextCardProps["action"], { title: string; titleHi?: string; icon: LucideIcon }> = {
  distributor_note: { title: "Note to distributor", titleHi: "वितरक को सूचना", icon: Truck },
  officer_note: { title: "Note for the district office", icon: FileText },
};

export function TextActionCard({ action, draft, approved, approver, onApprover, readOnly, busy, auditHref, onApprove }: TextCardProps) {
  const meta = TEXT_META[action];
  const [text, setText] = useState(draft);
  const ref = useRef<HTMLTextAreaElement>(null);
  const areaId = useId();
  const shown = approved ? approved.text : text;
  const edited = text.trim() !== draft.trim();

  useEffect(() => setText(draft), [draft]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight + 2}px`;
  }, [shown]);

  return (
    <Frame {...meta} approved={approved} edited={edited} auditHref={auditHref}
      footer={
        <>
          {edited && !readOnly && (
            <button type="button" className="mb-2 min-h-9 text-sm font-semibold text-accentText underline" onClick={() => setText(draft)}>
              Reset to draft
            </button>
          )}
          {readOnly ? (
            <p className="m-0 text-sm text-muted">Read-only. Only the health officer approves actions.</p>
          ) : (
            <ApproverRow
              approver={approver}
              onApprover={onApprover}
              busy={busy}
              disabled={text.trim().length === 0}
              onApprove={() => onApprove(action, edited ? text.trim() : undefined)}
            />
          )}
        </>
      }
    >
      <label htmlFor={areaId} className="sr-only">
        {meta.title}
      </label>
      <textarea
        id={areaId}
        ref={ref}
        rows={5}
        value={shown}
        readOnly={Boolean(approved) || readOnly}
        onChange={(e) => setText(e.target.value)}
        className="input min-h-[7.5rem] resize-none py-2 leading-relaxed read-only:bg-sunken"
      />
    </Frame>
  );
}

function priorityLabel(index: number, total: number): { word: string; cls: string } {
  const third = Math.max(1, Math.ceil(total / 3));
  if (index < third) return { word: "High", cls: "bg-alertBg text-alert" };
  if (index < third * 2) return { word: "Medium", cls: "bg-watchBg text-watch" };
  return { word: "Low", cls: "bg-sunken text-text border border-border" };
}

export function visitListText(items: VisitItem[]): string {
  return items.map((v, i) => `${i + 1}. ${v.name} (${v.landmark})`).join("; ");
}

interface VisitCardProps {
  draft: VisitItem[];
  approved: ApprovedState | null;
  approver: string;
  onApprover: (a: string) => void;
  readOnly: boolean;
  busy: boolean;
  auditHref: string;
  onApprove: (action: ActionName, text: string | undefined, visits: VisitItem[]) => void;
}

export function VisitListCard({ draft, approved, approver, onApprover, readOnly, busy, auditHref, onApprove }: VisitCardProps) {
  const [items, setItems] = useState(draft);
  const [announce, setAnnounce] = useState("");
  useEffect(() => setItems(draft), [draft]);

  const sameOrder = items.length === draft.length && items.every((v, i) => v.locality_id === draft[i].locality_id);

  const move = (i: number, dir: -1 | 1): void => {
    const j = i + dir;
    if (j < 0 || j >= items.length) return;
    const next = [...items];
    [next[i], next[j]] = [next[j], next[i]];
    setItems(next);
    setAnnounce(`Moved to position ${j + 1} of ${items.length}`);
  };

  const locked = Boolean(approved) || readOnly;

  return (
    <Frame
      title="ASHA visit list"
      titleHi="आशा दौरा सूची"
      icon={ClipboardList}
      approved={approved}
      edited={!sameOrder}
      auditHref={auditHref}
      footer={
        <>
          {!sameOrder && !readOnly && (
            <button type="button" className="mb-2 min-h-9 text-sm font-semibold text-accentText underline" onClick={() => setItems(draft)}>
              Reset to draft
            </button>
          )}
          {readOnly ? (
            <p className="m-0 text-sm text-muted">Read-only. Only the health officer approves actions.</p>
          ) : (
            <ApproverRow
              approver={approver}
              onApprover={onApprover}
              busy={busy}
              disabled={items.length === 0}
              onApprove={() => onApprove("asha_visit_list", sameOrder ? undefined : visitListText(items), items.map((v, i) => ({ ...v, priority: i + 1 })))}
              note="ASHAs in these pins will see this list on their phones."
            />
          )}
        </>
      }
    >
      {items.length === 0 ? (
        <p className="m-0 text-sm text-muted">The agent did not suggest any localities.</p>
      ) : (
        <ol className="m-0 list-none space-y-2 p-0">
          {items.map((v, i) => {
            const p = priorityLabel(i, items.length);
            return (
              <li key={v.locality_id} className="flex items-start gap-2 rounded-md border border-border bg-bg p-2">
                <span className="mono flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accentSoft text-sm text-accentText" aria-hidden="true">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1 text-sm">
                  <p className="m-0 flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{v.name}</span>
                    <Badge className={p.cls}>{p.word}</Badge>
                  </p>
                  <p className="m-0 text-muted">{v.landmark}</p>
                  {v.reason && <p className="m-0 mt-0.5">{v.reason}</p>}
                </div>
                {!locked && (
                  <div className="flex shrink-0">
                    <button type="button" aria-label={`Move ${v.name} up`} disabled={i === 0} onClick={() => move(i, -1)} className="flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken disabled:opacity-40">
                      <ArrowUp size={16} aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`Move ${v.name} down`} disabled={i === items.length - 1} onClick={() => move(i, 1)} className="flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken disabled:opacity-40">
                      <ArrowDown size={16} aria-hidden="true" />
                    </button>
                    <button type="button" aria-label={`Remove ${v.name} from the list`} onClick={() => setItems(items.filter((x) => x.locality_id !== v.locality_id))} className="flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken">
                      <Trash2 size={16} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
      <p className="sr-only" aria-live="polite">
        {announce}
      </p>
    </Frame>
  );
}
