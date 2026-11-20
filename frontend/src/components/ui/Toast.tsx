import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { cx } from "../../lib/format";

type ToastKind = "success" | "info" | "error";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
  action?: ToastAction;
}

interface ToastApi {
  show: (kind: ToastKind, message: string, action?: ToastAction) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

const BAR: Record<ToastKind, string> = { success: "bg-normal", info: "bg-accent", error: "bg-alert" };
const ICON = { success: CheckCircle2, info: Info, error: TriangleAlert } as const;

function ToastView({ toast, onClose }: { toast: ToastItem; onClose: () => void }) {
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (toast.kind === "error" || paused) return;
    const id = window.setTimeout(onClose, 5000);
    return () => window.clearTimeout(id);
  }, [toast.kind, paused, onClose]);

  const Icon = ICON[toast.kind];
  return (
    <div
      role={toast.kind === "error" ? "alert" : "status"}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="relative flex max-w-sm gap-3 overflow-hidden rounded-lg border border-border bg-surface p-3 pl-4 pr-12 text-text shadow-2"
    >
      <span aria-hidden="true" className={cx("absolute inset-y-0 left-0 w-1", BAR[toast.kind])} />
      <Icon size={20} strokeWidth={1.75} aria-hidden="true" className="mt-0.5 shrink-0" />
      <div className="text-sm">
        <p>{toast.message}</p>
        {toast.action && (
          <button
            type="button"
            onClick={() => {
              toast.action?.onClick();
              onClose();
            }}
            className="mt-1 font-semibold text-accentText underline"
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        aria-label="Dismiss message"
        onClick={onClose}
        className="absolute right-0 top-0 flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const idRef = useRef(0);

  const close = useCallback((id: number) => setItems((cur) => cur.filter((t) => t.id !== id)), []);
  const show = useCallback((kind: ToastKind, message: string, action?: ToastAction) => {
    idRef.current += 1;
    const id = idRef.current;
    setItems((cur) => [...cur.slice(-3), { id, kind, message, action }]);
  }, []);
  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed inset-x-4 bottom-24 z-50 flex flex-col gap-2 sm:inset-x-auto sm:bottom-4 sm:right-4">
        {items.map((t) => (
          <ToastView key={t.id} toast={t} onClose={() => close(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
