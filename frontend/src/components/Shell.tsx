import { CircleHelp, FlaskConical, Map as MapIcon, Moon, PackageCheck, Mic, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useSearchParams } from "react-router-dom";
import { cx } from "../lib/format";
import { useTheme } from "../lib/theme";
import { AuditLog } from "./AuditLog";
import { IconButton } from "./ui/Button";
import { Logo } from "./ui/Pulse";
import { Modal } from "./ui/Modal";

type Role = "distributor" | "officer" | "asha" | "none";

function roleOf(path: string): Role {
  if (path.startsWith("/distributor")) return "distributor";
  if (path.startsWith("/officer")) return "officer";
  if (path.startsWith("/asha")) return "asha";
  return "none";
}

const ROLES = [
  { to: "/distributor/inbox", role: "distributor", en: "Distributor", hi: "वितरक", short: "Dist.", icon: PackageCheck },
  { to: "/officer", role: "officer", en: "Health officer", hi: "स्वास्थ्य अधिकारी", short: "Officer", icon: MapIcon },
  { to: "/asha", role: "asha", en: "ASHA", hi: "आशा", short: "ASHA", icon: Mic },
] as const;

function SubTab({ to, children, match }: { to: string; children: React.ReactNode; match: boolean }) {
  return (
    <Link
      to={to}
      aria-current={match ? "page" : undefined}
      className={cx(
        "inline-flex min-h-11 items-center whitespace-nowrap border-b-[3px] px-3 text-sm font-medium",
        match ? "border-accent text-text" : "border-transparent text-muted hover:text-text",
      )}
    >
      {children}
    </Link>
  );
}

function SubNav({ role }: { role: Role }) {
  const { pathname, search } = useLocation();
  const audit = new URLSearchParams(search).get("view") === "audit";
  if (role !== "distributor" && role !== "officer") return null;
  const auditTo = `${pathname}?view=audit`;
  return (
    <nav aria-label="Section" className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-[1440px] gap-1 overflow-x-auto px-4 md:px-6 xl:px-8">
        {role === "distributor" ? (
          <>
            <SubTab to="/distributor/inbox" match={pathname === "/distributor/inbox" && !audit}>
              Inbox <span lang="hi" className="ml-1.5 text-muted">इनबॉक्स</span>
            </SubTab>
            <SubTab to="/distributor/radar" match={pathname === "/distributor/radar"}>
              Stock radar <span lang="hi" className="ml-1.5 text-muted">स्टॉक रडार</span>
            </SubTab>
          </>
        ) : (
          <SubTab to="/officer" match={pathname === "/officer" && !audit}>
            Map and alerts
          </SubTab>
        )}
        <SubTab to={auditTo} match={audit}>
          Audit log <span lang="hi" className="ml-1.5 text-muted">ऑडिट</span>
        </SubTab>
      </div>
    </nav>
  );
}

function KeyboardHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  const rows: Array<[string, string]> = [
    ["Tab / Shift+Tab", "Move between controls"],
    ["Arrow Down / Arrow Up", "Next or previous message in the inbox list"],
    ["Enter", "Open the focused message, or jump to its first line that needs a check"],
    ["Escape", "Close a menu, dialog or photo zoom"],
    ["Space or Enter on the round button", "Start or stop a recording"],
    ["?", "Open this help"],
  ];
  return (
    <Modal open={open} onClose={onClose} title="Keyboard help">
      <dl className="space-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[auto_1fr] gap-4">
            <dt className="mono rounded bg-sunken px-2 py-0.5 text-xs">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-sm text-muted">There is no one-key shortcut that approves anything. Approving always needs a click or Enter on the Approve button.</p>
    </Modal>
  );
}

export function Shell() {
  const { pathname } = useLocation();
  const role = roleOf(pathname);
  const [params, setParams] = useSearchParams();
  const { theme, toggle } = useTheme();
  const [help, setHelp] = useState(false);
  const auditOpen = params.get("view") === "audit";
  const isAsha = role === "asha";
  const subnav = role === "distributor" || role === "officer";

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      const t = e.target as HTMLElement | null;
      const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if (e.key === "?" && !typing) setHelp(true);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [pathname]);

  const closeAudit = (): void => {
    const next = new URLSearchParams(params);
    next.delete("view");
    setParams(next, { replace: true });
  };

  return (
    <div style={{ ["--shell-h" as string]: subnav ? "132px" : "88px" }} className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[3000] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-accentFg"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-2 px-3 sm:gap-3 sm:px-4 md:px-6 xl:px-8">
          <Logo />
          <nav aria-label="Choose your role" className="mx-auto hidden md:block">
            <ul className="m-0 inline-flex list-none gap-1 rounded-lg bg-sunken p-1">
              {ROLES.map((r) => (
                <li key={r.role}>
                  <NavLink
                    to={r.to}
                    aria-current={role === r.role ? "page" : undefined}
                    className={cx(
                      "inline-flex min-h-9 items-center gap-1.5 rounded-md border-b-2 px-3 text-sm font-medium",
                      role === r.role ? "border-accent bg-surface text-text shadow-1" : "border-transparent text-muted hover:text-text",
                    )}
                  >
                    {r.en}
                    <span lang="hi" className="text-muted">{r.hi}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="ml-auto flex items-center gap-0 sm:gap-1 md:ml-0">
            {isAsha && (
              <Link to="/" className="inline-flex min-h-14 items-center whitespace-nowrap px-1 text-sm font-medium text-accentText underline md:hidden">
                Change role
              </Link>
            )}
            <IconButton label="Keyboard help" onClick={() => setHelp(true)} className="hidden md:inline-flex">
              <CircleHelp size={20} strokeWidth={1.75} aria-hidden="true" />
            </IconButton>
            <IconButton label="Switch theme" onClick={toggle} aria-pressed={theme === "dark"} className={isAsha ? "min-h-14 min-w-14" : undefined}>
              {theme === "dark" ? <Sun size={20} strokeWidth={1.75} aria-hidden="true" /> : <Moon size={20} strokeWidth={1.75} aria-hidden="true" />}
            </IconButton>
            <Link to="/about" className={cx("inline-flex items-center rounded-lg text-sm font-medium hover:bg-sunken", isAsha ? "min-h-14 px-1.5" : "min-h-11 px-3")}>
              About
            </Link>
          </div>
        </div>
      </header>

      <div role="region" aria-label="Simulated data notice" className="sticky top-14 z-40 border-b border-watch bg-watchBg text-watch">
        <div className="mx-auto flex max-w-[1440px] items-center gap-2 px-4 py-1.5 text-sm md:px-6 xl:px-8">
          <FlaskConical size={16} strokeWidth={1.75} aria-hidden="true" className="shrink-0" />
          {isAsha ? (
            <p className="m-0 font-medium">
              Simulated demo data <span lang="hi">/ डेमो डेटा</span>
            </p>
          ) : (
            <p className="m-0">
              <strong>Simulated demo data.</strong> Chemist orders and 90-day history are simulated, no real patients or people.{" "}
              <span lang="hi" className="hidden lg:inline">यह डेमो डेटा है, असली नहीं।</span>
            </p>
          )}
        </div>
      </div>

      <SubNav role={role} />

      <main id="main" tabIndex={-1} className={cx("outline-none", !isAsha && "pb-16 md:pb-0")}>
        <Outlet />
      </main>

      {!isAsha && (
        <nav aria-label="Choose your role (mobile)" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface md:hidden">
          <ul className="m-0 grid h-16 list-none grid-cols-3 p-0">
            {ROLES.map((r) => {
              const Icon = r.icon;
              const current = role === r.role;
              return (
                <li key={r.role} className="contents">
                  <NavLink
                    to={r.to}
                    aria-current={current ? "page" : undefined}
                    className={cx(
                      "flex flex-col items-center justify-center gap-0.5 border-t-[3px] text-xs font-medium",
                      current ? "border-accent text-accentText" : "border-transparent text-muted",
                    )}
                  >
                    <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
                    {r.short}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>
      )}

      <Modal open={auditOpen} onClose={closeAudit} title="Audit log" variant="drawer">
        <p lang="hi" className="-mt-3 mb-3 text-muted">ऑडिट लॉग</p>
        <AuditLog />
      </Modal>
      <KeyboardHelp open={help} onClose={() => setHelp(false)} />
    </div>
  );
}
