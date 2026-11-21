"""Build neofetch-card.svg — a neofetch-style profile card.

Left side  : profile-src.png converted to ASCII art.
Right side : neofetch-style rows with dotted leaders, filled from live
             GitHub numbers (fetched from the public API at build time).

Run:  python neofetch.py        (needs Pillow; network for the stats)
Add   --offline                 to reuse the numbers baked in below.
"""
import datetime
from collections import deque
import json
import os
import sys
import urllib.request

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "profile-src.png")
OUT = os.path.join(HERE, "neofetch-card.svg")
USER = "abin0x"

# ── theme ─────────────────────────────────────────────────────────────────
PAGE = "#0D1117"
PANEL = "#161B22"
BORDER = "#232A34"
ART = "#C9D1D9"
LABEL = "#79C0FF"
VALUE = "#E6EDF3"
LEADER = "#30363D"
RULE = "#39414D"
GREEN = "#3FB950"
ORANGE = "#F0883E"
PURPLE = "#BC8CFF"

FS = 15.0          # right-hand column font size
LH = 22.0          # right-hand line height
ART_FS = 8.0
ART_LH = 9.2
CHAR_W = ART_FS * 0.60

# ── ASCII art ─────────────────────────────────────────────────────────────
# Dark-to-light ramp. The photo is downsampled to a character grid, the studio
# backdrop is dropped, and Floyd-Steinberg dithering gives flat areas texture.
RAMP = " .',:;!|jkr*+=#%@&$8MW"   # sparse -> dense; dark pixels get the dense end
TONES = ["#00000000", "#8B96A3", "#A7B2BE", "#C9D1D9", "#E4EBF1", "#FFFFFF"]
CROP = (60, 0, 390, 330)           # head and shoulders (profile-src.png is the 460x460 GitHub photo)
# The studio backdrop is a smooth neutral near-black. Hair is just as dark but textured and the
# suit is navy, so the backdrop is found by colour + smoothness. HEAD (fractions of the crop:
# centre x, centre y, radius x, radius y) guards the hair above the forehead from leaks.
HEAD = (0.50, 0.29, 0.21, 0.19)
COLS = 110


def ascii_art():
    im = Image.open(SRC).convert("RGB").crop(CROP)
    im = im.filter(ImageFilter.UnsharpMask(radius=3, percent=170, threshold=1))
    rows = max(1, round(COLS * im.height / im.width * (CHAR_W / ART_LH)))
    sm = im.resize((COLS, rows), Image.LANCZOS)
    grey = ImageEnhance.Contrast(ImageOps.autocontrast(sm.convert("L"), cutoff=1)).enhance(1.15)

    # Find the backdrop at full resolution: flood in from the borders through
    # dark, neutral, smooth pixels (hair has strands, the suit is blue), then
    # shrink that mask to the character grid.
    raw = Image.open(SRC).convert("RGB").crop(CROP)    # unsharpened: sharpening lifts backdrop noise
    W0, H0 = raw.size
    rgb = raw.load()
    edge = raw.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.BoxBlur(5)).load()
    hx, hy, hrx, hry = HEAD

    def backdrop_like(x, y):
        if ((x / W0 - hx) / hrx) ** 2 + ((y / H0 - hy) / hry) ** 2 < 1:
            return False
        r, g, b = rgb[x, y]
        # the edge filter misreads the outermost pixels, so trust colour alone there
        smooth = edge[x, y] < 9 or not (6 <= x < W0 - 6 and 6 <= y < H0 - 6)
        return (r + g + b) / 3 < 48 and b - max(r, g) < 12 and smooth

    full = Image.new("L", (W0, H0), 0)
    fm = full.load()
    queue = deque()
    for x in range(W0):
        for y in (0, H0 - 1):
            if fm[x, y] == 0 and backdrop_like(x, y):
                fm[x, y] = 255
                queue.append((x, y))
    for y in range(H0):
        for x in (0, W0 - 1):
            if fm[x, y] == 0 and backdrop_like(x, y):
                fm[x, y] = 255
                queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W0 and 0 <= ny < H0 and fm[nx, ny] == 0 and backdrop_like(nx, ny):
                fm[nx, ny] = 255
                queue.append((nx, ny))
    small_mask = full.resize((COLS, rows), Image.BOX)
    bg = [[small_mask.getpixel((x, y)) > 140 for x in range(COLS)] for y in range(rows)]

    # de-speckle: lone cells the flood fill could not reach are backdrop too
    for threshold in (4, 3, 3):
        for y in range(rows):
            for x in range(COLS):
                if bg[y][x]:
                    continue
                near = sum(1 for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                           if not (0 <= nx < COLS and 0 <= ny < rows) or bg[ny][nx])
                if near >= threshold:
                    bg[y][x] = True

    # colour comes from the photo, lifted so it reads on a dark terminal
    tint = ImageEnhance.Color(sm).enhance(1.7)
    tint = ImageEnhance.Brightness(tint).enhance(1.25)
    tint = tint.quantize(colors=14, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")

    val = [[grey.getpixel((x, y)) / 255.0 for x in range(COLS)] for y in range(rows)]
    n = len(RAMP) - 1
    out = []
    for y in range(rows):
        line = []                       # (char, colour) per cell
        for x in range(COLS):
            if bg[y][x]:
                line.append((" ", None))
                continue
            v = min(1.0, max(0.0, val[y][x])) ** 0.62   # lift midtones so the face fills in
            q = round(v * n)
            err = (v - q / n) * 0.55
            for dx, dy, w in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < COLS and 0 <= ny < rows:
                    val[ny][nx] += err * w
            r, g, b = tint.getpixel((x, y))
            floor = 62                  # never let a glyph sink into the panel
            colour = "#%02x%02x%02x" % (max(r, floor), max(g, floor), max(b, floor))
            line.append((RAMP[q], colour))
        out.append(line)
    while out and not any(c != " " for c, _ in out[0]):
        out.pop(0)
    while out and not any(c != " " for c, _ in out[-1]):
        out.pop()
    return out


# ── live GitHub numbers ───────────────────────────────────────────────────
FALLBACK = {"repos": 81, "stars": 10, "followers": 13, "following": 13,
            "created": "2021-05-07T05:47:57Z",
            "langs": [("HTML", 29), ("Python", 21), ("JavaScript", 7), ("CSS", 6)]}


def fetch():
    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "readme-builder"})
        return json.load(urllib.request.urlopen(req, timeout=25))

    u = get("https://api.github.com/users/%s" % USER)
    stars, langs, page = 0, {}, 1
    while True:
        batch = get("https://api.github.com/users/%s/repos?per_page=100&page=%d" % (USER, page))
        for r in batch:
            stars += r["stargazers_count"]
            if r["language"]:
                langs[r["language"]] = langs.get(r["language"], 0) + 1
        if len(batch) < 100:
            break
        page += 1
    return {"repos": u["public_repos"], "stars": stars, "followers": u["followers"],
            "following": u["following"], "created": u["created_at"],
            "langs": sorted(langs.items(), key=lambda kv: -kv[1])[:4]}


gh = FALLBACK
if "--offline" not in sys.argv:
    try:
        gh = fetch()
    except Exception as exc:                      # keep the build working offline
        print("! GitHub API unavailable (%s) - using baked-in numbers" % exc)

start = datetime.datetime.strptime(gh["created"], "%Y-%m-%dT%H:%M:%SZ")
now = datetime.datetime.utcnow()
years = now.year - start.year - ((now.month, now.day) < (start.month, start.day))
months = (now.month - start.month) % 12 - (1 if now.day < start.day else 0)
days = (now - start.replace(year=now.year if (now.month, now.day) >= (start.month, start.day)
                            else now.year - 1)).days % 30
uptime = "%d years, %d months, %d days" % (years, max(months, 0), days)
top_langs = ", ".join("%s %d" % (n, c) for n, c in gh["langs"][:3])

# ── rows: (label, value, value-colour) | ("", "", "") is a blank line ─────
#          ("§", "Section name", "") starts a new section header
ROWS = [
    ("OS", "Windows 11, Ubuntu Linux", VALUE),
    ("Uptime", uptime, VALUE),
    ("Role", "Software Engineer", VALUE),
    ("Host", "HSTU, Dinajpur, Bangladesh", VALUE),
    ("Kernel", "Django (Python Web Framework)", VALUE),
    ("IDE", "VS Code, PyCharm", VALUE),
    ("", "", ""),
    ("Languages.Programming", "Python, C, C++, Java, JavaScript", VALUE),
    ("Languages.Computer", "HTML, CSS, SQL, JSON, YAML", VALUE),
    ("Languages.Real", "Bangla, English", VALUE),
    ("", "", ""),
    ("Stack.Backend", "Django, Django REST Framework", VALUE),
    ("Stack.Database", "PostgreSQL, MySQL, MongoDB, SQLite", VALUE),
    ("Stack.AI", "LLM APIs, AI agents, RAG, MCP", VALUE),
    ("Hobbies.Software", "Web Dev, App Dev, AI, Problem Solving", VALUE),
    ("§", "Contact", ""),
    ("Portfolio", "abin0x.netlify.app", PURPLE),
    ("LinkedIn", "abin0x", PURPLE),
    ("GitHub", "abin0x", PURPLE),
    ("X", "abin0x", PURPLE),
    ("Instagram", "abin0x", PURPLE),
    # ("Email", "you@example.com", PURPLE),   <- add your email here if you want it public
    ("§", "GitHub Stats", ""),
    ("Repos", "%d {Stars: %d}" % (gh["repos"], gh["stars"]), GREEN),
    ("Community", "Followers: %d | Following: %d" % (gh["followers"], gh["following"]), GREEN),
    ("Top Languages", top_langs, ORANGE),
]

# ── geometry ──────────────────────────────────────────────────────────────
PAD = 22                                   # page margin around the panel
ART_X = 54
art = ascii_art()
art_w = COLS * CHAR_W
COL_X = ART_X + art_w + 46                 # right column starts here
LABEL_X = COL_X + 18
VAL_X = COL_X + 640
W = VAL_X + 38 + PAD
head_y = 62

n_lines = len(ROWS) + 2
right_h = head_y + n_lines * LH + 54
H = max(right_h, 96 + len(art) * ART_LH + 40)
ART_TOP = (H - len(art) * ART_LH) / 2 + ART_LH   # vertically centred beside the text

# ── build ─────────────────────────────────────────────────────────────────
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


body, y, delay = [], head_y, 0.0
STEP = 0.055

body.append(
    '<g><set attributeName="opacity" to="0" begin="0s"/><text x="%.0f" y="%.0f" fill="%s" font-weight="700">%s@github</text>'
    '<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="1.4" '
    'stroke-dasharray="7 5"/>'
    '<animate attributeName="opacity" values="0;1" dur="0.3s" begin="%.2fs" fill="freeze"/></g>'
    % (COL_X, y, GREEN, USER, COL_X + len(USER + "@github") * FS * 0.62 + 14, y - 5,
       VAL_X + 24, y - 5, RULE, delay))
y += LH * 1.25
delay += 0.22

for label, value, colour in ROWS:
    if label == "":
        y += LH * 0.5
        continue
    if label == "§":
        body.append(
            '<g><set attributeName="opacity" to="0" begin="0s"/><text x="%.0f" y="%.0f" fill="%s">-</text>'
            '<text x="%.0f" y="%.0f" fill="%s" font-weight="700">%s</text>'
            '<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="1.4" '
            'stroke-dasharray="7 5"/>'
            '<animate attributeName="opacity" values="0;1" dur="0.3s" begin="%.2fs" fill="freeze"/></g>'
            % (COL_X, y + LH * 0.55, RULE, LABEL_X, y + LH * 0.55, VALUE, esc(value),
               LABEL_X + len(value) * FS * 0.62 + 14, y + LH * 0.55 - 5,
               VAL_X + 24, y + LH * 0.55 - 5, RULE, delay))
        y += LH * 1.35
        delay += STEP
        continue

    lead_x1 = LABEL_X + (len(label) + 1) * FS * 0.62 + 10
    lead_x2 = VAL_X - len(value) * FS * 0.62 - 10
    leader = ""
    if lead_x2 - lead_x1 > 12:
        leader = ('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="2" '
                  'stroke-linecap="round" stroke-dasharray="0.5 7"/>'
                  % (lead_x1, y - 4, lead_x2, y - 4, LEADER))
    body.append(
        '<g><set attributeName="opacity" to="0" begin="0s"/>'
        '<text x="%.0f" y="%.0f" fill="%s">.</text>'
        '<text x="%.0f" y="%.0f" fill="%s">%s:</text>'
        '%s'
        '<text x="%.0f" y="%.0f" fill="%s" text-anchor="end">%s</text>'
        '<animate attributeName="opacity" values="0;1" dur="0.28s" begin="%.2fs" fill="freeze"/>'
        '</g>'
        % (COL_X, y, LEADER, LABEL_X, y, LABEL, esc(label), leader,
           VAL_X, y, colour, esc(value), delay))
    y += LH
    delay += STEP

cursor_y = y + 2
body.append(
    '<g><set attributeName="opacity" to="0" begin="0s"/><text x="%.0f" y="%.0f" fill="%s">%s</text>'
    '<rect x="%.0f" y="%.0f" width="%.0f" height="%.0f" fill="%s">'
    '<animate attributeName="opacity" values="1;1;0;0" dur="1.05s" begin="%.2fs" repeatCount="indefinite"/>'
    '</rect>'
    '<animate attributeName="opacity" values="0;1" dur="0.25s" begin="%.2fs" fill="freeze"/></g>'
    % (COL_X, cursor_y, GREEN, "$", COL_X + FS * 0.85, cursor_y - FS * 0.78,
       FS * 0.58, FS * 1.0, ART, delay + 0.2, delay))

art_lines = []
for i, line in enumerate(art):
    # hard spaces: SVG collapses ordinary runs of whitespace, which would
    # shear the art apart. Runs of equal tone share one tspan.
    spans, run, tone = [], "", ART
    for ch, t in line:
        if ch == " ":
            run += "&#160;"
            continue
        if t != tone and run:
            spans.append('<tspan fill="%s">%s</tspan>' % (tone, run))
            run = ""
        tone = t
        run += esc(ch)
    if run:
        spans.append('<tspan fill="%s">%s</tspan>' % (tone, run))
    line = "".join(spans)
    art_lines.append(
        '<text xml:space="preserve" x="%.0f" y="%.1f">%s<set attributeName="opacity" to="0" begin="0s"/>'
        '<animate attributeName="opacity" values="0;1" dur="0.5s" begin="%.2fs" fill="freeze"/>'
        '</text>' % (ART_X, ART_TOP + i * ART_LH, line, 0.15 + i * 0.035))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" role="img" aria-label="neofetch style profile card for {USER}">
<title>{USER}@github — Mahmudul Hasan Abin</title>
<defs>
  <clipPath id="panel"><rect x="{PAD}" y="{PAD}" width="{W - PAD * 2:.0f}" height="{H - PAD * 2:.0f}" rx="16"/></clipPath>
  <linearGradient id="glow" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7C3AED" stop-opacity="0"/>
    <stop offset="0.5" stop-color="#22D3EE" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#7C3AED" stop-opacity="0"/>
  </linearGradient>
</defs>

<rect width="{W:.0f}" height="{H:.0f}" fill="{PAGE}"/>
<g clip-path="url(#panel)">
  <rect x="{PAD}" y="{PAD}" width="{W - PAD * 2:.0f}" height="{H - PAD * 2:.0f}" fill="{PANEL}"/>
  <rect x="{PAD}" y="{PAD}" width="240" height="2" fill="url(#glow)">
    <animate attributeName="x" values="{PAD - 240};{W - PAD:.0f}" dur="7s" repeatCount="indefinite"/>
  </rect>
</g>

<g font-family="'JetBrains Mono','Fira Code','DejaVu Sans Mono',Consolas,'Courier New',monospace" xml:space="preserve">
  <g font-size="{ART_FS}" fill="{ART}">
    {"".join(art_lines)}
  </g>
  <g font-size="{FS}">
    {"".join(body)}
  </g>
</g>

<rect x="{PAD + 0.75}" y="{PAD + 0.75}" width="{W - PAD * 2 - 1.5:.0f}" height="{H - PAD * 2 - 1.5:.0f}" rx="16" fill="none" stroke="{BORDER}" stroke-width="1.5"/>
</svg>'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("art: %d x %d | card: %.0f x %.0f | %.1f KB | repos %d, stars %d, followers %d"
      % (COLS, len(art), W, H, len(svg) / 1024, gh["repos"], gh["stars"], gh["followers"]))
