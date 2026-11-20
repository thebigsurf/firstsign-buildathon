import { TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { ApiError } from "../../api";
import { cx } from "../../lib/format";
import { Button } from "./Button";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cx("skeleton", className)} />;
}

interface ErrorPanelProps {
  error?: ApiError | Error | null;
  message?: string;
  detail?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorPanel({ error, message, detail: detailProp, onRetry, className }: ErrorPanelProps) {
  const detail = detailProp ?? (error && "detail" in error ? (error as ApiError).detail : error?.message);
  const text = message ?? error?.message ?? "Something went wrong.";
  return (
    <div role="alert" className={cx("panel-error", className)}>
      <div className="flex items-start gap-3">
        <TriangleAlert size={20} strokeWidth={1.75} aria-hidden="true" className="mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{text}</p>
          {detail && detail !== text && (
            <details className="mt-1 text-sm">
              <summary className="cursor-pointer">Details</summary>
              <p className="mono mt-1 break-words text-xs">{detail}</p>
            </details>
          )}
          {onRetry && (
            <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
              Try again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  body?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, body, action, className }: EmptyStateProps) {
  return (
    <div className={cx("flex flex-col items-center gap-3 px-6 py-12 text-center", className)}>
      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-sunken text-muted">
        <Icon size={32} strokeWidth={1.75} aria-hidden="true" />
      </span>
      <h2 className="text-h3">{title}</h2>
      {body && <p className="max-w-sm text-muted">{body}</p>}
      {action}
    </div>
  );
}
