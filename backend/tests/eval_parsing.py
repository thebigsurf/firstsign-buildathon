"""Parsing eval harness: scores real Gemini parsing against data/samples/*.expected.json.

Run from backend/:   python -m tests.eval_parsing            (live Gemini, uses the key in .env)
                     python -m tests.eval_parsing --json out.json

It prints, per sample and in total:
  * line recall   : expected lines found with the right sku_id AND quantity
  * sku accuracy  : expected lines found with the right sku_id (quantity ignored)
  * silent errors : lines marked "matched" that are wrong (the number that must be zero)
  * uncertain / unknown counts and latency
Feeds the quality gate in docs/METRICS.md (>= 85% lines correct, 0 silently wrong).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.catalogue import Catalogue  # noqa: E402
from app.config import Settings  # noqa: E402
from app.gemini import GeminiClient  # noqa: E402
from app.parsing import Upload, parse_order  # noqa: E402
from app.store import Reference  # noqa: E402

MEDIA_SUFFIXES = (".mp3", ".wav", ".ogg", ".jpg", ".jpeg", ".png")


@dataclasses.dataclass
class SampleScore:
    name: str
    expected: int
    sku_correct: int
    fully_correct: int
    silent_errors: int
    uncertain: int
    unknown: int
    extra_lines: int
    latency_ms: int
    model: str
    problems: list[str]


def score_sample(parsed_lines: list[Any], expected_lines: list[dict[str, Any]]) -> tuple[int, int, int, list[str]]:
    """Greedy match of parsed lines to expected lines by sku_id; returns (sku_ok, full_ok, silent, problems)."""
    remaining = list(parsed_lines)
    sku_ok = full_ok = silent = 0
    problems: list[str] = []
    for want in expected_lines:
        hit = next((p for p in remaining if p.sku_id == want.get("sku_id")), None)
        if hit is None:
            problems.append(f"missing {want.get('raw_text')} ({want.get('sku_id')})")
            continue
        remaining.remove(hit)
        sku_ok += 1
        if hit.qty == want.get("qty"):
            full_ok += 1
        elif hit.status == "matched":
            silent += 1
            problems.append(f"qty {hit.qty} != {want.get('qty')} for {want.get('raw_text')} (status matched)")
    for stray in remaining:
        if stray.status == "matched":
            silent += 1
            problems.append(f"matched but not expected: {stray.raw_text} -> {stray.sku_id}")
    return sku_ok, full_ok, silent, problems


def run(settings: Settings, ref: Reference) -> list[SampleScore]:
    gemini, catalogue = GeminiClient(settings), Catalogue(ref.catalogue)
    scores: list[SampleScore] = []
    samples = settings.data_dir / "samples"
    for expected_path in sorted(samples.glob("order_*.expected.json")):
        stem = expected_path.name[: -len(".expected.json")]
        media = next((p for s in MEDIA_SUFFIXES if (p := samples / f"{stem}{s}").exists()), None)
        if media is None:
            continue
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        chemist = ref.chemist(expected["chemist_id"]) or {"chemist_id": expected["chemist_id"], "language": "hi"}
        parsed = parse_order(gemini, catalogue, chemist, upload=Upload(media.read_bytes(), media.name))
        if parsed.model.startswith("offline"):
            print(f"{media.name}: Gemini was unavailable, so this sample is NOT scored (pre-recorded answer returned).")
            continue
        sku_ok, full_ok, silent, problems = score_sample(parsed.lines, expected["lines"])
        scores.append(SampleScore(
            name=media.name, expected=len(expected["lines"]), sku_correct=sku_ok, fully_correct=full_ok,
            silent_errors=silent, uncertain=sum(ln.status == "uncertain" for ln in parsed.lines),
            unknown=sum(ln.status == "unknown" for ln in parsed.lines),
            extra_lines=max(0, len(parsed.lines) - len(expected["lines"])), latency_ms=parsed.latency_ms,
            model=parsed.model, problems=problems,
        ))
    return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="also write the scores to this JSON file")
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.offline:
        print("No GEMINI_API_KEY (or DEMO_OFFLINE=1): the eval needs live Gemini.", file=sys.stderr)
        return 2
    scores = run(settings, Reference.load(settings.data_dir))
    if not scores:
        print("No sample media found in data/samples.", file=sys.stderr)
        return 2
    print(f"{'sample':<16}{'lines':>6}{'sku ok':>8}{'full ok':>9}{'silent':>8}{'uncert':>8}{'unkn':>6}{'ms':>8}  model")
    for s in scores:
        print(f"{s.name:<16}{s.expected:>6}{s.sku_correct:>8}{s.fully_correct:>9}{s.silent_errors:>8}"
              f"{s.uncertain:>8}{s.unknown:>6}{s.latency_ms:>8}  {s.model}")
        for problem in s.problems:
            print(f"    - {problem}")
    total = sum(s.expected for s in scores)
    print(f"\nTOTAL expected lines {total}: sku accuracy {sum(s.sku_correct for s in scores) / total:.0%}, "
          f"line recall (sku and qty) {sum(s.fully_correct for s in scores) / total:.0%}, "
          f"silent errors {sum(s.silent_errors for s in scores)}")
    if args.json:
        args.json.write_text(json.dumps([dataclasses.asdict(s) for s in scores], indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
