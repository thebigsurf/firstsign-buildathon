import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { authenticate, loadSession, saveSession, type DemoUser } from "./auth";

interface AuthValue {
  user: DemoUser | null;
  /** Returns the user on success, null on wrong credentials. */
  signIn: (email: string, password: string) => DemoUser | null;
  signOut: () => void;
}

const Ctx = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(() => loadSession());
  const signIn = useCallback((email: string, password: string) => {
    const u = authenticate(email, password);
    if (u) {
      saveSession(u);
      setUser(u);
    }
    return u;
  }, []);
  const signOut = useCallback(() => {
    saveSession(null);
    setUser(null);
  }, []);
  const value = useMemo(() => ({ user, signIn, signOut }), [user, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}

/** The signed-in user. Only call inside routes behind the guard. */
export function useUser(): DemoUser {
  const { user } = useAuth();
  if (!user) throw new Error("No signed-in user");
  return user;
}
