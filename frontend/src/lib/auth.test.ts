import { beforeEach, describe, expect, it } from "vitest";
import { ACCOUNTS, authenticate, guardDecision, initials, loadSession, safeNext, saveSession, workspaceOfPath } from "./auth";

function fakeStorage(broken = false): Storage {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => {
      if (broken) throw new Error("denied");
      return m.get(k) ?? null;
    },
    setItem: (k: string, v: string) => {
      if (broken) throw new Error("denied");
      m.set(k, v);
    },
    removeItem: (k: string) => {
      if (broken) throw new Error("denied");
      m.delete(k);
    },
  } as unknown as Storage;
}

function setStorage(s: Storage): void {
  (globalThis as unknown as { window: unknown }).window = { localStorage: s };
}

describe("authenticate", () => {
  it("accepts every demo account, case-insensitive email", () => {
    for (const a of ACCOUNTS) expect(authenticate(a.email.toUpperCase(), "firstsign")?.email).toBe(a.email);
  });
  it("rejects wrong password and unknown email", () => {
    expect(authenticate("clerk@saikrupa.demo", "nope")).toBeNull();
    expect(authenticate("who@x.demo", "firstsign")).toBeNull();
  });
  it("uses fictional .demo domains only", () => {
    for (const a of ACCOUNTS) expect(a.email.endsWith(".demo")).toBe(true);
  });
});

describe("session", () => {
  beforeEach(() => setStorage(fakeStorage()));
  it("round-trips through storage", () => {
    saveSession(ACCOUNTS[0]);
    expect(loadSession()?.email).toBe(ACCOUNTS[0].email);
    saveSession(null);
    expect(loadSession()).toBeNull();
  });
  it("falls back to memory when storage throws", () => {
    setStorage(fakeStorage(true));
    saveSession(ACCOUNTS[2]);
    expect(loadSession()?.email).toBe(ACCOUNTS[2].email);
    saveSession(null);
    expect(loadSession()).toBeNull();
  });
});

describe("guardDecision", () => {
  const byId = (id: string) => ACCOUNTS.find((a) => a.roleId === id)!;
  it("sends signed-out users to login", () => {
    expect(guardDecision(null, "distributor")).toBe("login");
    expect(guardDecision(null, null)).toBe("login");
  });
  it("allows own workspace and shared routes", () => {
    expect(guardDecision(byId("clerk"), "distributor")).toBe("ok");
    expect(guardDecision(byId("officer"), null)).toBe("ok");
  });
  it("forbids other workspaces but not for the founder", () => {
    expect(guardDecision(byId("clerk"), "officer")).toBe("forbidden");
    expect(guardDecision(byId("asha"), "distributor")).toBe("forbidden");
    expect(guardDecision(byId("chemist"), "asha")).toBe("forbidden");
    for (const w of ["distributor", "officer", "asha", "chemist"] as const) expect(guardDecision(byId("founder"), w)).toBe("ok");
  });
  it("maps paths to workspaces", () => {
    expect(workspaceOfPath("/officer/alert/3")).toBe("officer");
    expect(workspaceOfPath("/about")).toBeNull();
  });
});

describe("helpers", () => {
  it("initials", () => {
    expect(initials("Dr. Meera")).toBe("ME");
    expect(initials("Rohan")).toBe("RO");
  });
  it("safeNext blocks external and login targets", () => {
    expect(safeNext("/officer/alert/1")).toBe("/officer/alert/1");
    expect(safeNext("//evil.com")).toBeNull();
    expect(safeNext("https://evil.com")).toBeNull();
    expect(safeNext("/login")).toBeNull();
  });
});
