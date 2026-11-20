import { Link } from "react-router-dom";
import { cx } from "../../lib/format";

/** The one brand motif: a thin line with a single ECG blip. */
export function PulseLine({ className, width = 64 }: { className?: string; width?: number }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 64 24"
      width={width}
      height={(width / 64) * 24}
      className={cx("text-accent", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M0 12 H18 L22 4 L27 20 L31 12 H64" />
    </svg>
  );
}

export function Logo({ tagline = false }: { tagline?: boolean }) {
  return (
    <Link to="/" aria-label="FirstSign home" className="inline-flex items-center gap-2 rounded-lg">
      <PulseLine width={36} />
      <span className="flex flex-col leading-none">
        <span className="font-display text-xl font-bold text-text">
          First<span className="text-accentText">Sign</span>
        </span>
        {tagline && (
          <span lang="hi" className="mt-1 text-sm text-muted">
            पहला संकेत
          </span>
        )}
      </span>
    </Link>
  );
}
