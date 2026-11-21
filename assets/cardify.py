"""Build profile-card.svg — an animated profile card for the README.

Reads profile-src.png (and icons.json for the brand glyphs) and writes
profile-card.svg: the photo is embedded as a JPEG *and* as a dot-matrix
layer, and the two cross-fade so the portrait keeps dissolving into dots.

Run:  python cardify.py     (needs Pillow)
"""
import base64
import io
import json
import os

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "profile-src.png")
ICONS = json.load(open(os.path.join(HERE, "icons.json")))
OUT = os.path.join(HERE, "profile-card.svg")

# ── canvas ────────────────────────────────────────────────────────────────
W, H = 1160, 600
INK, BODY = "#0B1120", "#334155"
VIOLET, CYAN = "#7C3AED", "#06B6D4"

NAME = ["Mahmudul Hasan", "Abin"]
BIO = [
    "Hi, I'm Mahmudul Hasan Abin, a Software Engineer and CSE student at",
    "Hajee Mohammad Danesh Science and Technology University, Dinajpur.",
    "I build web applications and backends with Python, Django and Django",
    "REST Framework, with a strong base in C, C++ and DSA. Right now I am",
    "exploring AI and agentic development: LLM APIs, AI agents, RAG and",
    "MCP. I love writing clean code and learning something new every day.",
]
SOCIALS = [
    ("instagram", "abin0x"),
    ("linkedin", "abin0x"),
    ("x", "abin0x"),
    ("github", "abin0x"),
]

PAD_L = 84
BIO_TOP = 300           # first bio baseline
BIO_LH = 28             # bio line height
BIO_FS = 18.5
CHAR_W = 9.05           # rough advance width, used for reveal timing
CX, CY, R = 900, 300, 142   # portrait circle

# ── portrait: embedded JPEG + matching dot-matrix layer ───────────────────
CROP = (40, 0, 420, 380)   # profile-src.png is the 460x460 GitHub photo
photo = Image.open(SRC).convert("RGB").crop(CROP).resize((420, 420), Image.LANCZOS)
buf = io.BytesIO()
photo.save(buf, "JPEG", quality=82, optimize=True)
photo_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

CELL = 5.0
COLS = 64
src = Image.open(SRC).convert("RGB").crop(CROP)
src = src.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
small = src.resize((COLS, COLS), Image.LANCZOS)
small = ImageEnhance.Color(small).enhance(1.30)
small = ImageEnhance.Contrast(small).enhance(1.18)
lum = ImageOps.autocontrast(small.convert("L"), cutoff=1)
small = small.quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")

span = COLS * CELL                      # dot field is span x span, centred on the circle
x0, y0 = CX - span / 2, CY - span / 2
buckets = {}
for gy in range(COLS):
    for gx in range(COLS):
        r, g, b = small.getpixel((gx, gy))
        l = lum.getpixel((gx, gy)) / 255.0
        rad = (CELL * 0.54) * (l ** 0.55)
        if rad < 0.35:
            continue
        cx = x0 + gx * CELL + CELL / 2
        cy = y0 + gy * CELL + CELL / 2
        if ((cx - CX) ** 2 + (cy - CY) ** 2) ** 0.5 > R - 2:
            continue
        key = "#%02x%02x%02x" % (r, g, b)
        buckets.setdefault(key, []).append(
            '<circle cx="%.1f" cy="%.1f" r="%.1f"/>' % (cx, cy, rad))
dot_layer = "".join('<g fill="%s">%s</g>' % (c, "".join(v)) for c, v in buckets.items())
n_dots = sum(len(v) for v in buckets.values())

# ── text blocks ───────────────────────────────────────────────────────────
bio_text = "".join(
    '<text x="%d" y="%d">%s</text>' % (PAD_L, BIO_TOP + i * BIO_LH, line)
    for i, line in enumerate(BIO))

# one mask, one rect per line: each line wipes in like it is being typed
bio_mask_rects = []
t = 1.05
for i, line in enumerate(BIO):
    width = len(line) * CHAR_W + 12
    dur = max(0.34, len(line) * 0.0085)
    bio_mask_rects.append(
        '<rect x="%d" y="%d" width="0" height="%d" fill="#fff">'
        '<animate attributeName="width" values="0;%.0f" dur="%.2fs" begin="%.2fs" fill="freeze"/>'
        '</rect>' % (PAD_L - 4, BIO_TOP + i * BIO_LH - 19, BIO_LH - 2, width, dur, t))
    t += dur * 0.86
bio_mask = "".join(bio_mask_rects)
socials_begin = t + 0.5

# ── social row, centred as a group ────────────────────────────────────────
ICON, GAP, ITEM_GAP, LABEL_FS = 21, 9, 34, 16.5
items, total = [], 0
for name, handle in SOCIALS:
    w = ICON + GAP + len(handle) * (LABEL_FS * 0.53)
    items.append((name, handle, w))
    total += w
total += ITEM_GAP * (len(items) - 1)

sx = W / 2 - total / 2
socials = []
for i, (name, handle, w) in enumerate(items):
    scale = ICON / 24.0
    socials.append(
        '<g opacity="0">'
        '<g transform="translate(%.1f,528) scale(%.4f)"><path d="%s" fill="%s"/></g>'
        '<text x="%.1f" y="545" font-size="%.1f" fill="%s">%s</text>'
        '<animate attributeName="opacity" values="0;1" dur="0.45s" begin="%.2fs" fill="freeze"/>'
        '<animateTransform attributeName="transform" type="translate" values="0 12;0 0" '
        'dur="0.5s" begin="%.2fs" fill="freeze"/>'
        '</g>' % (sx, scale, ICONS[name], INK, sx + ICON + GAP, LABEL_FS, INK, handle,
                  socials_begin + i * 0.13, socials_begin + i * 0.13))
    sx += w + ITEM_GAP
socials = "".join(socials)

divider_begin = socials_begin - 0.35
name_w = 680

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Mahmudul Hasan Abin - Software Engineer">
<title>Mahmudul Hasan Abin, Software Engineer</title>
<defs>
  <clipPath id="card"><rect width="{W}" height="{H}" rx="26"/></clipPath>
  <clipPath id="ring"><circle cx="{CX}" cy="{CY}" r="{R}"/></clipPath>

  <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#F4F7F9"/><stop offset="0.55" stop-color="#ECF0F1"/><stop offset="1" stop-color="#E4EAEE"/>
  </linearGradient>
  <pattern id="mesh" width="16" height="16" patternUnits="userSpaceOnUse">
    <circle cx="8" cy="8" r="1" fill="#9FB0BD" fill-opacity="0.38"/>
  </pattern>
  <radialGradient id="blobV"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0.22"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
  <radialGradient id="blobC"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.20"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>

  <!-- name: dark ink with a colour band sweeping through it -->
  <linearGradient id="inkSweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="420" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset="0.34" stop-color="{INK}"/>
    <stop offset="0.46" stop-color="{VIOLET}"/><stop offset="0.56" stop-color="{CYAN}"/>
    <stop offset="0.68" stop-color="{INK}"/><stop offset="1" stop-color="{INK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-460 0;760 0;-460 0" dur="9s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
  <mask id="nameWipe">
    <rect x="{PAD_L - 6}" y="96" width="0" height="150" fill="#fff">
      <animate attributeName="width" values="0;{name_w}" dur="0.85s" begin="0.15s" fill="freeze"/>
    </rect>
  </mask>
  <mask id="bioWipe">{bio_mask}</mask>

  <linearGradient id="ruleGrad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{VIOLET}"/><stop offset="0.5" stop-color="{CYAN}"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="topBar" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{VIOLET}"/><stop offset="0.5" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/>
  </linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset="0.5" stop-color="{CYAN}" stop-opacity="0.45"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="halo"><stop offset="0.62" stop-color="{VIOLET}" stop-opacity="0"/><stop offset="0.86" stop-color="{VIOLET}" stop-opacity="0.26"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
</defs>

<g clip-path="url(#card)" font-family="Poppins, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif">
  <rect width="{W}" height="{H}" fill="url(#paper)"/>
  <rect width="{W}" height="{H}" fill="url(#mesh)"/>

  <!-- drifting ambience -->
  <ellipse cx="240" cy="120" rx="320" ry="240" fill="url(#blobV)">
    <animateTransform attributeName="transform" type="translate" values="0 0;120 60;0 0" dur="19s" repeatCount="indefinite"/>
  </ellipse>
  <ellipse cx="980" cy="520" rx="360" ry="260" fill="url(#blobC)">
    <animateTransform attributeName="transform" type="translate" values="0 0;-140 -70;0 0" dur="23s" repeatCount="indefinite"/>
  </ellipse>

  <!-- top accent bar -->
  <rect x="0" y="0" width="0" height="5" fill="url(#topBar)">
    <animate attributeName="width" values="0;{W}" dur="1.1s" begin="0s" fill="freeze"/>
  </rect>

  <!-- name -->
  <g mask="url(#nameWipe)" font-size="56" font-weight="800" letter-spacing="-0.8" fill="url(#inkSweep)">
    <text x="{PAD_L}" y="150">{NAME[0]}</text>
    <text x="{PAD_L}" y="222">{NAME[1]}</text>
  </g>

  <!-- waving hand -->
  <text x="{PAD_L}" y="{BIO_TOP}" font-size="19" opacity="0">👋
    <animate attributeName="opacity" values="0;1" dur="0.3s" begin="1.0s" fill="freeze"/>
    <animateTransform attributeName="transform" type="rotate" values="0 {PAD_L + 9} {BIO_TOP - 5};16 {PAD_L + 9} {BIO_TOP - 5};-10 {PAD_L + 9} {BIO_TOP - 5};16 {PAD_L + 9} {BIO_TOP - 5};0 {PAD_L + 9} {BIO_TOP - 5}" dur="1.6s" begin="1.2s" repeatCount="indefinite"/>
  </text>

  <!-- bio, typed line by line (indented past the hand) -->
  <g mask="url(#bioWipe)" font-size="{BIO_FS}" fill="{BODY}" transform="translate(30,0)">
    {bio_text}
  </g>

  <!-- divider -->
  <rect x="{PAD_L}" y="482" width="0" height="2.5" rx="1.25" fill="url(#ruleGrad)">
    <animate attributeName="width" values="0;664" dur="0.8s" begin="{divider_begin:.2f}s" fill="freeze"/>
  </rect>

  <!-- socials -->
  <g font-size="{LABEL_FS}" font-weight="600">{socials}</g>

  <!-- portrait -->
  <g opacity="0">
    <animate attributeName="opacity" values="0;1" dur="0.7s" begin="0.35s" fill="freeze"/>

    <circle cx="{CX}" cy="{CY}" r="{R + 26}" fill="url(#halo)">
      <animate attributeName="opacity" values="0.75;1;0.75" dur="4.5s" repeatCount="indefinite"/>
    </circle>

    <g clip-path="url(#ring)">
      <!-- real photo -->
      <g>
        <image x="{CX - R}" y="{CY - R}" width="{R * 2}" height="{R * 2}"
               preserveAspectRatio="xMidYMid slice"
               href="data:image/jpeg;base64,{photo_b64}"
               xlink:href="data:image/jpeg;base64,{photo_b64}"/>
        <animate attributeName="opacity" values="1;1;0;0;1;1" keyTimes="0;0.34;0.44;0.70;0.80;1" dur="13s" begin="1.5s" repeatCount="indefinite"/>
      </g>
      <!-- same portrait, drawn in dots -->
      <g opacity="0">
        <circle cx="{CX}" cy="{CY}" r="{R}" fill="#05070E"/>
        {dot_layer}
        <animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;0.34;0.44;0.70;0.80;1" dur="13s" begin="1.5s" repeatCount="indefinite"/>
      </g>
      <!-- scan sweep -->
      <rect x="{CX - R}" y="{CY - R}" width="{R * 2}" height="54" fill="url(#scan)" opacity="0.9">
        <animate attributeName="y" values="{CY - R - 54};{CY + R}" dur="6.5s" begin="2s" repeatCount="indefinite"/>
      </rect>
    </g>

    <!-- rings -->
    <circle cx="{CX}" cy="{CY}" r="{R + 1}" fill="none" stroke="#FFFFFF" stroke-width="6" opacity="0.9"/>
    <circle cx="{CX}" cy="{CY}" r="{R + 11}" fill="none" stroke="{VIOLET}" stroke-width="1.6" stroke-opacity="0.55" stroke-dasharray="3 9" stroke-linecap="round">
      <animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" to="360 {CX} {CY}" dur="26s" repeatCount="indefinite"/>
    </circle>
    <circle cx="{CX}" cy="{CY}" r="{R + 21}" fill="none" stroke="{CYAN}" stroke-width="1.4" stroke-opacity="0.45" stroke-dasharray="34 210" stroke-linecap="round">
      <animateTransform attributeName="transform" type="rotate" from="360 {CX} {CY}" to="0 {CX} {CY}" dur="14s" repeatCount="indefinite"/>
    </circle>

    <!-- orbiting dots -->
    <g><circle cx="{CX}" cy="{CY - R - 11}" r="4.5" fill="{VIOLET}"/>
      <animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" to="360 {CX} {CY}" dur="9s" repeatCount="indefinite"/></g>
    <g><circle cx="{CX + R + 21}" cy="{CY}" r="3.2" fill="{CYAN}"/>
      <animateTransform attributeName="transform" type="rotate" from="0 {CX} {CY}" to="-360 {CX} {CY}" dur="12s" repeatCount="indefinite"/></g>
    <g><circle cx="{CX}" cy="{CY + R + 21}" r="2.6" fill="{INK}" opacity="0.45"/>
      <animateTransform attributeName="transform" type="rotate" from="120 {CX} {CY}" to="480 {CX} {CY}" dur="17s" repeatCount="indefinite"/></g>
  </g>

  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="26" fill="none" stroke="#CBD5E1" stroke-width="2"/>
</g>
</svg>'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("dots:", n_dots, "| jpeg b64:", len(photo_b64) // 1024, "KB | svg:", len(svg) // 1024, "KB")
