"""Title and closing cards, 1920x1080, in the FirstSign design tokens (docs/DESIGN.md)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D = Path(__file__).parent
BG, SURFACE, TEXT, MUTED, ACCENT, ACCENT_SOFT, BORDER = "#F4F7F8", "#FFFFFF", "#0F1F26", "#4A5D66", "#0B5C7A", "#DCEFF5", "#C5D1D6"
GOLD = "#8A5A00"; GOLD_BG = "#FFF0CC"
F = "C:/Windows/Fonts/"


def font(name, size):
    return ImageFont.truetype(F + name, size)


def pulse(d, x, y, scale, color=ACCENT, width=8):
    # SVG path from the design: M0 12 H18 L22 4 L27 20 L31 12 H64
    pts = [(0, 12), (18, 12), (22, 4), (27, 20), (31, 12), (64, 12)]
    d.line([(x + px * scale, y + (py - 12) * scale) for px, py in pts], fill=color, width=width, joint="curve")


def centered(d, text, y, fnt, fill, w=1920):
    b = d.textbbox((0, 0), text, font=fnt)
    d.text(((w - (b[2] - b[0])) / 2 - b[0], y), text, font=fnt, fill=fill)


def pill(d, text, y, fnt, fg, bg, padx=44, pady=18):
    b = d.textbbox((0, 0), text, font=fnt)
    w, h = b[2] - b[0] + 2 * padx, b[3] - b[1] + 2 * pady
    x = (1920 - w) / 2
    d.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=bg)
    d.text((x + padx - b[0], y + pady - b[1]), text, font=fnt, fill=fg)


def logo(d, y, size):
    f = font("segoeuib.ttf", size)
    a, b = "First", "Sign"
    wa = d.textlength(a, font=f); wb = d.textlength(b, font=f)
    mark_w = 64 * (size / 40)
    total = mark_w + 30 + wa + wb
    x = (1920 - total) / 2
    pulse(d, x, y + size * 0.75, size / 40, width=max(6, size // 18))
    x += mark_w + 30
    d.text((x, y), a, font=f, fill=TEXT)
    d.text((x + wa, y), b, font=f, fill=ACCENT)


def base():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1920, 14), fill=ACCENT)
    return im, d


def title():
    im, d = base()
    centered(d, "Google DeepMind x Google Cloud Startup Buildathon  ·  Mumbai", 70, font("segoeui.ttf", 32), MUTED)
    logo(d, 270, 190)
    centered(d, "पहला संकेत", 520, font("Nirmala.ttc", 72), MUTED)
    centered(d, "Orders into bills. A first sign of illness.", 650, font("segoeuisl.ttf", 58), TEXT)
    pill(d, "Built with Gemini on Google Cloud", 790, font("segoeuib.ttf", 40), "#FFFFFF", ACCENT)
    centered(d, "Simulated data is labelled as simulated throughout.", 930, font("segoeui.ttf", 28), MUTED)
    im.save(D / "card_title.png")


def closing():
    im, d = base()
    logo(d, 110, 120)
    centered(d, "Orders into bills, and a first sign of illness", 300, font("segoeuisl.ttf", 54), TEXT)
    items = [("Chemists", "send orders the way they already do"),
             ("Distributors", "get ready-to-bill orders and a stock radar"),
             ("Health officers", "get an early, explained, human-approved alert"),
             ("ASHA workers", "confirm it on the ground, in their own language")]
    y = 420
    for head, rest in items:
        d.rounded_rectangle((330, y, 1590, y + 86), radius=14, fill=SURFACE, outline=BORDER, width=2)
        d.text((370, y + 20), head, font=font("segoeuib.ttf", 38), fill=ACCENT)
        d.text((680, y + 22), rest, font=font("segoeui.ttf", 36), fill=TEXT)
        y += 104
    pill(d, "Built with Gemini on Google Cloud", 850, font("segoeuib.ttf", 40), "#FFFFFF", ACCENT)
    centered(d, "History is simulated and labelled. Weather and air are real (Open-Meteo). A real pilot is the real test.", 940, font("segoeui.ttf", 28), GOLD)
    im.save(D / "card_closing.png")


if __name__ == "__main__":
    title(); closing(); print("cards done")
