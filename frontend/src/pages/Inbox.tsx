import { MessageSquareDashed } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { MessageList, type ListMessage, type StatusFilter } from "../components/inbox/MessageList";
import { NewMessageModal, type NewMessage } from "../components/inbox/NewMessageModal";
import { OrderWorkspace, type WorkspaceMessage } from "../components/inbox/OrderWorkspace";
import { EmptyState, Skeleton } from "../components/ui/States";
import { useToast } from "../components/ui/Toast";
import { readStored, writeStored } from "../lib/format";
import { toApiError, useAsync, useDocumentTitle, useMediaQuery } from "../lib/hooks";
import {
  addedLine,
  editableFromRecord,
  needsCheck,
  toEditable,
  type EditableLine,
  type Work,
} from "../lib/order";
import type { CatalogueItem, InboxMessage, MessageType } from "../types";

interface LocalMessage {
  id: string;
  chemist_id: string;
  received_at: string;
  type: MessageType;
  text?: string;
  blob?: Blob;
  fileName?: string;
  blobUrl?: string;
}

const APPROVERS = ["Rohan (clerk)", "Sneha (clerk)"];
const APPROVER_KEY = "fs-approver";

function emptyWork(): Work {
  return { phase: "parsing", parsed: null, lines: [], dismissedNA: [], error: null, startedAt: Date.now() };
}

export function Inbox() {
  useDocumentTitle("Inbox");
  const toast = useToast();
  const navigate = useNavigate();
  const wide = useMediaQuery("(min-width: 1024px)");
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("msg");

  const inbox = useAsync((s) => api.inbox(s), []);
  const orders = useAsync((s) => api.orders(s), []);

  const [local, setLocal] = useState<LocalMessage[]>([]);
  const [work, setWork] = useState<Record<string, Work>>({});
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [newOpen, setNewOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approver, setApproverState] = useState(() => {
    const saved = readStored(APPROVER_KEY);
    return saved && APPROVERS.includes(saved) ? saved : APPROVERS[0];
  });
  const started = useRef(new Set<string>());
  const focusFirstAfter = useRef(false);

  const setApprover = (a: string): void => {
    setApproverState(a);
    writeStored(APPROVER_KEY, a);
  };

  const patchWork = useCallback((id: string, fn: (w: Work) => Work) => {
    setWork((cur) => ({ ...cur, [id]: fn(cur[id] ?? emptyWork()) }));
  }, []);

  const serverMessages: InboxMessage[] = useMemo(
    () => [...(inbox.data ?? [])].sort((a, b) => b.received_at.localeCompare(a.received_at)),
    [inbox.data],
  );

  const messages = useMemo<ListMessage[]>(() => {
    const statusOf = (id: string, serverStatus: ListMessage["status"]): ListMessage["status"] => {
      const w = work[id];
      if (w?.phase === "approved" || serverStatus === "approved") return "approved";
      if (w?.phase === "ready" || serverStatus === "parsed") return "parsed";
      return "new";
    };
    const flagsOf = (id: string, serverMsg?: InboxMessage): boolean => {
      const w = work[id];
      if (w) return w.lines.some(needsCheck);
      return Boolean(serverMsg?.parsed?.lines.some((l) => l.status !== "matched"));
    };
    const localRows: ListMessage[] = [...local].reverse().map((m) => ({
      id: m.id,
      chemist_id: m.chemist_id,
      received_at: m.received_at,
      type: m.type,
      text: m.text,
      status: statusOf(m.id, "new"),
      hasFlags: flagsOf(m.id),
      local: true,
    }));
    const serverRows: ListMessage[] = serverMessages.map((m) => ({
      id: m.id,
      chemist_id: m.chemist_id,
      received_at: m.received_at,
      type: m.type,
      text: m.text,
      status: statusOf(m.id, m.status),
      hasFlags: flagsOf(m.id, m),
      local: false,
    }));
    return [...localRows, ...serverRows];
  }, [local, serverMessages, work]);

  const select = useCallback(
    (id: string | null, replace = false) => {
      setParams(
        (cur) => {
          const next = new URLSearchParams(cur);
          if (id) next.set("msg", id);
          else next.delete("msg");
          return next;
        },
        { replace },
      );
    },
    [setParams],
  );

  // On wide screens always show something: the first message that still needs work.
  useEffect(() => {
    if (!wide || selectedId || messages.length === 0) return;
    select((messages.find((m) => m.status === "new") ?? messages[0]).id, true);
  }, [wide, selectedId, messages, select]);

  const runParse = useCallback(
    async (id: string) => {
      const localMsg = local.find((m) => m.id === id);
      const server = serverMessages.find((m) => m.id === id);
      const chemistId = localMsg?.chemist_id ?? server?.chemist_id;
      if (!chemistId) return;
      setWork((cur) => ({ ...cur, [id]: emptyWork() }));
      try {
        const parsed = await api.parseOrder({
          chemistId,
          messageId: localMsg ? null : id,
          file: localMsg?.blob,
          fileName: localMsg?.fileName,
          text: localMsg?.type === "text" ? localMsg.text : undefined,
        });
        patchWork(id, (w) => ({ ...w, phase: "ready", parsed, lines: toEditable(parsed), error: null }));
      } catch (err) {
        const e = toApiError(err);
        patchWork(id, (w) => ({ ...w, phase: "error", error: { message: e.message, detail: e.detail } }));
      }
    },
    [local, serverMessages, patchWork],
  );

  // Make sure the selected message has a workspace: reuse what the server holds, or read it now.
  useEffect(() => {
    if (!selectedId || started.current.has(selectedId)) return;
    const localMsg = local.find((m) => m.id === selectedId);
    if (localMsg) {
      started.current.add(selectedId);
      void runParse(selectedId);
      return;
    }
    const server = serverMessages.find((m) => m.id === selectedId);
    if (!server) return;
    if (server.status === "approved") {
      if (!orders.data) return;
      const order = orders.data.find((o) => o.message_id === server.id);
      started.current.add(selectedId);
      setWork((cur) => ({
        ...cur,
        [selectedId]: {
          phase: "approved",
          parsed: server.parsed ?? null,
          lines: order ? editableFromRecord(order.lines) : server.parsed ? toEditable(server.parsed) : [],
          dismissedNA: [],
          error: null,
          startedAt: Date.now(),
          approvedBy: order?.approved_by,
          approvedAt: order?.created_at,
        },
      }));
      return;
    }
    started.current.add(selectedId);
    if (server.status === "parsed" && server.parsed) {
      const parsed = server.parsed;
      setWork((cur) => ({
        ...cur,
        [selectedId]: { phase: "ready", parsed, lines: toEditable(parsed), dismissedNA: [], error: null, startedAt: Date.now() },
      }));
    } else {
      void runParse(selectedId);
    }
  }, [selectedId, local, serverMessages, orders.data, runParse]);

  const onNewMessage = (m: NewMessage): void => {
    const id = `local-${Date.now().toString(36)}`;
    const blobUrl = m.blob ? URL.createObjectURL(m.blob) : undefined;
    setLocal((cur) => [
      ...cur,
      { id, chemist_id: m.chemistId, received_at: new Date().toISOString(), type: m.type, text: m.text, blob: m.blob, fileName: m.fileName, blobUrl },
    ]);
    select(id);
  };

  useEffect(
    () => () => {
      // Local uploads live only for this visit; release the object URLs when leaving.
      local.forEach((m) => m.blobUrl && URL.revokeObjectURL(m.blobUrl));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const selectedLocal = local.find((m) => m.id === selectedId);
  const selectedServer = serverMessages.find((m) => m.id === selectedId);
  const selectedWork = selectedId ? work[selectedId] : undefined;

  const workspaceMessage: WorkspaceMessage | null = selectedLocal
    ? {
        id: selectedLocal.id,
        chemist_id: selectedLocal.chemist_id,
        received_at: selectedLocal.received_at,
        type: selectedLocal.type,
        text: selectedLocal.text,
        mediaUrl: selectedLocal.blobUrl ?? null,
        local: true,
      }
    : selectedServer
      ? {
          id: selectedServer.id,
          chemist_id: selectedServer.chemist_id,
          received_at: selectedServer.received_at,
          type: selectedServer.type,
          text: selectedServer.text,
          mediaUrl: api.mediaUrl(selectedServer),
          local: false,
        }
      : null;

  const updateLine = (fn: (l: EditableLine) => EditableLine, key: string): void => {
    if (!selectedId) return;
    patchWork(selectedId, (w) => ({ ...w, lines: w.lines.map((l) => (l.key === key ? fn(l) : l)) }));
  };

  const addLine = (item: CatalogueItem): void => {
    if (!selectedId) return;
    patchWork(selectedId, (w) => ({ ...w, lines: [...w.lines, addedLine(item)] }));
  };

  const goToNext = (fromId: string): void => {
    const next = messages.find((m) => m.id !== fromId && m.status === "new");
    if (next) {
      focusFirstAfter.current = true;
      select(next.id);
    }
  };

  const approve = async (): Promise<void> => {
    if (!selectedId || !selectedWork || !workspaceMessage) return;
    const final = selectedWork.lines.filter((l) => l.resolution !== "removed" && l.resolution !== "not_available");
    setApproving(true);
    try {
      await api.saveOrder({
        chemist_id: workspaceMessage.chemist_id,
        message_id: workspaceMessage.local ? null : workspaceMessage.id,
        lines: final.map((l) => l.line),
        approved_by: approver,
        original_lines: selectedWork.parsed?.lines,
      });
      patchWork(selectedId, (w) => ({
        ...w,
        phase: "approved",
        lines: editableFromRecord(final.map((l) => l.line)),
        approvedBy: approver,
        approvedAt: new Date().toISOString(),
      }));
      toast.show("success", `Order saved. Logged as approved by ${approver}.`, {
        label: "View in audit log",
        onClick: () => {
          const q = new URLSearchParams(window.location.search);
          q.set("view", "audit");
          navigate({ search: q.toString() });
        },
      });
      orders.reload();
      inbox.reload();
      goToNext(selectedId);
    } catch (err) {
      const e = toApiError(err);
      toast.show("error", e instanceof ApiError && e.status === 409 ? "This message already has an approved order." : `Could not save the order. ${e.message}`);
    } finally {
      setApproving(false);
    }
  };

  // After approving, move keyboard focus to the first line that needs attention in the next message.
  useEffect(() => {
    if (!focusFirstAfter.current || selectedWork?.phase !== "ready") return;
    focusFirstAfter.current = false;
    const el = document.querySelector<HTMLElement>("[data-first-control]");
    el?.focus({ preventScroll: false });
  }, [selectedId, selectedWork?.phase]);

  const showList = wide || !selectedId;
  const showDetail = wide || Boolean(selectedId);

  return (
    <div className="mx-auto max-w-[1440px] lg:grid lg:h-[calc(100dvh-var(--shell-h))] lg:grid-cols-[340px_minmax(0,1fr)]">
      {showList && (
        <div className="min-h-[60dvh] border-border lg:h-full lg:min-h-0 lg:border-r">
          <h1 className="sr-only">Inbox</h1>
          <MessageList
            messages={messages}
            loading={inbox.loading}
            error={inbox.error}
            onRetry={inbox.reload}
            selectedId={selectedId}
            onSelect={(id) => select(id)}
            filter={filter}
            onFilter={setFilter}
            onNew={() => setNewOpen(true)}
          />
        </div>
      )}
      {showDetail && (
        <section aria-label="Parsed order" aria-busy={selectedWork?.phase === "parsing"} className="min-h-0 bg-bg lg:h-full">
          {workspaceMessage && selectedWork ? (
            <OrderWorkspace
              message={workspaceMessage}
              work={selectedWork}
              approvers={APPROVERS}
              approver={approver}
              onApprover={setApprover}
              approving={approving}
              onUpdateLine={(key, fn) => updateLine(fn, key)}
              onAddLine={addLine}
              onRestore={(key) => updateLine((l) => ({ ...l, resolution: "none" }), key)}
              onDismissNA={(t) => selectedId && patchWork(selectedId, (w) => ({ ...w, dismissedNA: [...w.dismissedNA, t] }))}
              onReread={() => selectedId && void runParse(selectedId)}
              onManual={() =>
                selectedId && patchWork(selectedId, (w) => ({ ...w, phase: "ready", lines: [], parsed: w.parsed, error: null }))
              }
              onSkip={() => {
                const next = messages.find((m) => m.id !== selectedId && m.status === "new");
                if (next) select(next.id);
                else if (!wide) select(null);
              }}
              onApprove={() => void approve()}
              onBack={wide ? undefined : () => select(null)}
            />
          ) : selectedId && !selectedServer && !selectedLocal && !inbox.loading ? (
            <EmptyState icon={MessageSquareDashed} title="We could not find that message" body="Pick one from the list." />
          ) : selectedId ? (
            <div aria-busy="true" className="space-y-3 p-5">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <EmptyState icon={MessageSquareDashed} title="Pick a message" body="Choose a message on the left to see the order we read from it." />
          )}
        </section>
      )}
      <NewMessageModal open={newOpen} onClose={() => setNewOpen(false)} onCreate={onNewMessage} />
    </div>
  );
}
