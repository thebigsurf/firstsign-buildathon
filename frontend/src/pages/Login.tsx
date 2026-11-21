import { Moon, Sun } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Logo, PulseLine } from "../components/ui/Pulse";
import { ACCOUNTS, safeNext } from "../lib/auth";
import { useAuth } from "../lib/AuthContext";
import { useDocumentTitle } from "../lib/hooks";
import { useTheme } from "../lib/theme";

export function Login() {
  useDocumentTitle("Sign in");
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const { theme, toggle } = useTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to={next ?? user.home} replace />;

  const submit = (e: FormEvent): void => {
    e.preventDefault();
    const u = signIn(email, password);
    if (!u) {
      setError("That email and password don't match. Check them, or use one of the demo accounts below.");
      return;
    }
    setError(null);
    navigate(next ?? u.home, { replace: true });
  };

  return (
    <div className="min-h-dvh bg-bg">
      <header className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Logo />
        <button
          type="button"
          onClick={toggle}
          aria-label="Switch theme"
          aria-pressed={theme === "dark"}
          className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-sunken"
        >
          {theme === "dark" ? <Sun size={20} strokeWidth={1.75} aria-hidden="true" /> : <Moon size={20} strokeWidth={1.75} aria-hidden="true" />}
        </button>
      </header>

      <main id="main" className="mx-auto grid max-w-5xl gap-6 px-4 pb-12 pt-4 md:grid-cols-2 md:items-start md:gap-8 md:pt-10">
        <section aria-labelledby="signin-h" className="card space-y-5 p-6 md:p-8">
          <div className="space-y-2">
            <PulseLine width={40} />
            <h1 id="signin-h" className="text-h1">Sign in to your workspace</h1>
            <p className="m-0 text-muted">Use your work email. Orders, alerts and visit lists live inside your workspace.</p>
          </div>
          <form onSubmit={submit} noValidate className="space-y-4">
            {error && (
              <p role="alert" className="panel-error m-0 text-sm">
                {error}
              </p>
            )}
            <label className="block text-sm font-medium">
              Email
              <input
                className="input mt-1"
                type="email"
                name="email"
                autoComplete="username"
                inputMode="email"
                value={email}
                aria-invalid={error ? true : undefined}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.demo"
              />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input
                className="input mt-1"
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                aria-invalid={error ? true : undefined}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <Button type="submit" size="lg" className="w-full">
              Sign in
            </Button>
          </form>
        </section>

        <section aria-labelledby="demo-h" className="card space-y-3 p-5 md:p-6">
          <div>
            <h2 id="demo-h" className="text-h3">Demo accounts</h2>
            <p className="m-0 mt-1 text-sm text-muted">
              This is a sandbox with simulated data and a demo sign-in, not real authentication. Pick an account to try its workspace.
            </p>
          </div>
          <ul className="m-0 list-none divide-y divide-border p-0">
            {ACCOUNTS.map((a) => (
              <li key={a.email} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="m-0 font-medium">
                    {a.name} <span className="font-normal text-muted">· {a.roleLabel}</span>
                  </p>
                  <p className="mono m-0 break-all text-xs text-muted">{a.email}</p>
                  <p className="mono m-0 text-xs text-muted">password: {a.password}</p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  aria-label={`Use this account: ${a.name}, ${a.roleLabel}`}
                  className="shrink-0"
                  onClick={() => {
                    setEmail(a.email);
                    setPassword(a.password);
                    setError(null);
                  }}
                >
                  Use this account
                </Button>
              </li>
            ))}
          </ul>
        </section>
      </main>
      <p className="mx-auto max-w-5xl px-4 pb-8 text-center text-xs text-muted">
        FirstSign sandbox · all data is simulated · <span lang="hi">यह डेमो डेटा है, असली नहीं।</span>
      </p>
    </div>
  );
}
