import { Lock } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { guardDecision, type Workspace } from "../lib/auth";
import { useAuth } from "../lib/AuthContext";
import { useDocumentTitle } from "../lib/hooks";
import { ButtonLink } from "./ui/Button";
import { EmptyState } from "./ui/States";

/** Redirects to /login (remembering where the person was going) when signed out. */
export function RequireAuth() {
  const { user } = useAuth();
  const loc = useLocation();
  if (guardDecision(user, null) === "login") {
    const next = loc.pathname + loc.search;
    return <Navigate to={next && next !== "/" ? `/login?next=${encodeURIComponent(next)}` : "/login"} replace />;
  }
  return <Outlet />;
}

/** Shows a polite message when the signed-in role does not own this workspace. */
export function RequireWorkspace({ workspace }: { workspace: Workspace }) {
  const { user } = useAuth();
  useDocumentTitle("No access");
  const decision = guardDecision(user, workspace);
  if (decision === "login") return <Navigate to="/login" replace />;
  if (decision === "forbidden") {
    return (
      <div className="mx-auto max-w-xl px-4 py-12">
        <h1 className="sr-only">No access</h1>
        <EmptyState
          icon={Lock}
          title="You don't have access to this workspace"
          body="Your account is set up for a different workspace. Go back to your own home screen."
          action={<ButtonLink to={user?.home ?? "/"}>Go to my home</ButtonLink>}
        />
      </div>
    );
  }
  return <Outlet />;
}

/** "/" sends each person to their own home screen. */
export function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.home ?? "/login"} replace />;
}
