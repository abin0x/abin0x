"""Animated cards for the profile README: hero.svg, now.svg, orbit.svg, footer.svg.

    python assets/animated.py        (needs Pillow; network once for the tech icons)

The photo comes from profile-src.png. Tech icons come from skillicons.dev and are
cached in skillicons.json, so later runs work offline. Everything moves with plain
SVG animation and CSS, which GitHub renders inside <img> tags (no scripts, no web
fonts). The CSS animations stop for visitors who ask for reduced motion; the SMIL
ones (the hero's role ticker, the orbits) keep going, since CSS cannot pause them.
"""
import base64
import io
import json
import math
import os
import random
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "profile-src.png")
ICON_CACHE = os.path.join(HERE, "skillicons.json")

# ── theme (matches the neofetch and stats cards) ─────────────────────────────
BG, PANEL, LINE = "#05070E", "#070B16", "#1B2333"
TEXT, MUTED, DIM = "#E6EDF3", "#8B949E", "#5B6577"
CYAN, SKY, PURPLE, VIOLET = "#22D3EE", "#38BDF8", "#8B5CF6", "#A855F7"
GREEN, AMBER, PINK = "#3FB950", "#F59E0B", "#F472B6"
MONO = "'JetBrains Mono','Fira Code',Consolas,'Courier New',monospace"
SANS = "'Segoe UI',Inter,system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"

# ── content ──────────────────────────────────────────────────────────────────
NAME = "Mahmudul Hasan Abin"
ROLES = ["Software Engineer", "AI Enthusiast", "Researcher", "Builder"]
CHIPS = [("Dinajpur, Bangladesh", CYAN), ("CSE @ HSTU", VIOLET), ("abin0x.netlify.app", SKY)]
MARQUEE = ["PYTHON", "DJANGO", "REST APIs", "POSTGRESQL", "NEXT.JS", "SUPABASE",
           "AI AGENTS", "RAG & MCP", "SYSTEM DESIGN", "PROBLEM SOLVING"]
NOW = [
    ("building", "abin0x.netlify.app  ·  Next.js, Supabase, Tailwind CSS", CYAN),
    ("learning", "System design  ·  LLM APIs & AI agents  ·  RAG & MCP", VIOLET),
    ("exploring", "AI and agentic development, and the future of software engineering", SKY),
    ("open to", "Internships  ·  Freelance projects  ·  Collaboration", GREEN),
    ("based in", "Dinajpur, Bangladesh  ·  UTC+6", AMBER),
]
# inner ring = core stack, middle = data and UI, outer = languages and tools
ORBITS = [
    (205, 86, 36, 1, 52, CYAN, ["py", "django", "nextjs", "ts", "js"]),
    (360, 158, 56, 0, 48, VIOLET, ["postgres", "supabase", "mysql", "mongodb", "sqlite", "tailwind", "bootstrap"]),
    (530, 236, 84, 1, 44, SKY, ["c", "cpp", "java", "html", "css", "git", "github", "linux",
                                "vscode", "postman", "figma", "netlify", "vercel"]),
]
ORBIT_LEGEND = [("core stack", CYAN), ("data & UI", VIOLET), ("languages & tools", SKY)]

BASE_CSS = """
.mono{font-family:%s}
.sans{font-family:%s}
@keyframes blink{50%%{opacity:0}}
@keyframes pulse{0%%,100%%{opacity:1}50%%{opacity:.28}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes spinBack{to{transform:rotate(-360deg)}}
@keyframes drift{0%%,100%%{transform:translate(0,0)}50%%{transform:translate(70px,26px)}}
@keyframes driftBack{0%%,100%%{transform:translate(0,0)}50%%{transform:translate(-80px,-20px)}}
@keyframes twinkle{0%%,100%%{opacity:.15}50%%{opacity:.9}}
.blink{animation:blink 1.1s steps(1) infinite}
.pulse{animation:pulse 2.4s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" % (MONO, SANS)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def photo_uri(size=320):
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    side = min(w, h)
    im = im.crop(((w - side) // 2, 0, (w - side) // 2 + side, side)).resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def load_icons(names):
    cache = {}
    if os.path.exists(ICON_CACHE):
        with open(ICON_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    for n in names:
        if n not in cache:
            req = urllib.request.Request("https://skillicons.dev/icons?i=%s&theme=dark" % n,
                                         headers={"User-Agent": "Mozilla/5.0 (profile README build)"})
            cache[n] = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    with open(ICON_CACHE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(cache.items())), f, indent=0)
    return {n: "data:image/svg+xml;base64," + base64.b64encode(cache[n].encode()).decode() for n in names}


def svg_doc(w, h, label, defs, css, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            'role="img" aria-label="{label}">\n<title>{label}</title>\n<defs>\n'
            '<clipPath id="win"><rect x="1" y="1" width="{w2}" height="{h2}" rx="20"/></clipPath>\n'
            '<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse">'
            '<circle cx="4.5" cy="4.5" r="1.1" fill="#16203A"/></pattern>\n'
            '{defs}\n</defs>\n<style>{css}</style>\n'
            '<g clip-path="url(#win)">\n{body}\n</g>\n'
            '<rect x="1" y="1" width="{w2}" height="{h2}" rx="20" fill="none" stroke="{line}" stroke-width="2"/>\n'
            '</svg>\n').format(w=w, h=h, w2=w - 2, h2=h - 2, label=esc(label), defs=defs,
                               css=BASE_CSS + css, body=body, line=LINE)


def backdrop(w, h):
    return ('<rect width="{w}" height="{h}" fill="{bg}"/>'
            '<rect width="{w}" height="{h}" fill="url(#dots)"/>').format(w=w, h=h, bg=BG)


def title_bar(w, title, right=""):
    return ('<rect width="{w}" height="62" fill="{panel}"/>'
            '<line x1="0" y1="62" x2="{w}" y2="62" stroke="{line}" stroke-width="1.5"/>'
            '<circle cx="34" cy="31" r="7" fill="#FF5F56"/><circle cx="58" cy="31" r="7" fill="#FFBD2E"/>'
            '<circle cx="82" cy="31" r="7" fill="#27C93F"/>'
            '<text x="{cx}" y="37" text-anchor="middle" class="mono" font-size="16" fill="{dim}">{t}</text>{right}'
            ).format(w=w, panel=PANEL, line=LINE, cx=w / 2, dim=DIM, t=esc(title), right=right)


def status_pill(w, text, colour):
    est = len(text) * 0.6 * 15
    x_end = w - 34
    return ('<g class="mono" font-size="15"><circle class="pulse" cx="{cx:.0f}" cy="31" r="5" fill="{c}"/>'
            '<text x="{x}" y="36" text-anchor="end" fill="{c}">{t}</text></g>'
            ).format(cx=x_end - est - 14, c=colour, x=x_end, t=esc(text))


def name_gradient(gid, x1, x2, dur=8):
    span = x2 - x1
    return ('<linearGradient id="{id}" gradientUnits="userSpaceOnUse" x1="{a}" y1="0" x2="{b}" y2="0" spreadMethod="reflect">'
            '<stop offset="0" stop-color="{c1}"/><stop offset=".35" stop-color="{c2}"/>'
            '<stop offset=".7" stop-color="{c3}"/><stop offset="1" stop-color="{c1}"/>'
            '<animate attributeName="x1" values="{a};{a2};{a}" dur="{d}s" repeatCount="indefinite"/>'
            '<animate attributeName="x2" values="{b};{b2};{b}" dur="{d}s" repeatCount="indefinite"/>'
            '</linearGradient>').format(id=gid, a=x1, b=x2, a2=x1 + span, b2=x2 + span,
                                        c1=CYAN, c2=SKY, c3=VIOLET, d=dur)


# ── 1. hero ──────────────────────────────────────────────────────────────────
def hero():
    W, H = 1200, 440
    cx, cy, R = 235, 248, 118
    x0 = 445
    defs = [
        name_gradient("nameGrad", x0, x0 + 700),
        '<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/>'
        '<stop offset=".5" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (CYAN, PURPLE, SKY),
        '<linearGradient id="rule" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">'
        '<stop offset="0" stop-color="%s" stop-opacity=".9"/><stop offset=".6" stop-color="%s" stop-opacity=".5"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>' % (x0, x0 + 700, CYAN, PURPLE, PURPLE),
        '<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>' % (x0, x0 + 120),
        '<radialGradient id="glowA"><stop offset="0" stop-color="%s" stop-opacity=".22"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>' % (CYAN, CYAN),
        '<radialGradient id="glowB"><stop offset="0" stop-color="%s" stop-opacity=".26"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>' % (PURPLE, PURPLE),
        '<clipPath id="face"><circle cx="%d" cy="%d" r="%d"/></clipPath>' % (cx, cy, R),
        '<clipPath id="who"><rect x="%d" y="100" width="0" height="40">'
        '<animate attributeName="width" from="0" to="230" begin=".3s" dur=".9s" fill="freeze"/></rect></clipPath>' % (x0 - 4),
    ]
    css = """
.ring1{transform-origin:%(cx)dpx %(cy)dpx;animation:spin 14s linear infinite}
.ring2{transform-origin:%(cx)dpx %(cy)dpx;animation:spinBack 40s linear infinite}
.glowA{animation:drift 16s ease-in-out infinite}
.glowB{animation:driftBack 19s ease-in-out infinite}
.name{animation:rise .8s .7s both}
.ruleIn{animation:fade .8s 1.1s both}
.shine{animation:shine 4.5s 1.6s ease-in-out infinite both}
@keyframes shine{0%%{transform:translateX(0);opacity:0}15%%{opacity:1}85%%{opacity:1}100%%{transform:translateX(580px);opacity:0}}
.chip{animation:rise .6s both}
.marquee{animation:marquee 48s linear infinite}
@keyframes marquee{to{transform:translateX(-%(loop)dpx)}}
""" % {"cx": cx, "cy": cy, "loop": 190 * len(MARQUEE)}

    b = [backdrop(W, H)]
    b.append('<circle class="glowA" cx="210" cy="150" r="300" fill="url(#glowA)"/>')
    b.append('<circle class="glowB" cx="1010" cy="380" r="340" fill="url(#glowB)"/>')
    b.append(title_bar(W, "abin0x@github: ~", status_pill(W, "open to internships & freelance", GREEN)))

    # portrait with rings, a sonar pulse and an online dot
    b.append('<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="2" opacity="0">'
             '<animate attributeName="r" values="{r};{r2}" dur="3.2s" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values=".5;0" dur="3.2s" repeatCount="indefinite"/></circle>'
             .format(cx=cx, cy=cy, r=R, r2=R + 62, c=CYAN))
    b.append('<g class="ring2"><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#334155" stroke-width="2" '
             'stroke-dasharray="2 10" stroke-linecap="round"/></g>'.format(cx=cx, cy=cy, r=R + 30))
    b.append('<g class="ring1"><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#ring)" stroke-width="4" '
             'stroke-dasharray="170 34 46 34" stroke-linecap="round"/>'
             '<circle cx="{dx}" cy="{cy}" r="6.5" fill="{c}"/></g>'.format(cx=cx, cy=cy, r=R + 15, dx=cx + R + 15, c=CYAN))
    b.append('<circle cx="{cx}" cy="{cy}" r="{r}" fill="#0B1020"/>'
             '<image href="{img}" x="{x}" y="{y}" width="{s}" height="{s}" clip-path="url(#face)" '
             'preserveAspectRatio="xMidYMid slice"/>'.format(cx=cx, cy=cy, r=R, img=photo_uri(),
                                                              x=cx - R, y=cy - R, s=2 * R))
    ox, oy = cx + int(R * 0.71), cy + int(R * 0.71)
    b.append('<circle cx="{x}" cy="{y}" r="13" fill="{g}" opacity="0">'
             '<animate attributeName="r" values="13;26" dur="2s" repeatCount="indefinite"/>'
             '<animate attributeName="opacity" values=".6;0" dur="2s" repeatCount="indefinite"/></circle>'
             '<circle cx="{x}" cy="{y}" r="13" fill="{g}" stroke="{bg}" stroke-width="5"/>'
             .format(x=ox, y=oy, g=GREEN, bg=BG))

    # right column: whoami, name, rule, cycling roles, chips
    b.append('<g clip-path="url(#who)" class="mono" font-size="22"><text x="{x}" y="128">'
             '<tspan fill="{p}">$</tspan><tspan fill="{c}"> whoami</tspan></text></g>'
             '<rect class="blink" x="{cx}" y="110" width="12" height="24" fill="{c}" opacity=".85"/>'
             .format(x=x0, p=VIOLET, c=CYAN, cx=x0 + 120))
    b.append('<text class="sans name" x="{x}" y="206" font-size="58" font-weight="800" fill="url(#nameGrad)" '
             'letter-spacing=".5">{n}</text>'.format(x=x0, n=esc(NAME)))
    b.append('<g class="ruleIn"><line x1="{x}" y1="230" x2="{x2}" y2="230" stroke="url(#rule)" stroke-width="2"/>'
             '<line class="shine" x1="{x}" y1="230" x2="{xs}" y2="230" stroke="url(#shine)" stroke-width="3" '
             'stroke-linecap="round"/></g>'.format(x=x0, x2=x0 + 700, xs=x0 + 120))
    b.append('<text class="sans" x="{x}" y="290" font-size="32" font-weight="600" fill="{p}">›</text>'.format(x=x0, p=VIOLET))
    # each role slides up, holds about 2 s, then leaves; one full cycle is len(ROLES) * 2.5 s
    cycle = 2.5 * len(ROLES)
    for i, role in enumerate(ROLES):
        b.append('<g opacity="0"><animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.05;.22;.27;1" '
                 'dur="{d}s" begin="{s:.1f}s" repeatCount="indefinite"/>'
                 '<animateTransform attributeName="transform" type="translate" values="0 22;0 0;0 0;0 -22;0 -22" '
                 'keyTimes="0;.05;.22;.27;1" dur="{d}s" begin="{s:.1f}s" repeatCount="indefinite"/>'
                 '<text class="sans" x="{x}" y="290" font-size="32" font-weight="600" fill="{t}">{r}</text></g>'
                 .format(d=cycle, s=1.3 + i * 2.5, x=x0 + 30, t=TEXT, r=esc(role)))
    x = x0
    for i, (label, colour) in enumerate(CHIPS):
        w = len(label) * 9.4 + 50
        b.append('<g class="chip" style="animation-delay:{d:.2f}s">'
                 '<rect x="{x:.0f}" y="322" width="{w:.0f}" height="40" rx="20" fill="#0B1222" stroke="{line}" stroke-width="1.5"/>'
                 '<circle cx="{dx:.0f}" cy="342" r="5" fill="{c}"/>'
                 '<text class="sans" x="{tx:.0f}" y="348" font-size="17" fill="{t}">{l}</text></g>'
                 .format(d=1.5 + i * 0.15, x=x, w=w, line=LINE, dx=x + 22, c=colour, tx=x + 36, t=TEXT, l=esc(label)))
        x += w + 14

    # keyword marquee along the bottom edge
    slot = 190
    items = []
    for k, word in enumerate(MARQUEE * 2):
        sx = k * slot
        items.append('<text x="{sx}" y="{y}" fill="{c}" opacity=".75">✦</text>'
                     '<text x="{tx}" y="{y}" text-anchor="middle" fill="{d}" letter-spacing="2">{w}</text>'
                     .format(sx=sx, tx=sx + slot / 2 + 6, y=H - 17, c=CYAN, d=DIM, w=esc(word)))
    b.append('<rect x="0" y="{y}" width="{w}" height="46" fill="{p}"/>'
             '<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{l}" stroke-width="1.5"/>'
             '<g class="mono marquee" font-size="14">{items}</g>'
             .format(y=H - 46, w=W, p=PANEL, l=LINE, items="".join(items)))
    return svg_doc(W, H, "Mahmudul Hasan Abin, Software Engineer", "\n".join(defs), css, "\n".join(b))


# ── 2. right now ─────────────────────────────────────────────────────────────
def now():
    W, H = 1200, 470
    defs, b = [], [backdrop(W, H)]
    b.append(title_bar(W, "~/now.sh", status_pill(W, "live", GREEN)))
    css = """
.row{animation:fade .4s both}
.end{animation:fade .4s 3.7s both}
"""
    # prompt line types itself out
    defs.append('<clipPath id="cmd"><rect x="44" y="92" width="0" height="40">'
                '<animate attributeName="width" from="0" to="460" begin=".2s" dur=".8s" fill="freeze"/></rect></clipPath>')
    b.append('<g clip-path="url(#cmd)" class="mono" font-size="20"><text x="50" y="118">'
             '<tspan fill="{g}">$</tspan><tspan fill="{t}"> ./now.sh --live</tspan></text></g>'.format(g=GREEN, t=TEXT))
    for i, (key, value, colour) in enumerate(NOW):
        y = 174 + i * 50
        t0 = 1.0 + i * 0.45
        defs.append('<clipPath id="row{i}"><rect x="40" y="{y}" width="0" height="46">'
                    '<animate attributeName="width" from="0" to="1120" begin="{t:.2f}s" dur=".7s" fill="freeze"/>'
                    '</rect></clipPath>'.format(i=i, y=y - 30, t=t0))
        b.append('<g clip-path="url(#row{i})">'
                 '<circle class="pulse" style="animation-delay:{pd:.1f}s" cx="66" cy="{cy}" r="6" fill="{c}"/>'
                 '<text class="mono" x="88" y="{y}" font-size="19" fill="{m}">{k}</text>'
                 '<text class="mono" x="226" y="{y}" font-size="19" fill="{d}">→</text>'
                 '<text class="sans" x="262" y="{y}" font-size="20" fill="{t}">{v}</text></g>'
                 .format(i=i, pd=i * 0.4, cy=y - 6, c=colour, y=y, m=MUTED, k=esc(key), d=DIM, t=TEXT, v=esc(value)))
    b.append('<g class="end mono" font-size="20"><text x="50" y="432" fill="{g}">$</text>'
             '<rect class="blink" x="72" y="414" width="12" height="23" fill="{t}" opacity=".85"/></g>'.format(g=GREEN, t=TEXT))
    return svg_doc(W, H, "What Mahmudul Hasan Abin is doing right now", "\n".join(defs), css, "\n".join(b))


# ── 3. tech orbit ────────────────────────────────────────────────────────────
def ellipse_path(cx, cy, rx, ry, sweep):
    return "M {a} {cy} A {rx} {ry} 0 1 {s} {b} {cy} A {rx} {ry} 0 1 {s} {a} {cy}".format(
        a=cx + rx, b=cx - rx, cy=cy, rx=rx, ry=ry, s=sweep)


def orbit():
    W, H = 1200, 620
    cx, cy = 600, 341
    icons = load_icons([n for o in ORBITS for n in o[6]])
    defs = [
        '<radialGradient id="core"><stop offset="0" stop-color="#14203A"/><stop offset="1" stop-color="%s"/></radialGradient>' % BG,
        '<radialGradient id="halo"><stop offset="0" stop-color="%s" stop-opacity=".2"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>' % (PURPLE, PURPLE),
        '<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/>'
        '<stop offset="1" stop-color="%s"/></linearGradient>' % (CYAN, PURPLE),
    ]
    b = [backdrop(W, H)]
    b.append('<circle cx="{cx}" cy="{cy}" r="320" fill="url(#halo)"/>'.format(cx=cx, cy=cy))
    b.append(title_bar(W, "tech.orbit()"))
    for rx, ry, dur, sweep, size, colour, names in ORBITS:
        d = ellipse_path(cx, cy, rx, ry, sweep)
        per = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
        tail = 110
        b.append('<path d="{d}" fill="none" stroke="#1E293B" stroke-width="1.5" stroke-dasharray="3 7"/>'.format(d=d))
        b.append('<path d="{d}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round" opacity=".7" '
                 'stroke-dasharray="{t} {g:.1f}"><animate attributeName="stroke-dashoffset" values="0;-{p:.1f}" '
                 'dur="{dd:.1f}s" repeatCount="indefinite"/></path>'
                 .format(d=d, c=colour, t=tail, g=per - tail, p=per, dd=dur / 2.2))
    # core
    for begin in (0, 1.8):
        b.append('<circle cx="{cx}" cy="{cy}" r="64" fill="none" stroke="{c}" stroke-width="2" opacity="0">'
                 '<animate attributeName="r" values="64;128" dur="3.6s" begin="{b}s" repeatCount="indefinite"/>'
                 '<animate attributeName="opacity" values=".45;0" dur="3.6s" begin="{b}s" repeatCount="indefinite"/>'
                 '</circle>'.format(cx=cx, cy=cy, c=CYAN, b=begin))
    b.append('<circle cx="{cx}" cy="{cy}" r="64" fill="url(#core)" stroke="url(#ring)" stroke-width="2.5"/>'
             '<text class="mono" x="{cx}" y="{y1}" text-anchor="middle" font-size="24" font-weight="700" fill="{t}">abin0x</text>'
             '<text class="mono" x="{cx}" y="{y2}" text-anchor="middle" font-size="14" fill="{m}">{{ stack }}</text>'
             .format(cx=cx, cy=cy, y1=cy + 4, y2=cy + 28, t=TEXT, m=MUTED))
    # icons riding the orbits, evenly spaced, always upright
    for rx, ry, dur, sweep, size, colour, names in ORBITS:
        d = ellipse_path(cx, cy, rx, ry, sweep)
        n = len(names)
        for i, name in enumerate(names):
            b.append('<g><image href="{img}" x="{o}" y="{o}" width="{s}" height="{s}"/>'
                     '<animateMotion path="{d}" dur="{dur}s" begin="-{bg:.2f}s" repeatCount="indefinite"/></g>'
                     .format(img=icons[name], o=-size / 2, s=size, d=d, dur=dur, bg=dur * i / n))
    # legend
    x = 40
    for label, colour in ORBIT_LEGEND:
        b.append('<circle cx="{x}" cy="{y}" r="5" fill="{c}"/><text class="mono" x="{tx}" y="{ty}" font-size="14" '
                 'fill="{m}">{l}</text>'.format(x=x, y=H - 30, c=colour, tx=x + 12, ty=H - 25, m=MUTED, l=esc(label)))
        x += len(label) * 8.6 + 40
    return svg_doc(W, H, "Tech stack of Mahmudul Hasan Abin", "\n".join(defs), "", "\n".join(b))


# ── 4. footer ────────────────────────────────────────────────────────────────
def wave(y0, amp, period=300, width=2400, h=240):
    d = ["M 0 %d" % y0]
    x, up = 0, True
    while x < width:
        d.append("Q %d %d %d %d" % (x + period / 4, y0 - amp if up else y0 + amp, x + period / 2, y0))
        x += period // 2
        up = not up
    d.append("L %d %d L 0 %d Z" % (width, h, h))
    return " ".join(d)


def footer():
    W, H = 1200, 240
    defs = [
        name_gradient("nameGrad", 380, 820, 7),
        '<linearGradient id="sea" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1200" y2="0" spreadMethod="reflect">'
        '<stop offset="0" stop-color="%s"/><stop offset=".5" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
        '</linearGradient>' % (PURPLE, CYAN, SKY),
    ]
    css = """
.w1{animation:waveL 22s linear infinite}
.w2{animation:waveR 15s linear infinite}
.w3{animation:waveL 10s linear infinite}
@keyframes waveL{from{transform:translateX(0)}to{transform:translateX(-1200px)}}
@keyframes waveR{from{transform:translateX(-1200px)}to{transform:translateX(0)}}
.star{animation:twinkle 3s ease-in-out infinite}
.title{animation:rise .8s .2s both}
.sub{animation:rise .8s .5s both}
"""
    rnd = random.Random(7)
    b = [backdrop(W, H)]
    for _ in range(34):
        x, y = rnd.uniform(20, W - 20), rnd.uniform(14, 150)
        if 300 < x < 900 and 50 < y < 150:
            continue   # keep the text area clean
        b.append('<circle class="star" style="animation-delay:{d:.1f}s" cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#fff"/>'
                 .format(d=rnd.uniform(0, 3), x=x, y=y, r=rnd.uniform(0.8, 1.8)))
    b.append('<text class="sans title" x="600" y="96" text-anchor="middle" font-size="46" font-weight="800" '
             'fill="url(#nameGrad)">Thanks for visiting!</text>')
    b.append('<text class="mono sub" x="600" y="136" text-anchor="middle" font-size="18" fill="{m}">'
             'Let\'s build something together  ·  abin0x.netlify.app</text>'.format(m=MUTED))
    for cls, y0, amp, op in (("w1", 178, 16, .30), ("w2", 194, 12, .45), ("w3", 210, 9, .85)):
        b.append('<path class="{c}" d="{d}" fill="url(#sea)" opacity="{o}"/>'.format(c=cls, d=wave(y0, amp, h=H), o=op))
    return svg_doc(W, H, "Thanks for visiting", "\n".join(defs), css, "\n".join(b))


if __name__ == "__main__":
    for name, build in (("hero.svg", hero), ("now.svg", now), ("orbit.svg", orbit), ("footer.svg", footer)):
        svg = build()
        with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        print("%-11s %6.1f KB" % (name, len(svg.encode()) / 1024))
