#!/usr/bin/env python3
"""Render a brand-styled terminal demo of prd-maker as an animated GIF.

Content is faithful to real behavior: the questions come from the interview
guide, the results mirror the real scenario-2 run (PRD.md, 5/5 linter, etc.).
It is a styled demo, not a screen recording.

Requires Pillow (`pip install pillow`) and a monospace font; FONT_PATH below
points at macOS Menlo — change it on other platforms. Run: python3 assets/generate_demo.py
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 860, 560
PAD_X = 34
TOP_BAR = 42
LINE_H = 25
START_Y = TOP_BAR + 22
FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

BG = (18, 20, 43)
BAR = (27, 31, 59)
DOT_R, DOT_Y, DOT_G = (255, 95, 86), (255, 189, 46), (39, 201, 63)

# colors
WHITE = (233, 230, 255)
DIM = (107, 111, 174)
PURPLE = (167, 139, 250)
TEAL = (94, 214, 196)
GRAY = (201, 198, 240)

font = ImageFont.truetype(FONT_PATH, 16, index=0)
bold = ImageFont.truetype(FONT_PATH, 16, index=1)
tfont = ImageFont.truetype(FONT_PATH, 12, index=1)

CHAR_W = font.getlength("M")


def base():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14, fill=BG)
    d.rounded_rectangle([0, 0, W - 1, TOP_BAR], radius=14, fill=BAR)
    d.rectangle([0, TOP_BAR - 14, W - 1, TOP_BAR], fill=BAR)
    for i, c in enumerate((DOT_R, DOT_Y, DOT_G)):
        cx = 22 + i * 22
        d.ellipse([cx, TOP_BAR // 2 - 6, cx + 12, TOP_BAR // 2 + 6], fill=c)
    d.text((W / 2, TOP_BAR / 2), "prd-maker", font=tfont, fill=DIM, anchor="mm")
    return img, d


# screen = list of segments-lists; each line is a list of (text, color, font)
screen = []
frames = []  # (image, duration_ms)


def draw_line(d, y, segs, cursor=False):
    x = PAD_X
    for text, color, fnt in segs:
        d.text((x, y), text, font=fnt, fill=color)
        x += fnt.getlength(text)
    if cursor:
        d.rectangle([x + 1, y + 2, x + 1 + CHAR_W, y + 18], fill=WHITE)


def render(partial=None, cursor=False):
    img, d = base()
    y = START_Y
    for segs in screen:
        draw_line(d, y, segs)
        y += LINE_H
    if partial is not None:
        draw_line(d, y, partial, cursor=cursor)
    elif cursor:
        draw_line(d, y, [("", WHITE, font)], cursor=True)
    return img


def emit(dur, partial=None, cursor=False):
    frames.append((render(partial, cursor), dur))


def blank():
    screen.append([])


def line(segs, hold=6, dur=90):
    screen.append(segs)
    emit(dur)
    for i in range(hold):
        emit(240, cursor=(i % 2 == 0))


def type_cmd(text, dur=42):
    # char by char, for the command line
    for i in range(1, len(text) + 1):
        emit(dur, partial=[(text[:i], WHITE, bold)], cursor=True)
    screen.append([(text, WHITE, bold)])


def type_answer(segs_full, dur=55):
    # reveal the answer word by word (segs_full is a single (text,color,font))
    text, color, fnt = segs_full
    prefix = [("> ", DIM, font)]
    words = text.split(" ")
    acc = ""
    for w in words:
        acc = (acc + " " + w).strip()
        emit(dur, partial=prefix + [(acc, color, fnt)], cursor=True)
    screen.append(prefix + [(text, color, fnt)])
    for i in range(4):
        emit(240, cursor=(i % 2 == 0))


# ---- timeline (faithful demo) ----
type_cmd("$ /prd-maker")
for i in range(5):
    emit(260, cursor=(i % 2 == 0))
blank()

line([("? ", PURPLE, bold), ("What do you want to build?", GRAY, font)], hold=3)
type_answer(("A bookmark SaaS — Next.js + Supabase, Chrome", WHITE, font))
screen.append([("  extension, tag management on the web.", WHITE, font)])
emit(700)
blank()

line([("Q1  ", PURPLE, bold), ("Why build this — what's the pain today?", GRAY, font)], hold=3)
type_answer(("Hundreds pile up and I can never find them.", WHITE, font))
blank()

line([("Q2  ", PURPLE, bold), ("Build one thing first — which?", GRAY, font)], hold=3)
type_answer(("The save pipeline: extension → DB.", WHITE, font))
blank()

line([("   … 6 more adaptive questions, 10 max …", DIM, font)], hold=5)
blank()

line([("✓ ", TEAL, bold), ("Understanding confirmed", TEAL, font)], hold=2)
line([("✓ ", TEAL, bold), ("PRD drafted", TEAL, font)], hold=2)
line([("✓ ", TEAL, bold), ("Structure linter — 5 / 5 checks passed", TEAL, font)], hold=4)
blank()

line([("  PRD.md  ·  7 sections  ·  2 phases  ·  8 non-goals", WHITE, bold)], hold=4)
line([("→ Hand to any agent:  ", PURPLE, bold), ('"build this PRD"', WHITE, font)], hold=2)

# long final hold before loop
for i in range(14):
    emit(260, cursor=(i % 2 == 0))

imgs = [f[0] for f in frames]
durs = [f[1] for f in frames]
out = "/Users/justin/workspace/startup/prd-maker/assets/demo.gif"
imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durs,
             loop=0, optimize=True, disposal=2)
print(f"frames: {len(imgs)}  ->  {out}")
