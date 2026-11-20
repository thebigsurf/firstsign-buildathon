import {
  BadgeCheck,
  Check,
  CheckCircle2,
  CircleHelp,
  Eye,
  OctagonX,
  Pencil,
  TriangleAlert,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { cx } from "../../lib/format";
import type { AlertStatus, Level, LineStatus, MessageStatus } from "../../types";

interface BadgeProps {
  className: string;
  icon?: LucideIcon;
  children: ReactNode;
  size?: number;
  lang?: string;
}

export function Badge({ className, icon: Icon, children, size = 14, lang }: BadgeProps) {
  return (
    <span className={cx("badge", className)} lang={lang}>
      {Icon && <Icon size={size} strokeWidth={1.75} aria-hidden="true" />}
      {children}
    </span>
  );
}

const LEVEL: Record<Level, { cls: string; icon: LucideIcon; en: string; hi: string }> = {
  normal: { cls: "bg-normalBg text-normal", icon: CheckCircle2, en: "Normal", hi: "सामान्य" },
  watch: { cls: "bg-watchBg text-watch", icon: Eye, en: "Watch", hi: "निगरानी" },
  alert: { cls: "bg-alertBg text-alert", icon: TriangleAlert, en: "Alert", hi: "चेतावनी" },
};

export function levelWord(level: Level): string {
  return LEVEL[level].en;
}

export function LevelBadge({ level, showHindi = false }: { level: Level; showHindi?: boolean }) {
  const m = LEVEL[level];
  return (
    <Badge className={m.cls} icon={m.icon}>
      {m.en}
      {showHindi && (
        <span lang="hi" className="normal-case font-medium">
          {m.hi}
        </span>
      )}
    </Badge>
  );
}

const LINE: Record<LineStatus, { cls: string; icon: LucideIcon; en: string; hi: string }> = {
  matched: { cls: "bg-confHighBg text-confHigh", icon: Check, en: "Matched", hi: "मिलान" },
  uncertain: { cls: "bg-confUncBg text-confUnc", icon: CircleHelp, en: "Check this", hi: "जाँचें" },
  unknown: { cls: "bg-confUnkBg text-confUnk", icon: OctagonX, en: "Not found", hi: "नहीं मिला" },
};

export function LineStatusBadge({ status, confirmed = false }: { status: LineStatus; confirmed?: boolean }) {
  const m = LINE[status];
  if (confirmed) {
    return (
      <Badge className="bg-confHighBg text-confHigh" icon={UserCheck}>
        Matched, clerk confirmed
      </Badge>
    );
  }
  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <Badge className={m.cls} icon={m.icon}>
        {m.en}
      </Badge>
      <span lang="hi" className="text-sm text-muted">
        {m.hi}
      </span>
    </span>
  );
}

export function MessageStatusPill({ status, hasFlags }: { status: MessageStatus; hasFlags?: boolean }) {
  if (status === "approved") {
    return (
      <Badge className="bg-normalBg text-normal" icon={BadgeCheck}>
        Approved
      </Badge>
    );
  }
  if (status === "parsed") {
    return hasFlags ? (
      <Badge className="bg-watchBg text-watch" icon={CircleHelp}>
        Check
      </Badge>
    ) : (
      <Badge className="bg-normalBg text-normal" icon={Check}>
        Parsed
      </Badge>
    );
  }
  return <Badge className="border border-accent text-accentText">New</Badge>;
}

const ALERT_STATUS: Record<AlertStatus, string> = {
  open: "border border-borderStrong text-text",
  confirmed: "bg-normalBg text-normal",
  dismissed: "bg-sunken text-muted border border-border",
};

export function AlertStatusChip({ status }: { status: AlertStatus }) {
  const label = status === "open" ? "Open" : status === "confirmed" ? "Confirmed" : "Dismissed";
  return (
    <Badge className={ALERT_STATUS[status]} icon={status === "confirmed" ? BadgeCheck : undefined}>
      {label}
    </Badge>
  );
}

export function EditedTag() {
  return (
    <Badge className="bg-sunken text-text border border-borderStrong" icon={Pencil}>
      Edited
    </Badge>
  );
}

export function GroupChip({ label, labelHi, color }: { label: string; labelHi?: string; color?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-sunken px-2.5 py-0.5 text-sm text-text">
      <span
        aria-hidden="true"
        className="inline-block h-2.5 w-2.5 rounded-full border border-borderStrong"
        style={{ background: color || "var(--muted)" }}
      />
      {label}
      {labelHi && (
        <span lang="hi" className="text-muted">
          {labelHi}
        </span>
      )}
    </span>
  );
}

export function PinChip({ pin }: { pin: string }) {
  return <span className="mono rounded-md bg-sunken px-1.5 py-0.5 text-sm">{pin}</span>;
}
