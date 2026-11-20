"""Create the media files for data/samples/ from the ground-truth JSON written by generate.py.

Voice notes: Hindi/Marathi speech synthesised with gTTS (Google Translate TTS), read from each
sample's expected transcript. Handwritten photos: rendered with PIL using the open-licence Kalam
handwriting font on lined paper with rotation, ink wobble, shadow and noise.

Usage:  python data/tools/make_media.py   (needs network for gTTS; run generate.py first)
Gemini image and audio generation were tried first and were not available on the free-tier key.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA_DIR = Path(__file__).resolve().parent.parent
SAMPLES = DATA_DIR / "samples"
FONT_PATH = Path(__file__).resolve().parent / "fonts" / "Kalam-Regular.ttf"

PAPER = (247, 243, 226)
RULE = (170, 195, 215)
MARGIN = (214, 120, 120)
INK = (28, 44, 120)
WIDTH, HEIGHT = 1000, 1350
RULE_GAP = 100
TOP = 230


def make_audio(text: str, lang: str, out: Path) -> None:
    gTTS(text=text, lang=lang, tld="co.in").save(str(out))


def write_line(base: Image.Image, text: str, xy: tuple[int, int], size: int, rng: random.Random,
               strike: bool = False) -> None:
    """Draw one handwritten line onto `base` with per-line tilt and per-word wobble."""
    font = ImageFont.truetype(str(FONT_PATH), size)
    layer = Image.new("RGBA", (WIDTH, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 10
    ink = (INK[0] + rng.randint(-8, 8), INK[1] + rng.randint(-8, 8), INK[2] + rng.randint(-10, 10), 235)
    for word in text.split(" "):
        w = font.getlength(word + " ")
        d.text((x, 40 + rng.randint(-4, 4)), word, font=font, fill=ink)
        x += w + rng.randint(0, 10)
    if strike:
        y = 40 + size * 0.75
        d.line([(0, y), (x, y + rng.randint(-5, 5))], fill=ink, width=5)
    layer = layer.rotate(rng.uniform(-1.6, 1.6), resample=Image.BICUBIC, expand=False)
    base.alpha_composite(layer, (xy[0], xy[1] - 40))


def make_chit(lines: list[str], out: Path, seed: int) -> None:
    rng = random.Random(seed)
    img = Image.new("RGBA", (WIDTH, HEIGHT), PAPER + (255,))
    d = ImageDraw.Draw(img)
    for y in range(TOP, HEIGHT - 40, RULE_GAP):
        d.line([(0, y), (WIDTH, y)], fill=RULE, width=2)
    d.line([(95, 0), (95, HEIGHT)], fill=MARGIN, width=3)
    write_line(img, "Order   20/11", (130, 120), 62, rng)
    row = 0
    for raw in lines:
        struck = raw.startswith("[struck out] ")
        text = raw.replace("[struck out] ", "")
        name, qty = text.rsplit("   ", 1)
        y = TOP + RULE_GAP * row + RULE_GAP - 22
        write_line(img, name, (130, y), 54, rng, strike=struck)
        write_line(img, "-", (640, y), 54, rng, strike=struck)
        write_line(img, qty, (700, y), 54, rng, strike=struck)
        row += 1
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    nprng = np.random.RandomState(seed)
    arr += nprng.normal(0, 6, arr.shape)
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    shade = 1 - 0.18 * (((xx - WIDTH * 0.45) / WIDTH) ** 2 + ((yy - HEIGHT * 0.4) / HEIGHT) ** 2) * 2.2
    arr *= shade[..., None] * (1 + 0.04 * (xx / WIDTH))[..., None]
    photo = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    canvas = Image.new("RGB", (WIDTH + 120, HEIGHT + 120), (62, 56, 50))
    canvas.paste(photo.rotate(rng.uniform(-2.2, 2.2), resample=Image.BICUBIC, expand=True, fillcolor=(62, 56, 50)), (60, 60))
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.7))
    canvas.save(out, quality=84)


def main() -> None:
    inbox = json.loads((DATA_DIR / "demo_inbox.json").read_text(encoding="utf-8"))
    for msg in inbox:
        if msg["media"] is None:
            continue
        expected = json.loads((DATA_DIR / msg["expected"]).read_text(encoding="utf-8"))
        out = DATA_DIR / msg["media"]
        if msg["type"] == "voice":
            make_audio(expected["transcript"], "mr" if expected["language"] == "mr" else "hi", out)
        else:
            make_chit(expected["transcript"].split("\n"), out, seed=int(msg["id"].split("_")[1]) * 7)
        print("wrote", out.name)
    for exp in sorted(SAMPLES.glob("asha_*.expected.json")):
        report = json.loads(exp.read_text(encoding="utf-8"))
        out = SAMPLES / exp.name.replace(".expected.json", ".mp3")
        make_audio(report["transcript"], "mr" if report["language"] == "mr" else "hi", out)
        print("wrote", out.name)


if __name__ == "__main__":
    main()
