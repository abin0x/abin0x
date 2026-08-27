"""Render profile-src.png as a dot-matrix (halftone) SVG portrait.

To use a different photo: drop it in as profile-src.png, tune CROP so the face
fills the frame, then run `python dotify.py` (needs Pillow) — it rewrites
avatar-dots.svg. Raise COLS for more detail, lower it for a chunkier look.
"""
import os

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "profile-src.png")
OUT = os.path.join(HERE, "avatar-dots.svg")

CROP = (196, 8, 378, 190)     # tight head-and-shoulders crop
COLS = 110                     # dot columns (higher = sharper face)
CELL = 5                       # px per cell in the output
PAD_X, PAD_TOP, PAD_BOT = 18, 18, 18

im = Image.open(SRC).convert("RGB").crop(CROP)
im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
rows = round(COLS * im.height / im.width)
small = im.resize((COLS, rows), Image.LANCZOS)
small = ImageEnhance.Color(small).enhance(1.30)
small = ImageEnhance.Contrast(small).enhance(1.18)
lum_img = ImageOps.autocontrast(small.convert("L"), cutoff=1)
# a small palette keeps the SVG light: identical colours share one <g fill>
small = small.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")

W = COLS * CELL + PAD_X * 2
H = rows * CELL + PAD_TOP + PAD_BOT

buckets = {}
for y in range(rows):
    for x in range(COLS):
        r, g, b = small.getpixel((x, y))
        lum = lum_img.getpixel((x, y)) / 255.0
        # circular vignette: the portrait dissolves into the background grid
        dx, dy = (x - (COLS - 1) / 2) / (COLS / 2), (y - (rows - 1) / 2) / (rows / 2)
        dist = (dx * dx + dy * dy) ** 0.5
        fade = 1.0 if dist < 0.74 else max(0.0, 1 - (dist - 0.74) / 0.28)
        rad = (CELL * 0.54) * (lum ** 0.55) * fade
        if rad < 0.35:
            continue  # let the dim background grid show through
        cx = PAD_X + x * CELL + CELL // 2
        cy = PAD_TOP + y * CELL + CELL // 2
        col = "#%02x%02x%02x" % (r, g, b)
        buckets.setdefault(col, []).append('<circle cx="%d" cy="%d" r="%.1f"/>' % (cx, cy, rad))

groups = "".join('<g fill="%s">%s</g>' % (c, "".join(v)) for c, v in buckets.items())
n_dots = sum(len(v) for v in buckets.values())

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Mahmudul Hasan Abin, rendered as a dot matrix">
<title>Mahmudul Hasan Abin</title>
<defs>
  <clipPath id="p"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16"/></clipPath>
  <pattern id="grid" width="6" height="6" patternUnits="userSpaceOnUse">
    <circle cx="3" cy="3" r="1.1" fill="#1B2B4D"/>
  </pattern>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#05070E"/><stop offset="1" stop-color="#0A1024"/>
  </linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#22D3EE" stop-opacity="0"/>
    <stop offset="0.5" stop-color="#22D3EE" stop-opacity="0.30"/>
    <stop offset="1" stop-color="#22D3EE" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8B5CF6"/><stop offset="0.55" stop-color="#22D3EE"/><stop offset="1" stop-color="#8B5CF6"/>
  </linearGradient>
</defs>
<g clip-path="url(#p)">
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
  <g>
    {groups}
    
  </g>
  <rect x="0" y="-70" width="{W}" height="70" fill="url(#scan)">
    <animate attributeName="y" values="-70;{H}" dur="5.5s" begin="1s" repeatCount="indefinite"/>
  </rect>
  <g stroke="#22D3EE" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.85">
    <path d="M14 42 V20 Q14 14 20 14 H42"/>
    <path d="M{W - 14} {H - 42} V{H - 20} Q{W - 14} {H - 14} {W - 20} {H - 14} H{W - 42}"/>
    <animate attributeName="opacity" values="0.35;0.95;0.35" dur="3s" repeatCount="indefinite"/>
  </g>
</g>
<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="16" fill="none" stroke="url(#edge)" stroke-width="2" opacity="0.8"/>
</svg>'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("dots:", n_dots, "size:", W, "x", H, "bytes:", len(svg))
