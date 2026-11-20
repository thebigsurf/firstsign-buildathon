import { Compass } from "lucide-react";
import { ButtonLink } from "../components/ui/Button";
import { EmptyState } from "../components/ui/States";
import { useDocumentTitle } from "../lib/hooks";

export function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <div className="mx-auto max-w-xl px-4 py-12">
      <h1 className="sr-only">Page not found</h1>
      <EmptyState
        icon={Compass}
        title="We could not find that page"
        body="The link may be old. Start again from the home page."
        action={<ButtonLink to="/">Go to home</ButtonLink>}
      />
    </div>
  );
}
