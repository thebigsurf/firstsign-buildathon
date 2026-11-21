"""Writes narration.md, per-scene gTTS voiceover (en, co.in) and audio/durations.json."""
import json, subprocess, sys
from pathlib import Path
from scenes import SCENES
D = Path(__file__).parent; A = D / "audio"; A.mkdir(exist_ok=True)
words = sum(len(s["text"].split()) for s in SCENES)
md = ["# FirstSign demo narration", "", f"About {words} words. Plain English. The history shown is simulated and the narration says so.", ""]
for s in SCENES:
    md += [f"## {s['title']}", "", s["text"], ""]
(D / "narration.md").write_text("\n".join(md), encoding="utf-8")
from gtts import gTTS
dur = {}
for s in SCENES:
    out = A / f"{s['id']}.mp3"
    raw = A / f"{s['id']}_raw.mp3"
    gTTS(s["text"], lang="en", tld="co.in").save(str(raw))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter:a", "atempo=1.12", str(out)], check=True)
    raw.unlink()
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    dur[s["id"]] = float(r.stdout.strip()); print(s["id"], dur[s["id"]])
(A / "durations.json").write_text(json.dumps(dur, indent=1))
print("words", words, "total audio", sum(dur.values()))
