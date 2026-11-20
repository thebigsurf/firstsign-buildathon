import { forwardRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { cx, daysSince, fmtShortDate, plural } from "../../lib/format";
import { useRefData } from "../../lib/refdata";
import type { Alert } from "../../types";
import { AlertStatusChip, LevelBadge, PinChip } from "../ui/Badge";
import { buttonClass } from "../ui/Button";
import { ConfidenceMeter } from "../ui/ConfidenceMeter";

export function alertTitle(alert: Alert, groupLabel: (id: string) => string, areaOf: (pin: string) => string): string {
  const label = alert.group_label || groupLabel(alert.group);
  return `${label}: ${alert.pins.map(areaOf).join(", ")}`;
}

interface Props {
  alert: Alert;
  selected: boolean;
  asOf?: string;
  onHover: (alertId: string | null) => void;
}

export const AlertCard = forwardRef<HTMLLIElement, Props>(function AlertCard({ alert, selected, asOf, onHover }, ref) {
  const { groupLabel, areaOf } = useRefData();
  const navigate = useNavigate();
  const href = `/officer/alert/${encodeURIComponent(alert.alert_id)}`;
  const days = daysSince(alert.started, asOf);

  return (
    <li
      ref={ref}
      onMouseEnter={() => onHover(alert.alert_id)}
      onMouseLeave={() => onHover(null)}
      onFocusCapture={() => onHover(alert.alert_id)}
      onBlurCapture={() => onHover(null)}
      onClick={(e) => {
        if (!(e.target as HTMLElement).closest("a,button")) navigate(href);
      }}
      className={cx("card-link cursor-pointer space-y-3", selected && "border-accent shadow-2 ring-2 ring-accent")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-h3">{alertTitle(alert, groupLabel, areaOf)}</h3>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {alert.pins.map((p) => (
              <PinChip key={p} pin={p} />
            ))}
          </div>
        </div>
        <LevelBadge level={alert.level} />
      </div>
      <p className="m-0 text-sm">
        <span className="mono text-lg font-semibold">{alert.ratio.toFixed(1)}x</span> normal.{" "}
        <span className="text-muted">About {Math.round(alert.breadth * 100)}% of chemists in these pin codes are ordering above normal.</span>
      </p>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <ConfidenceMeter value={alert.confidence} label={`Confidence for ${alertTitle(alert, groupLabel, areaOf)}`} width="w-[120px]" />
        <span className="text-sm text-muted">ASHA reports: <span className="mono">{alert.asha_reports}</span></span>
        <AlertStatusChip status={alert.status} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="m-0 text-sm text-muted">
          Rising since {fmtShortDate(alert.started)} ({plural(days, "day")})
        </p>
        <Link to={href} className={buttonClass("secondary", "sm")} aria-label={`Open alert: ${alertTitle(alert, groupLabel, areaOf)}`}>
          Open alert
        </Link>
      </div>
    </li>
  );
});
