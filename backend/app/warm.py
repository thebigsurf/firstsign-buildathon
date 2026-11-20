"""Warm the Gemini disk cache before a demo.

    python -m app.warm            # parse every inbox message and explain every open alert
    python -m app.warm --no-explain

Runs against a throw-away in-memory store, so the demo state (inbox statuses, audit log) stays untouched; only
backend/.cache is filled. After this, every demo step that repeats one of these inputs answers instantly even if
Gemini is slow or rate-limited that day.
"""

from __future__ import annotations

import argparse
import sys
import time

from .config import Settings
from .context import build_context
from .errors import AppError
from .store import LocalStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-explain", action="store_true", help="only parse the inbox")
    args = parser.parse_args()

    settings = Settings.from_env()
    if settings.offline:
        print("Offline mode (no key or DEMO_OFFLINE=1): nothing to warm.")
        return 0
    ctx = build_context(settings, LocalStore(None))
    failures = 0
    for message in ctx.ref.inbox:
        started = time.perf_counter()
        try:
            parsed = ctx.services.parse_order(message["chemist_id"], message["id"], None, None)
            status = f"{len(parsed.lines)} lines, {parsed.model}{' (cached)' if parsed.cached else ''}"
        except AppError as exc:
            failures += 1
            status = f"FAILED {exc.code}: {exc.message[:90]}"
        print(f"parse   {message['id']:<8} {time.perf_counter() - started:6.1f}s  {status}", flush=True)
    if not args.no_explain:
        for alert in ctx.signal.alerts():
            if alert.level != "alert":
                continue
            started = time.perf_counter()
            try:
                plan = ctx.agent.explain(alert.alert_id)
                status = f"{plan.model}, {len(plan.sources)} sources, grounded={plan.grounded}"
            except AppError as exc:
                failures += 1
                status = f"FAILED {exc.code}: {exc.message[:90]}"
            print(f"explain {alert.alert_id:<18} {time.perf_counter() - started:6.1f}s  {status}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
