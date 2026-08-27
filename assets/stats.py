"""Build stats-card.svg — a self-hosted replacement for the third-party
GitHub stats / streak / activity-graph / trophy images.

Everything is fetched from free, no-auth endpoints and baked into one SVG that
lives in this repo, so no external service can rate-limit it or go 402 on you.

  numbers + languages : api.github.com
  contribution graph  : github-contributions-api.jogruber.de

Run:  python stats.py            (needs network; falls back to the cache)
      python stats.py --offline  (cache only, no network)

Language bytes are cached in stats-cache.json because the unauthenticated API
allows only 60 calls an hour; each run tops the cache up with whatever budget
is left, so a couple of runs fills it in completely.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stats-card.svg")
CACHE = os.path.join(HERE, "stats-cache.json")
USER = "abin0x"
OFFLINE = "--offline" in sys.argv

# ── theme (matches neofetch-card.svg) ─────────────────────────────────────
PAGE, PANEL, BORDER = "#0D1117", "#161B22", "#232A34"
LABEL, VALUE, MUTED = "#79C0FF", "#E6EDF3", "#7D8791"
GREEN, ORANGE, PURPLE, CYAN = "#3FB950", "#F0883E", "#BC8CFF", "#22D3EE"
RULE = "#39414D"
HEAT = ["#1B2230", "#0E4B5C", "#127D96", "#19A9C7", "#22D3EE"]
MONO = ("'JetBrains Mono','Fira Code','DejaVu Sans Mono',Consolas,"
        "'Courier New',monospace")

LANG_COLOURS = {
    "Python": "#3572A5", "HTML": "#E34C26", "CSS": "#563D7C", "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6", "Java": "#B07219", "C": "#555555", "C++": "#F34B7D",
    "Go": "#00ADD8", "Shell": "#89E051", "PHP": "#4F5D95", "Dart": "#00B4AB",
    "Jupyter Notebook": "#DA5B0B", "SCSS": "#C6538C", "Vue": "#41B883",
}


def api(url, headers=None):
    h = {"User-Agent": "readme-builder"}
    # Optional: set GITHUB_TOKEN to lift the API ceiling from 60 to 5000 an
    # hour, which fills the language cache in a single run.
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = "Bearer " + token
    h.update(headers or {})
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers=h), timeout=30))


def load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        return {"repo_langs": {}, "data": {}}


cache = load_cache()
data = dict(cache.get("data", {}))


def collect():
    """Refresh everything we can; anything that fails keeps its cached value."""
    budget = [60]
    try:
        budget[0] = api("https://api.github.com/rate_limit")["resources"]["core"]["remaining"]
    except Exception:
        pass

    def spend(url, headers=None):
        if budget[0] <= 2:
            raise RuntimeError("rate limit budget exhausted")
        budget[0] -= 1
        return api(url, headers)

    # Every block stands on its own: if the core quota (60/hour, unauthenticated)
    # runs dry, the rest of the card still refreshes from the other endpoints.
    repos = []
    try:
        u = spend("https://api.github.com/users/%s" % USER)
        data.update(name=u.get("name") or USER, repos=u["public_repos"],
                    followers=u["followers"], following=u["following"],
                    created=u["created_at"])

        stars, primary, page = 0, {}, 1
        while True:
            batch = spend("https://api.github.com/users/%s/repos?per_page=100&page=%d"
                          % (USER, page))
            for r in batch:
                stars += r["stargazers_count"]
                repos.append((r["name"], r["languages_url"], r["pushed_at"]))
                if r["language"]:
                    primary[r["language"]] = primary.get(r["language"], 0) + 1
            if len(batch) < 100:
                break
            page += 1
        data["stars"] = stars
        data["primary"] = primary
    except Exception as exc:
        print("   ! profile/repos not refreshed (%s)" % exc)

    # the search API has its own quota, so it never competes with the calls above
    try:
        r = api("https://api.github.com/search/commits?q=author:%s&per_page=1" % USER,
                {"Accept": "application/vnd.github.cloak-preview+json"})
        data["commits"] = r["total_count"]
    except Exception as exc:
        print("   ! commit count unavailable (%s)" % exc)

    # byte-weighted languages, topped up a few repos at a time
    known = cache.get("repo_langs", {})
    fresh = 0
    for name, url, pushed in repos:
        entry = known.get(name)
        if entry and entry.get("pushed_at") == pushed:
            continue
        try:
            known[name] = {"pushed_at": pushed, "langs": spend(url)}
            fresh += 1
        except Exception:
            break
    cache["repo_langs"] = known
    if repos:
        print("   language cache: %d/%d repos (%d new this run)"
              % (len(known), len(repos), fresh))

    try:
        cal = api("https://github-contributions-api.jogruber.de/v4/%s?y=last" % USER)
        data["days"] = [(d["date"], d["count"]) for d in cal["contributions"]]
        data["year_total"] = cal["total"].get("lastYear", sum(c for _, c in data["days"]))
    except Exception as exc:
        print("   ! contribution graph not refreshed (%s)" % exc)


if not OFFLINE:
    try:
        collect()
    except Exception as exc:
        print("! live fetch failed (%s) - using cached numbers" % exc)

if not data.get("days"):
    raise SystemExit("no data yet: run once with a network connection")

cache["data"] = data
cache["updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
json.dump(cache, open(CACHE, "w", encoding="utf-8"), indent=1)

# ── derived numbers ───────────────────────────────────────────────────────
days = [(datetime.date.fromisoformat(d), c) for d, c in data["days"]]
days = [(d, c) for d, c in days if d <= datetime.date.today()]

current = 0
for d, c in reversed(days):
    if c > 0:
        current += 1
    elif d != datetime.date.today():      # today not counted as a break yet
        break
longest = run = 0
for _, c in days:
    run = run + 1 if c > 0 else 0
    longest = max(longest, run)
active = sum(1 for _, c in days if c > 0)

# Languages: every repo counts once, split by the share of bytes inside that
# repo. Summing raw bytes instead would let a single large repo swallow the
# chart (one vendored bundle and you are "95% TypeScript").
totals = {}
for entry in cache["repo_langs"].values():
    langs = entry.get("langs", {})
    repo_bytes = sum(langs.values())
    if not repo_bytes:
        continue
    for k, v in langs.items():
        totals[k] = totals.get(k, 0) + v / repo_bytes
if not totals:
    totals = {k: float(v) for k, v in data.get("primary", {}).items()}
top = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
grand = sum(totals.values()) or 1

start = datetime.datetime.strptime(data["created"], "%Y-%m-%dT%H:%M:%SZ").date()
years = (datetime.date.today() - start).days / 365.25

TILES = [
    ("%s" % format(data["year_total"], ","), "CONTRIBUTIONS", "past year", CYAN),
    ("%s" % format(data.get("commits", 0), ","), "TOTAL COMMITS", "all time", GREEN),
    ("%d" % data["repos"], "PUBLIC REPOS", "%.1f yrs on GitHub" % years, PURPLE),
    ("%d" % data["stars"], "STARS EARNED", "across all repos", ORANGE),
    ("%d" % current, "CURRENT STREAK", "days in a row", CYAN),
    ("%d" % longest, "LONGEST STREAK", "personal best", GREEN),
    ("%d" % active, "ACTIVE DAYS", "of last 365", PURPLE),
    ("%d" % data["followers"], "FOLLOWERS", "%d following" % data["following"], ORANGE),
]

# ── geometry ──────────────────────────────────────────────────────────────
PAD = 22
W = 1200
X0 = PAD + 34                               # content left edge
LEGEND_W = 150
weeks = (len(days) + days[0][0].weekday() + 6) // 7
CELL = (W - PAD - 34 - X0 - LEGEND_W) / weeks   # heat map fills the card width
GAP = max(2.6, CELL * 0.2)
heat_w = weeks * CELL
TILE_W, TILE_H, TILE_GAP = 138, 74, 12
head_y = 62
tiles_y = head_y + 26
lang_x = X0 + TILE_W * 4 + TILE_GAP * 3 + 46
heat_y = tiles_y + TILE_H * 2 + TILE_GAP + 76
H = heat_y + 7 * CELL + 54

parts = []


def reveal(delay, dur=0.4):
    return ('<set attributeName="opacity" to="0" begin="0s"/>'
            '<animate attributeName="opacity" values="0;1" dur="%.2fs" begin="%.2fs" '
            'fill="freeze"/>' % (dur, delay))


# header
parts.append(
    '<g>%s<text x="%d" y="%d" fill="%s" font-weight="700" font-size="15">%s@github</text>'
    '<text x="%d" y="%d" fill="%s" font-size="15"> :: statistics</text>'
    '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.4" stroke-dasharray="7 5"/></g>'
    % (reveal(0.0), X0, head_y, GREEN, USER, X0 + 108, head_y, MUTED,
       X0 + 240, head_y - 5, W - PAD - 34, head_y - 5, RULE))

# metric tiles
for i, (num, label, sub, colour) in enumerate(TILES):
    col, row = i % 4, i // 4
    x = X0 + col * (TILE_W + TILE_GAP)
    y = tiles_y + row * (TILE_H + TILE_GAP)
    parts.append(
        '<g>%s'
        '<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="#11161F" stroke="%s"/>'
        '<rect x="%d" y="%d" width="3" height="%d" rx="1.5" fill="%s"/>'
        '<text x="%d" y="%d" fill="%s" font-size="27" font-weight="700">%s</text>'
        '<text x="%d" y="%d" fill="%s" font-size="9.5" letter-spacing="1.1">%s</text>'
        '<text x="%d" y="%d" fill="%s" font-size="9.5">%s</text>'
        '</g>'
        % (reveal(0.15 + i * 0.06),
           x, y, TILE_W, TILE_H, BORDER,
           x + 10, y + 14, TILE_H - 28, colour,
           x + 22, y + 33, VALUE, num,
           x + 22, y + 49, colour, label,
           x + 22, y + 63, MUTED, sub))

# language bars
parts.append('<g>%s<text x="%d" y="%d" fill="%s" font-size="12.5" font-weight="700" '
             'letter-spacing="0.6">TOP LANGUAGES</text></g>'
             % (reveal(0.5), lang_x, tiles_y + 14, VALUE))
bar_w = W - PAD - 34 - lang_x
for i, (name, size) in enumerate(top):
    pct = size / grand * 100
    y = tiles_y + 38 + i * 22
    colour = LANG_COLOURS.get(name, CYAN)
    parts.append(
        '<g>%s'
        '<circle cx="%d" cy="%d" r="4" fill="%s"/>'
        '<text x="%d" y="%d" fill="%s" font-size="11.5">%s</text>'
        '<text x="%d" y="%d" fill="%s" font-size="11.5" text-anchor="end">%.1f%%</text>'
        '<rect x="%d" y="%d" width="%d" height="5" rx="2.5" fill="#1B2230"/>'
        '<rect x="%d" y="%d" width="0" height="5" rx="2.5" fill="%s">'
        '<animate attributeName="width" values="0;%.1f" dur="0.9s" begin="%.2fs" fill="freeze"/>'
        '</rect></g>'
        % (reveal(0.55 + i * 0.07),
           lang_x + 5, y - 4, colour,
           lang_x + 16, y, VALUE, name,
           lang_x + bar_w, y, MUTED, pct,
           lang_x + 16, y + 6, int(bar_w - 16),
           lang_x + 16, y + 6, colour, max(3.0, (bar_w - 16) * pct / 100), 0.7 + i * 0.07))

# contribution heat map
parts.append('<g>%s<text x="%d" y="%d" fill="%s" font-size="12.5" font-weight="700" '
             'letter-spacing="0.6">CONTRIBUTIONS</text>'
             '<text x="%d" y="%d" fill="%s" font-size="11">last 12 months</text></g>'
             % (reveal(0.9), X0, heat_y - 22, VALUE, X0 + 132, heat_y - 22, MUTED))

first = days[0][0]
offset = (first.weekday() + 1) % 7          # weeks start on Sunday
months_seen = set()
for i, (d, count) in enumerate(days):
    idx = i + offset
    col, row = idx // 7, idx % 7
    level = 0 if count == 0 else min(4, 1 + (count > 2) + (count > 6) + (count > 12))
    parts.append(
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2.4" fill="%s">'
        '<set attributeName="opacity" to="0" begin="0s"/>'
        '<animate attributeName="opacity" values="0;1" dur="0.35s" begin="%.2fs" fill="freeze"/>'
        '<title>%s: %d contributions</title></rect>'
        % (X0 + col * CELL, heat_y + row * CELL, CELL - GAP, CELL - GAP, HEAT[level],
           1.0 + col * 0.012, d.isoformat(), count))
    if d.day <= 7 and d.month not in months_seen:
        months_seen.add(d.month)
        parts.append('<g>%s<text x="%.1f" y="%.1f" fill="%s" font-size="10">%s</text></g>'
                     % (reveal(1.0 + col * 0.012), X0 + col * CELL, heat_y - 6, MUTED,
                        d.strftime("%b")))

legend_x = X0 + heat_w + 24
parts.append('<g>%s<text x="%.1f" y="%.1f" fill="%s" font-size="10">Less</text></g>'
             % (reveal(1.6), legend_x, heat_y + 4 * CELL, MUTED))
for i, colour in enumerate(HEAT):
    parts.append('<g>%s<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2.4" fill="%s"/></g>'
                 % (reveal(1.65 + i * 0.04), legend_x + 34 + i * CELL, heat_y + 4 * CELL - 9,
                    CELL - GAP, CELL - GAP, colour))
parts.append('<g>%s<text x="%.1f" y="%.1f" fill="%s" font-size="10">More</text></g>'
             % (reveal(1.85), legend_x + 34 + 5 * CELL + 4, heat_y + 4 * CELL, MUTED))

stamp = "updated %s" % datetime.date.today().isoformat()
parts.append('<g>%s<text x="%d" y="%.1f" fill="%s" font-size="9.5" text-anchor="end">%s</text></g>'
             % (reveal(1.9), W - PAD - 34, H - PAD - 14, "#4B5563", stamp))

svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="GitHub statistics for %s">
<title>%s@github :: statistics</title>
<defs>
  <clipPath id="p"><rect x="%d" y="%d" width="%d" height="%d" rx="16"/></clipPath>
  <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#7C3AED" stop-opacity="0"/>
    <stop offset="0.5" stop-color="%s" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#7C3AED" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="%d" height="%d" fill="%s"/>
<g clip-path="url(#p)">
  <rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>
  <rect x="%d" y="%d" width="240" height="2" fill="url(#sweep)">
    <animate attributeName="x" values="%d;%d" dur="7s" repeatCount="indefinite"/>
  </rect>
</g>
<g font-family="%s">%s</g>
<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="16" fill="none" stroke="%s" stroke-width="1.5"/>
</svg>''' % (W, H, W, H, USER, USER,
             PAD, PAD, W - PAD * 2, H - PAD * 2, CYAN,
             W, H, PAGE,
             PAD, PAD, W - PAD * 2, H - PAD * 2, PANEL,
             PAD, PAD, PAD - 240, W - PAD,
             MONO, "".join(parts),
             PAD + 0.75, PAD + 0.75, W - PAD * 2 - 1.5, H - PAD * 2 - 1.5, BORDER)

open(OUT, "w", encoding="utf-8").write(svg)
print("stats-card.svg  %.1f KB | %d contributions, %d commits, %d repos, %d stars"
      % (len(svg) / 1024, data["year_total"], data.get("commits", 0),
         data["repos"], data["stars"]))
print("streaks: current %d, longest %d, active %d/365" % (current, longest, active))
