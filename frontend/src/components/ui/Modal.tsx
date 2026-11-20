import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { cx } from "../../lib/format";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** "sheet" always sits at the bottom; "dialog" is a bottom sheet on phones and centred on larger screens. */
  variant?: "dialog" | "sheet" | "drawer";
  titleLang?: string;
  width?: string;
}

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

/** Accessible modal: focus trap, Escape to close, focus returns to the trigger, background made inert. */
export function Modal({ open, title, onClose, children, variant = "dialog", titleLang, width = "max-w-lg" }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const returnRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    returnRef.current = document.activeElement as HTMLElement | null;
    const root = document.getElementById("root");
    root?.setAttribute("inert", "");
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      root?.removeAttribute("inert");
      returnRef.current?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  const position =
    variant === "drawer"
      ? "inset-y-0 right-0 w-full sm:max-w-2xl rounded-none sm:rounded-l-xl"
      : variant === "sheet"
        ? "inset-x-0 bottom-0 max-h-[85dvh] rounded-t-xl"
        : cx("inset-x-0 bottom-0 max-h-[85dvh] rounded-t-xl sm:inset-auto sm:left-1/2 sm:top-1/2 sm:w-[calc(100%-2rem)] sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-xl", width);

  return createPortal(
    <div className="fixed inset-0 z-[2000]">
      <div className="absolute inset-0" style={{ background: "var(--scrim)" }} onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cx("absolute overflow-auto bg-surface p-5 text-text shadow-3 sm:p-6", position)}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-h2" lang={titleLang}>
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
