import { FlaskConical, Info, Keyboard, LogOut, Map as MapIcon, Moon, PackageCheck, Mic, Store, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { initials, WORKSPACE_HOME, WORKSPACE_LABEL, workspaceOfPath, type DemoUser, type Workspace } from "../lib/auth";
import { useAuth, useUser } from "../lib/AuthContext";
import { cx } from "../lib/format";
import { useTheme } from "../lib/theme";
import { AuditLog } from "./AuditLog";
import { Logo } from "./ui/Pulse";
import { Modal } from "./ui/Modal";

type Role = "chemist" | "distributor" | "officer" | "asha" | "none";

function roleOf(path: string): Role {
  if (path.startsWith("/chemist")) return "chemist";
  if (path.startsWith("/distributor")) return "distributor";
  if (path.startsWith("/officer")) return "officer";
  if (path.startsWith("/asha")) return "asha";
  return "none";
}

const ROLES = [
  { to: "/chemist", role: "chemist", en: "Chemist", hi: "केमिस्ट", short: "Chemist", icon: Store },
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

function UserMenu({ user, onHelp }: { user: DemoUser; onHelp: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent): void => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const item = "flex min-h-11 w-full items-center gap-2 rounded-md px-3 text-left text-sm hover:bg-sunken";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu, ${user.name}`}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accentFg" aria-hidden="true">
          {initials(user.name)}
        </span>
      </button>
      {open && (
        <div role="menu" aria-label="Account" className="absolute right-0 top-12 z-50 w-64 rounded-lg border border-border bg-surface p-2 shadow-2">
          <div className="border-b border-border px-3 pb-2 pt-1">
            <p className="m-0 font-semibold">{user.name}</p>
            <p className="m-0 text-sm text-muted">{user.roleLabel}</p>
            <p className="m-0 text-xs text-muted">{user.org}</p>
          </div>
          <div className="pt-1">
            <Link to="/about" role="menuitem" className={item}>
              <Info size={18} strokeWidth={1.75} aria-hidden="true" /> About FirstSign
            </Link>
            <button type="button" role="menuitem" className={cx(item, "hidden md:flex")} onClick={() => { setOpen(false); onHelp(); }}>
              <Keyboard size={18} strokeWidth={1.75} aria-hidden="true" /> Keyboard shortcuts
            </button>
            <button
              type="button"
              role="menuitem"
              className={item}
              onClick={() => {
                setOpen(false);
                signOut();
                navigate("/login", { replace: true });
              }}
            >
              <LogOut size={18} strokeWidth={1.75} aria-hidden="true" /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Shell() {
  const { pathname } = useLocation();
  const user = useUser();
  const navigate = useNavigate();
  const role = roleOf(pathname);
  const ws = workspaceOfPath(pathname);
  const isFounder = user.roleId === "founder";
  const wsLabel = ws ? `${WORKSPACE_LABEL[ws]} workspace` : "FirstSign";
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
    <div style={{ ["--shell-h" as string]: subnav ? "100px" : "56px" }} className="min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[3000] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-accentFg"
      >
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-2 px-3 sm:gap-3 sm:px-4 md:px-6 xl:px-8">
          <Logo />
          <div className="ml-1 hidden min-w-0 border-l border-border pl-3 leading-tight lg:block">
            <p className="m-0 truncate text-sm font-medium">{user.org}</p>
            <p className="m-0 truncate text-xs text-muted">{wsLabel}</p>
          </div>
          {isFounder && (
            <label className="ml-2 hidden items-center gap-2 text-sm text-muted md:flex">
              <span>Workspace</span>
              <select
                aria-label="Switch workspace"
                className="input min-h-9 w-auto py-0 text-text"
                value={ws ?? ""}
                onChange={(e) => navigate(WORKSPACE_HOME[e.target.value as Workspace])}
              >
                {ws === null && <option value="">Choose...</option>}
                {user.workspaces.map((w) => (
                  <option key={w} value={w}>
                    {WORKSPACE_LABEL[w]}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <div
              role="region"
              aria-label="Simulated data notice"
              title="Sandbox workspace: all orders, chemists, ASHA workers and the 90-day history are simulated. No real patients or people. यह डेमो डेटा है, असली नहीं।"
              className="inline-flex min-h-7 items-center gap-1.5 whitespace-nowrap rounded-full border border-watch bg-watchBg px-2.5 text-xs font-medium text-watch"
            >
              <FlaskConical size={14} strokeWidth={1.75} aria-hidden="true" className="shrink-0" />
              <span className="whitespace-nowrap sm:hidden">
                {isAsha ? <span lang="hi">डेमो डेटा</span> : "Simulated data"}
              </span>
              <span className="hidden sm:inline">
                Sandbox workspace &middot; simulated data
                <span lang="hi" className="ml-1.5 hidden xl:inline">/ डेमो डेटा</span>
              </span>
            </div>
            <button
              type="button"
              onClick={toggle}
              aria-label="Switch theme"
              aria-pressed={theme === "dark"}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
            >
              {theme === "dark" ? <Sun size={20} strokeWidth={1.75} aria-hidden="true" /> : <Moon size={20} strokeWidth={1.75} aria-hidden="true" />}
            </button>
            <UserMenu user={user} onHelp={() => setHelp(true)} />
          </div>
        </div>
      </header>

      <SubNav role={role} />

      <main id="main" tabIndex={-1} className={cx("outline-none", isFounder && !isAsha && "pb-16 md:pb-0")}>
        <Outlet />
      </main>

      {isFounder && !isAsha && (
        <nav aria-label="Choose your workspace (mobile)" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface md:hidden">
          <ul className="m-0 grid h-16 list-none grid-cols-4 p-0">
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
