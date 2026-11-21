"""Measure real Gemini usage on the bundled samples and print tokens, latency and INR per input type.

    python -m app.measure --orders --asha --explain 2 --out ../docs/measure_run.json

Bypasses the disk cache so every call is live (this spends real money: about 14 calls for orders + ASHA, 2 per
explanation). Uses a throw-away in-memory store.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from .config import Settings
from .context import build_context
from .errors import AppError
from .parsing import Upload, parse_asha_report
from .store import LocalStore


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", action="store_true")
    ap.add_argument("--asha", action="store_true")
    ap.add_argument("--explain", type=int, default=0, help="number of alerts to explain")
    ap.add_argument("--only", default="", help="comma list of message ids, e.g. msg_05,msg_06")
    ap.add_argument("--resolution", default="", help="override GEMINI_IMAGE_RESOLUTION for this run")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    settings = Settings.from_env()
    if settings.offline:
        print("Offline mode: nothing to measure.")
        return 0
    settings = dataclasses.replace(settings, bypass_cache=True, parse_deadline_s=settings.warm_deadline_s,
                                   daily_budget_inr=0)
    if args.resolution:
        settings = dataclasses.replace(settings, image_resolution=args.resolution)
    ctx = build_context(settings, LocalStore(None))
    only = {x for x in args.only.split(",") if x}
    if args.orders:
        for message in ctx.ref.inbox:
            if only and message["id"] not in only:
                continue
            try:
                parsed = ctx.services.parse_order(message["chemist_id"], message["id"], None, None)
                print(f"order {message['id']} {message['type']:<6} {parsed.model} lines={len(parsed.lines)}", flush=True)
            except AppError as exc:
                print(f"order {message['id']} FAILED {exc.code}", flush=True)
    if args.asha:
        for path in sorted((settings.data_dir / "samples").glob("asha_*.mp3")):
            try:
                parsed = parse_asha_report(ctx.gemini, {"language": "hi"}, upload=Upload(path.read_bytes(), path.name))
                print(f"asha {path.name} {parsed.model}", flush=True)
            except AppError as exc:
                print(f"asha {path.name} FAILED {exc.code}", flush=True)
    done = 0
    for alert in ctx.signal.alerts() if args.explain else []:
        if alert.level != "alert" or done >= args.explain:
            continue
        done += 1
        plan = ctx.agent.explain(alert.alert_id, refresh=True)
        print(f"explain {alert.alert_id} {plan.model} grounded={plan.grounded}", flush=True)
    rows = ctx.gemini.ledger.rows()
    summary = ctx.gemini.ledger.summary()
    if args.out:
        Path(args.out).write_text(json.dumps({"rows": rows, "summary": summary}, indent=1), encoding="utf-8")
    for job, b in summary["by_job"].items():
        print(f"{job:<16} n={b['calls']:<3} prompt={b['avg_prompt_tokens']:<6} out={b['avg_output_tokens']:<5} "
              f"think={b['avg_thought_tokens']:<5} lat={b['avg_latency_ms']}ms inr={b['avg_cost_inr']}")
    print("total INR", summary["totals"]["cost_inr"], "calls", summary["totals"]["calls"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
