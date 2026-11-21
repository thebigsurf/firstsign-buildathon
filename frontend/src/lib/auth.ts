/**
 * Demo sign-in gate for the FirstSign sandbox.
 *
 * IMPORTANT: this is NOT real authentication. The accounts below are a fixed,
 * fictional, client-side list and the passwords are shown on the login page on
 * purpose. It exists so the sandbox feels like the real tool (workspaces per
 * role, a signed-in user, a sign-out) without any backend identity system.
 * Do not reuse this pattern to protect real data.
 */

export type RoleId = "clerk" | "owner" | "officer" | "asha" | "chemist" | "founder";
export type Workspace = "distributor" | "officer" | "asha" | "chemist";

export interface DemoUser {
  email: string;
  password: string;
  name: string;
  roleId: RoleId;
  roleLabel: string;
  org: string;
  /** Route to land on after sign-in. */
  home: string;
  /** Workspaces this user may open. */
  workspaces: Workspace[];
  /** Name written to the audit log when this user approves something. */
  approverLabel: string;
  ashaId?: string;
  chemistId?: string;
}

export const DEMO_PASSWORD = "firstsign";

export const ACCOUNTS: DemoUser[] = [
  {
    email: "clerk@saikrupa.demo",
    password: DEMO_PASSWORD,
    name: "Rohan",
    roleId: "clerk",
    roleLabel: "Order desk clerk",
    org: "Sai Krupa Pharma (distributor)",
    home: "/distributor/inbox",
    workspaces: ["distributor"],
    approverLabel: "Rohan (clerk)",
  },
  {
    email: "owner@saikrupa.demo",
    password: DEMO_PASSWORD,
    name: "Vikram",
    roleId: "owner",
    roleLabel: "Distributor owner",
    org: "Sai Krupa Pharma (distributor)",
    home: "/distributor/radar",
    workspaces: ["distributor"],
    approverLabel: "Vikram (owner)",
  },
  {
    email: "officer@wardhealth.demo",
    password: DEMO_PASSWORD,
    name: "Dr. Meera",
    roleId: "officer",
    roleLabel: "Ward health officer",
    org: "Ward health office (sandbox)",
    home: "/officer",
    workspaces: ["officer"],
    approverLabel: "Dr. Meera (district officer)",
  },
  {
    email: "sunita@asha.demo",
    password: DEMO_PASSWORD,
    name: "Sunita",
    roleId: "asha",
    roleLabel: "ASHA worker, pin 400070",
    org: "Community health (sandbox)",
    home: "/asha",
    workspaces: ["asha"],
    approverLabel: "Sunita (ASHA)",
    ashaId: "ASHA01",
  },
  {
    email: "chemist@unitymedical.demo",
    password: DEMO_PASSWORD,
    name: "Rakesh",
    roleId: "chemist",
    roleLabel: "Chemist, Unity Medical & General Stores",
    org: "Unity Medical & General Stores",
    home: "/chemist",
    workspaces: ["chemist"],
    approverLabel: "Rakesh (chemist)",
    chemistId: "CH020",
  },
  {
    email: "founder@firstsign.demo",
    password: DEMO_PASSWORD,
    name: "Founder",
    roleId: "founder",
    roleLabel: "All workspaces",
    org: "FirstSign",
    home: "/distributor/inbox",
    workspaces: ["distributor", "officer", "asha", "chemist"],
    approverLabel: "Rohan (clerk)",
  },
];

export const WORKSPACE_LABEL: Record<Workspace, string> = {
  distributor: "Distributor",
  officer: "Health officer",
  asha: "ASHA",
  chemist: "Chemist",
};

export const WORKSPACE_HOME: Record<Workspace, string> = {
  distributor: "/distributor/inbox",
  officer: "/officer",
  asha: "/asha",
  chemist: "/chemist",
};

export function workspaceOfPath(path: string): Workspace | null {
  if (path.startsWith("/chemist")) return "chemist";
  if (path.startsWith("/distributor")) return "distributor";
  if (path.startsWith("/officer")) return "officer";
  if (path.startsWith("/asha")) return "asha";
  return null;
}

export function initials(name: string): string {
  const parts = name.replace(/^Dr\.?\s+/i, "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  const letters = parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[parts.length - 1][0];
  return letters.toUpperCase();
}

/** Returns the matching account, or null for wrong credentials. Email is case-insensitive. */
export function authenticate(email: string, password: string): DemoUser | null {
  const e = email.trim().toLowerCase();
  return ACCOUNTS.find((a) => a.email === e && a.password === password) ?? null;
}

export function findAccount(email: string | null | undefined): DemoUser | null {
  if (!email) return null;
  const e = email.trim().toLowerCase();
  return ACCOUNTS.find((a) => a.email === e) ?? null;
}

// ---- session storage: localStorage when it works, memory otherwise ----

export const SESSION_KEY = "firstsign.session";
let memorySession: string | null = null;

export function loadSession(): DemoUser | null {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(SESSION_KEY);
  } catch {
    raw = null;
  }
  return findAccount(raw ?? memorySession);
}

export function saveSession(user: DemoUser | null): void {
  memorySession = user ? user.email : null;
  try {
    if (user) window.localStorage.setItem(SESSION_KEY, user.email);
    else window.localStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage unavailable: the in-memory copy keeps the session for this tab */
  }
}

// ---- route guard decision (pure, so it can be tested without a DOM) ----

export type GuardResult = "login" | "ok" | "forbidden";

/** `workspace` is the workspace a route belongs to, or null for routes open to every signed-in user. */
export function guardDecision(user: DemoUser | null, workspace: Workspace | null): GuardResult {
  if (!user) return "login";
  if (workspace === null) return "ok";
  return user.workspaces.includes(workspace) ? "ok" : "forbidden";
}

/** Only allow same-app paths as a post-login target. */
export function safeNext(next: string | null | undefined): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/login")) return null;
  return next;
}
