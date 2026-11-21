"""Assembles FirstSign_demo.mp4 (1920x1080 H.264 + AAC) and FirstSign_demo_captions.srt from raw scene videos,
gTTS voiceover per scene, the title/closing cards and burned captions (drawtext, Segoe UI)."""
import json, subprocess, shutil
from pathlib import Path
from scenes import SCENES

D = Path(__file__).parent
RAW = D / "raw"; AUD = D / "audio"; B = D / "build"
B.mkdir(exist_ok=True)
DUR = json.loads((AUD / "durations.json").read_text())
TIM = json.loads((RAW / "timing.json").read_text())
SPEED = {"s5_asha": 1.6}          # the two ASHA reports take longer than the narration; play that scene faster
FONT = "C\\:/Windows/Fonts/segoeui.ttf"
BGC = "0x0C1519"
PAD = 0.6


def run(cmd):
    r = subprocess.run(cmd, cwd=B, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1500:]); raise SystemExit(1)


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_time(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"


clips, srt, t_acc = [], [], 0.0
for i, sc in enumerate(SCENES):
    sid = sc["id"]
    audio = AUD / f"{sid}.mp3"
    a_len = DUR[sid]
    card = sid in ("s0_title", "s7_close")
    if card:
        v_len = 0
    else:
        sp = SPEED.get(sid, 1.0)
        v_len = (TIM[sid]["seconds"] + 0.4) / sp
    dur = round(max(a_len + PAD, v_len), 2)
    out = f"scene_{i}.mp4"
    # caption text files
    caps = sc["caps"]; n = len(caps)
    seg = dur / n
    cap_filters = []
    for j, c in enumerate(caps):
        tf = f"cap_{i}_{j}.txt"
        (B / tf).write_text(c, encoding="utf-8")
        a, b = j * seg, (j + 1) * seg
        cap_filters.append(
            f"drawtext=fontfile='{FONT}':textfile={tf}:fontcolor=white:fontsize=44:x=(w-text_w)/2:y=1035-text_h/2:enable='gte(t,{a:.2f})*lt(t,{b:.2f})'")
        srt.append((t_acc + a, t_acc + b - 0.05, c))
    bar = f"drawbox=x=0:y=990:w=1920:h=90:color={BGC}@1:t=fill"
    fades = f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3:.2f}:d=0.3"
    if card:
        img = D / ("card_title.png" if sid == "s0_title" else "card_closing.png")
        vin = ["-loop", "1", "-framerate", "30", "-i", str(img)]
        vf = (f"scale=2112:-1,zoompan=z='1+0.00008*on':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30,"
              f"{bar},{','.join(cap_filters)},{fades},format=yuv420p")
        # zoompan with d=1 per input frame; image looped as a 30 fps stream
    else:
        raw = RAW / f"{sid}.webm"
        sp = SPEED.get(sid, 1.0)
        phone = sid == "s5_asha"
        w = 458 if phone else 1584
        vin = ["-ss", str(TIM[sid]["trim"]), "-i", str(raw)]
        vf = (f"setpts=PTS/{sp},fps=30,scale={w}:990:flags=lanczos,tpad=stop_mode=clone:stop_duration={dur:.2f},"
              f"pad=1920:1080:(1920-{w})/2:0:color={BGC},{bar},{','.join(cap_filters)},{fades},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *vin, "-i", str(audio),
           "-filter_complex", f"[0:v]{vf}[v];[1:a]apad,atrim=0:{dur:.2f},afade=t=in:st=0:d=0.2,afade=t=out:st={dur - 0.4:.2f}:d=0.4[a]",
           "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", out]
    print(sid, "dur", dur, flush=True)
    run(cmd)
    clips.append(out)
    t_acc += dur

(B / "list.txt").write_text("\n".join(f"file '{c}'" for c in clips))
final = D / "FirstSign_demo.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "-movflags", "+faststart", str(final)])
with open(D / "FirstSign_demo_captions.srt", "w", encoding="utf-8") as f:
    for k, (a, b, c) in enumerate(srt, 1):
        f.write(f"{k}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
print("total", round(t_acc, 1), "s", probe(final), "s", round(final.stat().st_size / 1e6, 1), "MB")
