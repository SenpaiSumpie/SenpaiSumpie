"""Generate the artwork used by the profile README.

    pip install fonttools
    python tools/readme-art/gen.py

Writes self-contained SVGs to assets/readme/. GitHub shows README images in a
sandbox that cannot load fonts or scripts, so all lettering is converted to
outlines and all motion is plain CSS inside each file. Every animation stops
when the viewer has reduced motion turned on.

The two typefaces (Unbounded and Instrument Sans, both SIL Open Font License)
are downloaded on first run into tools/readme-art/.fonts, which is not
committed.
"""
import html
import math
import random
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / ".fonts"
OUT = HERE.parents[1] / "assets" / "readme"
FONT_URLS = {
    "Unbounded.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/unbounded/Unbounded%5Bwght%5D.ttf",
    "InstrumentSans.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentsans/InstrumentSans%5Bwdth%2Cwght%5D.ttf",
}

INK = "#0E0A1A"
SURF_TOP = "#231839"
SURF_BOTTOM = "#171028"
WELL = "#130D20"
DUSK = "#2A1740"
RAISED = "#2B1F42"
VIOLET = "#8B6CF0"
PINK = "#F26CA7"
CYAN = "#6FE3E1"
EMBER = "#F7A259"
TEXT = "#F3EDFC"
BODY_INK = "#CFC4E4"
SOFT = "#B3A2D6"
FAINT = "#8777A8"
HAIR = "#3A2A55"

REDUCED = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


class Face:
    def __init__(self, file, **axes):
        path = FONTS / file
        if not path.exists():
            FONTS.mkdir(exist_ok=True)
            urllib.request.urlretrieve(FONT_URLS[file], path)
        self.font = instantiateVariableFont(TTFont(path), axes)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def width(self, text, size, track=0.0):
        s = size / self.upm
        return sum(self.glyphs[self.cmap[ord(c)]].width * s + track for c in text)

    def path(self, text, x, y, size, fill, track=0.0):
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        for c in text:
            g = self.glyphs[self.cmap[ord(c)]]
            g.draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
            x += g.width * s + track
        return f'<path d="{pen.getCommands()}" fill="{fill}"/>'

    def wrap(self, text, size, max_w):
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if self.width(trial, size) > max_w and cur:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + [cur]


DISPLAY = Face("Unbounded.ttf", wght=600)
BODY = Face("InstrumentSans.ttf", wght=450, wdth=100)
BODY_B = Face("InstrumentSans.ttf", wght=600, wdth=100)


def speckle(seed, w, h, count, top=0):
    """A faint scatter of stars so panels share the header's night sky."""
    rng = random.Random(seed)
    return "".join(
        f'<circle cx="{rng.uniform(6, w - 6):.0f}" cy="{rng.uniform(top + 6, h - 6):.0f}" r="{rng.choice([.5, .6, .8])}" fill="#fff" opacity="{rng.uniform(.05, .16):.2f}"/>'
        for _ in range(count)
    )


def panel(w, h, label, css, defs, body, rx=12, stars=None):
    """The shared surface: graded fill, lit top-left edge, faint star texture."""
    texture = speckle(stars, w, h, max(6, w * h // 3600)) if stars is not None else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(label)}">
<style>
{css}
{REDUCED}
</style>
<defs>
<clipPath id="frame"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>
<linearGradient id="surf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{SURF_TOP}"/><stop offset="1" stop-color="{SURF_BOTTOM}"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#C9B8FF" stop-opacity=".55"/><stop offset=".3" stop-color="{HAIR}"/><stop offset="1" stop-color="#1D1430"/></linearGradient>
{defs}</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" fill="url(#surf)"/>
{texture}
{body}
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx - .5}" fill="none" stroke="url(#edge)"/>
</g>
</svg>
"""


def conifers(rng, x0, x1, base, lo, hi, half=3.2, gap=(4, 9)):
    out, x = [], x0
    while x < x1:
        y = base(x) if callable(base) else base
        h = rng.uniform(lo, hi)
        out.append(f"M{x - half:.1f},{y:.1f} L{x:.1f},{y - h:.1f} L{x + half:.1f},{y:.1f} Z")
        x += rng.uniform(*gap)
    return " ".join(out)


# --- header ---------------------------------------------------------------

def ridge(rng, w, base, amp, step=6):
    waves = [(rng.uniform(0.004, 0.02), rng.uniform(0, 6.28), rng.uniform(0.3, 1)) for _ in range(5)]
    total = sum(a for _, _, a in waves)
    return [
        (x, base - amp * sum(a * math.sin(f * x + p) for f, p, a in waves) / total + rng.uniform(-1.2, 1.2))
        for x in range(0, w + step, step)
    ]


def poly(pts, h, fill):
    d = f"M0,{h} " + " ".join(f"L{x},{y:.1f}" for x, y in pts) + f" L{pts[-1][0]},{h} Z"
    return f'<path d="{d}" fill="{fill}"/>'


def y_at(pts, x):
    return min(pts, key=lambda p: abs(p[0] - x))[1]


def header():
    W, H = 846, 300
    rng = random.Random(11)
    far, mid, near = ridge(rng, W, 212, 20, step=4), ridge(rng, W, 240, 24), ridge(rng, W, 274, 10)
    tx = 664
    ty = y_at(mid, tx)
    top = ty - 50

    stars = []
    for i in range(170):
        x, y = rng.uniform(8, W - 8), rng.uniform(8, 190)
        if 30 < x < 560 and 56 < y < 194:
            continue
        r = rng.choice([0.45, 0.55, 0.6, 0.7, 0.9, 1.2])
        tw = f' class="tw" style="animation-duration:{rng.uniform(4, 8):.1f}s;animation-delay:-{rng.uniform(0, 6):.1f}s"' if i % 5 == 0 else ""
        stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rng.uniform(.3, .9):.2f}"{tw}/>')

    mid_trees = conifers(rng, 0, W, lambda x: y_at(mid, x) + 1.5, 3, 9, half=2.1, gap=(3, 8))
    near_trees = conifers(rng, 0, W, lambda x: y_at(near, x) + 2, 7, 24)

    def rings():
        return "".join(f'<circle class="arc" cx="{tx}" cy="{top}" r="96" style="animation-delay:-{d}s"/>' for d in (0, 1.6, 3.2))

    tower = (
        f'<g stroke="#0B0714" stroke-width="1.3" fill="none">'
        f'<path d="M{tx - 6},{ty + 3} L{tx},{top} L{tx + 6},{ty + 3}"/>'
        f'<path d="M{tx - 4.6},{ty - 9} L{tx + 3.2},{ty - 22} M{tx + 4.6},{ty - 9} L{tx - 3.2},{ty - 22} '
        f'M{tx - 3.2},{ty - 22} L{tx + 1.8},{ty - 35} M{tx + 3.2},{ty - 22} L{tx - 1.8},{ty - 35}"/></g>'
        f'<circle cx="{tx}" cy="{top}" r="9" fill="url(#bloom)"/>'
        f'<circle class="beacon" cx="{tx}" cy="{top}" r="2.4" fill="#FFD3E6"/>'
    )
    css = f""".tw{{animation:tw 6s ease-in-out infinite}}
@keyframes tw{{50%{{opacity:.12}}}}
.arc{{fill:none;stroke:{PINK};stroke-width:1.3;vector-effect:non-scaling-stroke;transform-box:fill-box;transform-origin:center;opacity:0;animation:arc 4.8s linear infinite}}
.halo .arc{{stroke-width:5;stroke:#FF8FC0}}
@keyframes arc{{0%{{transform:scale(.04);opacity:.8}}100%{{transform:scale(1);opacity:0}}}}
.beacon{{animation:bk 2.4s ease-in-out infinite}}
@keyframes bk{{50%{{opacity:.3}}}}
.au{{animation:au 22s ease-in-out infinite alternate}}
@keyframes au{{to{{transform:translateX(46px)}}}}
@media (prefers-reduced-motion: reduce){{.arc{{opacity:.3}}.arc:nth-of-type(2){{transform:scale(.66)}}.arc:nth-of-type(3){{transform:scale(.33)}}}}
{REDUCED}"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Max Mosier. Building reliable systems, intelligent tools, and ambitious software. A night sky over mountain ridgelines with a radio tower sending out a signal.">
<style>
{css}
</style>
<defs>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}"/><stop offset=".62" stop-color="{DUSK}"/><stop offset="1" stop-color="#4A2256"/></linearGradient>
<radialGradient id="glow" cx="{tx}" cy="246" r="340" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{EMBER}" stop-opacity=".88"/><stop offset=".22" stop-color="{PINK}" stop-opacity=".52"/><stop offset=".6" stop-color="{VIOLET}" stop-opacity=".13"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
<radialGradient id="bloom"><stop offset="0" stop-color="{PINK}" stop-opacity=".9"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>
<linearGradient id="haze1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#D478A8" stop-opacity="0"/><stop offset="1" stop-color="#D478A8" stop-opacity=".3"/></linearGradient>
<linearGradient id="haze2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5A3478" stop-opacity="0"/><stop offset="1" stop-color="#5A3478" stop-opacity=".55"/></linearGradient>
<linearGradient id="title" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".3"/><stop offset=".4" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity=".03"/></linearGradient>
<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="26"/></filter>
<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3.2"/></filter>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
<g class="au" filter="url(#blur)" opacity=".5"><ellipse cx="250" cy="34" rx="210" ry="20" fill="{VIOLET}"/><ellipse cx="560" cy="60" rx="150" ry="13" fill="{CYAN}" opacity=".35"/></g>
<ellipse cx="250" cy="128" rx="250" ry="58" fill="url(#title)" opacity=".2" filter="url(#blur)"/>
{''.join(stars)}
<rect width="{W}" height="{H}" fill="url(#glow)"/>
{poly(far, H, "#4B2C63")}
<rect y="196" width="{W}" height="52" fill="url(#haze1)"/>
<g class="halo" filter="url(#soft)" opacity=".7">{rings()}</g>
<g>{rings()}</g>
{poly(mid, H, "#27163B")}
<path d="{mid_trees}" fill="#27163B"/>
{tower}
<rect y="232" width="{W}" height="46" fill="url(#haze2)"/>
{poly(near, H, "#120B1E")}
<path d="{near_trees}" fill="#120B1E"/>
{DISPLAY.path("Max Mosier", 46, 116, 56, TEXT, track=-0.6)}
{BODY.path("Building reliable systems, intelligent tools,", 48, 153, 22, "#DDD2F0")}
{BODY.path("and ambitious software.", 48, 181, 22, "#DDD2F0")}
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="13.5" fill="none" stroke="url(#edge)"/>
</g>
</svg>
"""


# --- section headings -------------------------------------------------------

def tab(title):
    W, H = 410, 54
    x0 = 20 + DISPLAY.width(title, 18.5, 0.1) + 16
    x1 = W - 20
    css = f""".run{{animation:run 4.6s linear infinite}}
@keyframes run{{0%{{transform:translateX(0);opacity:0}}12%{{opacity:1}}88%{{opacity:1}}100%{{transform:translateX({x1 - x0 - 30:.0f}px);opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.run{{opacity:0}}}}"""
    defs = f'<linearGradient id="pulse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PINK}" stop-opacity="0"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
    body = (
        DISPLAY.path(title, 20, 33.5, 18.5, TEXT, track=0.1)
        + f'<rect x="{x0:.0f}" y="26.5" width="{x1 - x0:.0f}" height="1" fill="{HAIR}"/>'
        + f'<rect class="run" x="{x0:.0f}" y="26" width="30" height="2" rx="1" fill="url(#pulse)"/>'
        + f'<circle cx="{x1}" cy="27" r="5" fill="{PINK}" opacity=".22"/><circle cx="{x1}" cy="27" r="2.6" fill="{PINK}"/>'
    )
    return panel(W, H, title, css, defs, body, rx=11)


# --- focus tiles ------------------------------------------------------------
# Every icon sits in the same 64px well, uses a 1.5px stroke and one accent.

def glyph_backend(c):
    rows = "".join(
        f'<rect x="33" y="{y}" width="38" height="10" rx="3" fill="{RAISED}" stroke="{c}" stroke-width="1.5"/>'
        f'<circle class="led" cx="40" cy="{y + 5}" r="1.8" style="animation-delay:{i * .45}s"/>'
        f'<rect x="46" y="{y + 4}" width="{w}" height="2" rx="1" fill="{c}" opacity=".35"/>'
        for i, (y, w) in enumerate([(32, 18), (47, 12), (62, 20)])
    )
    css = f".led{{fill:{HAIR};animation:led 3.2s ease-in-out infinite}}@keyframes led{{0%,40%,100%{{fill:{HAIR}}}12%,26%{{fill:{c}}}}}"
    return css, rows


def glyph_fullstack(c):
    def layer(dy, opacity, cls):
        return f'<path class="{cls}" d="M52,{28 + dy} L73,{38 + dy} L52,{48 + dy} L31,{38 + dy} Z" fill="{RAISED}" stroke="{c}" stroke-opacity="{opacity}" stroke-width="1.5" stroke-linejoin="round"/>'
    css = ".l1{animation:fl 4.4s ease-in-out infinite alternate}.l2{animation:fl 4.4s ease-in-out infinite alternate -1.4s}@keyframes fl{to{transform:translateY(-2.6px)}}"
    return css, layer(22, .35, "l3") + layer(11, .65, "l2") + layer(0, 1, "l1")


def glyph_ai(c):
    outer = [(34, 36), (72, 40), (48, 72)]
    lines = "".join(f'<path d="M52,53 L{x},{y}" stroke="{c}" stroke-opacity=".45" stroke-width="1.5"/>' for x, y in outer)
    nodes = "".join(f'<circle class="tool" cx="{x}" cy="{y}" r="4.2" style="animation-delay:{i * .9}s"/>' for i, (x, y) in enumerate(outer))
    css = f".tool{{fill:{RAISED};stroke:{c};stroke-width:1.5;animation:tool 3.6s ease-in-out infinite}}@keyframes tool{{0%,34%,100%{{fill:{RAISED}}}10%,22%{{fill:{c}}}}}.core{{animation:core 3.6s ease-in-out infinite}}@keyframes core{{50%{{opacity:.55}}}}"
    return css, lines + nodes + f'<circle class="core" cx="52" cy="53" r="6.4" fill="{c}"/>'


def glyph_indie(c):
    css = ".go{animation:go 3.4s ease-in-out infinite}@keyframes go{50%{opacity:.35}}"
    art = (
        f'<rect x="31" y="35" width="42" height="34" rx="5" fill="{RAISED}" stroke="{c}" stroke-width="1.5"/>'
        f'<rect x="31" y="43" width="42" height="1.5" fill="{c}" opacity=".45"/>'
        f'<circle cx="36.5" cy="39.4" r="1.3" fill="{c}"/><circle cx="41" cy="39.4" r="1.3" fill="{c}" opacity=".4"/>'
        f'<path class="go" d="M48,49.5 L59,56 L48,62.5 Z" fill="{c}"/>'
    )
    return css, art


def tile(title, text, glyph, accent, seed):
    W, H = 410, 132
    css, art = glyph(accent)
    room = W - 104 - 20
    size = 15.5
    while DISPLAY.width(title, size, 0.1) > room:
        size -= 0.25
    lines = BODY.wrap(text, 14.5, room)
    defs = f'<radialGradient id="tint" cx="52" cy="52" r="46" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{accent}" stop-opacity=".3"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>'
    body = (
        f'<g transform="translate(0,14)"><rect x="20" y="20" width="64" height="64" rx="11" fill="{WELL}"/>'
        f'<rect x="20" y="20" width="64" height="64" rx="11" fill="url(#tint)" stroke="{accent}" stroke-opacity=".4"/>{art}</g>'
        + DISPLAY.path(title, 104, 44, size, TEXT, track=0.1)
        + "".join(BODY.path(l, 104, 70 + i * 21, 14.5, BODY_INK) for i, l in enumerate(lines))
    )
    return panel(W, H, f"{title}: {text}", css, defs, body, stars=seed)


# --- project cards ----------------------------------------------------------
# One system for every project: a metadata strip, a 104px scene under a shared
# tint, then title, one-line descriptor, explanation and a footer link.

STRIP, SCENE = 32, 104


def card(title, category, descriptor, desc, art, status, live=False, link=None, seed=0):
    W, H = 410, 334
    css, defs, scene = art
    top = STRIP + SCENE
    lines = BODY.wrap(desc, 15.5, W - 48)
    assert len(lines) <= 3, (title, lines)
    css = ".dot{animation:dot 2.6s ease-in-out infinite}@keyframes dot{50%{opacity:.3}}\n" + css
    defs += (
        f'<clipPath id="band"><rect width="{W}" height="{SCENE}"/></clipPath>'
        f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".6" stop-color="#1F1533" stop-opacity="0"/><stop offset="1" stop-color="#1F1533" stop-opacity=".92"/></linearGradient>'
    )
    dot = CYAN if live else PINK
    body = (
        f'<rect width="{W}" height="{STRIP}" fill="{WELL}"/>'
        f'<circle cx="26" cy="16" r="6.5" fill="{dot}" opacity=".2"/><circle class="dot" cx="26" cy="16" r="3.4" fill="{dot}"/>'
        + BODY_B.path(status, 39, 20.4, 12.5, TEXT)
        + BODY.path(category, W - 22 - BODY.width(category, 12.5), 20.4, 12.5, FAINT)
        + f'<g transform="translate(0,{STRIP})"><g clip-path="url(#band)">{scene}'
        f'<rect width="{W}" height="{SCENE}" fill="{VIOLET}" opacity=".07"/><rect width="{W}" height="{SCENE}" fill="url(#fade)"/></g></g>'
        f'<rect y="{STRIP - .5}" width="{W}" height="1" fill="#000" opacity=".4"/>'
        + DISPLAY.path(title, 24, top + 40, 23, TEXT, track=0.2)
        + BODY_B.path(descriptor, 24, top + 64, 14.5, SOFT)
        + "".join(BODY.path(l, 24, top + 94 + i * 23, 15.5, BODY_INK) for i, l in enumerate(lines))
    )
    foot = H - 26
    if link:
        body += BODY_B.path(link, 24, foot, 14, CYAN)
    else:
        body += BODY.path("Not public yet", 24, foot, 14, FAINT)
    return panel(W, H, f"{title}, {descriptor}. {status}.", css, defs, body, stars=seed)


def trace_art():
    """Evidence being traced through a graph to a single finding."""
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1" fill="#fff" opacity=".09"/>' for x in range(14, 410, 20) for y in range(12, 104, 20))
    nodes = [(34, 70), (94, 30), (154, 70), (214, 50), (274, 30), (334, 70), (376, 50)]
    side = [((94, 30), (134, 12)), ((154, 70), (194, 88)), ((214, 50), (254, 70)), ((274, 30), (314, 12)), ((334, 70), (294, 88))]
    d = "M" + " L".join(f"{x},{y}" for x, y in nodes)
    branches = "".join(
        f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="{HAIR}" stroke-width="1.4"/><circle cx="{b[0]}" cy="{b[1]}" r="3" fill="{RAISED}" stroke="{HAIR}"/>'
        for a, b in side
    )
    rng = random.Random(3)
    wave = "M0,96 " + " ".join(f"L{x},{96 - rng.uniform(0, 7) * (1 if x % 12 else 1.8):.1f}" for x in range(6, 416, 6))
    n = len(nodes) - 1
    lit = "".join(f'<circle class="nd" cx="{x}" cy="{y}" r="4.2" style="animation-delay:{i / n * 4.2:.2f}s"/>' for i, (x, y) in enumerate(nodes[:-1]))
    ex, ey = nodes[-1]
    css = f""".tr{{stroke-dasharray:100;stroke-dashoffset:100;animation:tr 7s ease-in-out infinite}}
@keyframes tr{{0%{{stroke-dashoffset:100;opacity:1}}60%{{stroke-dashoffset:0;opacity:1}}88%{{stroke-dashoffset:0;opacity:1}}100%{{stroke-dashoffset:0;opacity:0}}}}
.nd{{fill:{RAISED};stroke:{VIOLET};stroke-width:1.4;animation:nd 7s linear infinite}}
@keyframes nd{{0%{{fill:{RAISED}}}4%{{fill:{CYAN}}}82%{{fill:{CYAN}}}100%{{fill:{RAISED}}}}}
.hit{{fill:{RAISED};stroke:{PINK};stroke-width:1.6;animation:hit 7s linear infinite}}
@keyframes hit{{0%,58%{{fill:{RAISED}}}62%,88%{{fill:{PINK}}}100%{{fill:{RAISED}}}}}
.ring{{fill:none;stroke:{PINK};stroke-width:1.4;transform-box:fill-box;transform-origin:center;opacity:0;animation:ring 7s ease-out infinite}}
@keyframes ring{{0%,60%{{transform:scale(.4);opacity:0}}63%{{opacity:.9}}90%,100%{{transform:scale(1.7);opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.tr{{stroke-dashoffset:0}}.nd{{fill:{CYAN}}}.hit{{fill:{PINK}}}}}"""
    defs = (
        f'<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".75" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        '<filter id="lineglow" x="-10%" y="-60%" width="120%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>'
    )
    scene = (
        f'<rect width="410" height="104" fill="{WELL}"/>{dots}'
        f'<path d="{wave}" fill="none" stroke="{VIOLET}" stroke-opacity=".3" stroke-width="1"/>{branches}'
        f'<path d="{d}" fill="none" stroke="{HAIR}" stroke-width="1.6"/>'
        f'<path class="tr" d="{d}" pathLength="100" fill="none" stroke="url(#tg)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" filter="url(#lineglow)" opacity=".8"/>'
        f'<path class="tr" d="{d}" pathLength="100" fill="none" stroke="url(#tg)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>{lit}'
        f'<circle class="ring" cx="{ex}" cy="{ey}" r="9"/><circle class="hit" cx="{ex}" cy="{ey}" r="5"/>'
    )
    return css, defs, scene


def reverie_art():
    """A figure at the lake's edge, seen on a worn tape, with a hand of cards held up."""
    rng = random.Random(9)
    horizon = 72
    trees = conifers(rng, 0, 410, horizon, 9, 26, half=4.2)
    frame = conifers(rng, -4, 46, horizon, 30, 50, half=7, gap=(9, 15)) + " " + conifers(rng, 372, 414, horizon, 30, 50, half=7, gap=(9, 15))
    ripples = "".join(
        f'<rect class="rp" x="{96 - w / 2:.0f}" y="{y}" width="{w}" height="1.4" rx=".7" fill="#FFD9E6" opacity="{o}" style="animation-delay:-{i * .9}s"/>'
        for i, (y, w, o) in enumerate([(78, 30, .5), (85, 20, .34), (92, 26, .22)])
    )
    cabin = (
        f'<path d="M168,{horizon} V57 L163,57 L183,43 L203,57 L198,57 V{horizon} Z" fill="#08040C"/>'
        f'<rect class="lamp" x="186" y="60" width="6" height="6" fill="{EMBER}"/>'
        f'<g opacity=".22"><rect class="lamp" x="186" y="77" width="6" height="14" fill="{EMBER}"/></g>'
    )
    figure = f'<path d="M224.5,{horizon} L226.6,{horizon - 13} L231.4,{horizon - 13} L233.5,{horizon} Z" fill="#050208"/><circle cx="229" cy="{horizon - 16.2}" r="2.7" fill="#050208"/>'

    def held(rot, delay, lead=False):
        edge = f'stroke="{PINK}" stroke-width="1.6"' if lead else 'stroke="#A04C80" stroke-width="1.2"'
        return (
            f'<g transform="translate(312,176) rotate({rot})"><g class="sway" style="animation-delay:-{delay}s">'
            f'<rect x="-26" y="-144" width="52" height="74" rx="5" fill="#2A1238" {edge}/>'
            f'<rect x="-21" y="-139" width="42" height="64" rx="3" fill="none" stroke="#A04C80" stroke-opacity=".5"/>'
            f'<path d="M0,-118 L7.5,-107 L0,-96 L-7.5,-107 Z" fill="none" stroke="{PINK}" stroke-opacity=".85" stroke-width="1.3"/></g></g>'
        )

    css = """.sway{transform-origin:0 0;animation:sway 6s ease-in-out infinite alternate}
@keyframes sway{from{transform:rotate(-1.4deg)}to{transform:rotate(1.4deg)}}
.gl{animation:gl 5s ease-in-out infinite}
@keyframes gl{50%{opacity:.45}}
.rp{animation:rp 3.6s ease-in-out infinite alternate}
@keyframes rp{to{transform:translateX(5px)}}
.lamp{animation:lamp 6.5s ease-in-out infinite}
@keyframes lamp{0%,100%{opacity:1}46%{opacity:.92}50%{opacity:.45}56%{opacity:.95}}
.track{animation:track 9s linear infinite}
@keyframes track{from{transform:translateY(-14px)}to{transform:translateY(112px)}}
@media (prefers-reduced-motion: reduce){.track{opacity:0}}"""
    defs = (
        '<linearGradient id="ns" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#150A20"/><stop offset=".68" stop-color="#6A1840"/><stop offset=".7" stop-color="#2C1030"/><stop offset="1" stop-color="#150A1A"/></linearGradient>'
        '<radialGradient id="rg" cx="312" cy="70" r="150" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#F0366A" stop-opacity=".6"/><stop offset="1" stop-color="#F0366A" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="mg" cx="96" cy="50" r="46" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FFD9E6" stop-opacity=".4"/><stop offset="1" stop-color="#FFD9E6" stop-opacity="0"/></radialGradient>'
        '<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".2"/></pattern>'
    )
    scene = (
        '<rect width="410" height="104" fill="url(#ns)"/><rect width="410" height="104" fill="url(#mg)"/>'
        '<circle cx="96" cy="50" r="16" fill="#FFE3EC"/><circle cx="102" cy="45" r="14" fill="#6A1840" opacity=".2"/>'
        f'<path d="{trees}" fill="#08040C"/><path d="{frame}" fill="#050208"/>{cabin}{figure}{ripples}'
        '<rect class="gl" width="410" height="104" fill="url(#rg)"/>'
        + held(-19, 0) + held(19, 4) + held(0, 2.2, lead=True)
        + '<rect width="410" height="104" fill="url(#scan)"/><rect class="track" width="410" height="9" fill="#fff" opacity=".07"/>'
    )
    return css, defs, scene


def registry_art():
    """Rows of deck cards being checked off one at a time."""
    rng = random.Random(21)
    tints = [VIOLET, CYAN, PINK, EMBER]
    cards = []
    for n in range(20):
        col, row = n % 10, n // 10
        x, y = 22 + col * 37.4, 12 + row * 42
        tint = rng.choice(tints)
        cards.append(
            f'<g class="dk" style="animation-delay:{n * .22:.2f}s"><rect x="{x:.1f}" y="{y}" width="29" height="36" rx="4" fill="{RAISED}" stroke="{tint}" stroke-opacity=".5"/>'
            f'<circle cx="{x + 7:.1f}" cy="{y + 8}" r="2.6" fill="{tint}"/>'
            f'<rect x="{x + 5:.1f}" y="{y + 18}" width="19" height="2" rx="1" fill="#fff" opacity=".3"/>'
            f'<rect x="{x + 5:.1f}" y="{y + 24}" width="{rng.choice([9, 12, 15])}" height="2" rx="1" fill="#fff" opacity=".17"/></g>'
        )
    css = ".dk{opacity:.45;animation:dk 7s ease-in-out infinite}@keyframes dk{0%,100%{opacity:.45}6%,70%{opacity:1}86%{opacity:.45}}\n@media (prefers-reduced-motion: reduce){.dk{opacity:1}}"
    return css, "", f'<rect width="410" height="104" fill="{WELL}"/>' + "".join(cards)


def noir_art():
    """A black-and-white editor with a single coloured token."""
    rng = random.Random(5)
    rows = []
    for n in range(6):
        y = 20 + n * 13.5
        x = 48 + rng.choice([0, 0, 14, 28])
        rows.append(f'<rect x="20" y="{y}" width="9" height="3.4" rx="1.7" fill="#4C4658"/>')
        for k in range(rng.randint(2, 4)):
            w = rng.choice([20, 28, 38, 50, 64])
            tone = PINK if (n, k) == (2, 1) else rng.choice(["#F4F1F9", "#A29CAE", "#A29CAE", "#625C6E"])
            rows.append(f'<rect x="{x}" y="{y}" width="{w}" height="3.4" rx="1.7" fill="{tone}"/>')
            x += w + 8
        if n == 4:
            rows.append(f'<rect class="cur" x="{x}" y="{y - 3.6}" width="5.5" height="10.6" fill="#F4F1F9"/>')
    css = ".cur{animation:cur 1.8s ease-in-out infinite}@keyframes cur{0%,45%{opacity:1}55%,95%{opacity:0}}"
    scene = '<rect width="410" height="104" fill="#100C16"/><rect x="38" width="1" height="104" fill="#241E2E"/>' + "".join(rows)
    return css, "", scene


# --- technology panels ------------------------------------------------------

PILL_H, PILL_SIZE = 32, 13.5


def tech_layout(items, w, top):
    x, y, out = 16, top, []
    for name in items:
        pw = BODY_B.width(name, PILL_SIZE) + 28
        if x + pw > w - 16:
            x, y = 16, y + PILL_H + 9
        out.append((name, x, y, pw))
        x += pw + 8
    return out, y + PILL_H + 20


def tech(title, items, strong, height, seed, note=None):
    W = 270
    top = 78 if note else 56
    placed, _ = tech_layout(items, W, top)
    fill, stroke, so = (RAISED, VIOLET, ".75") if strong else ("#1E1530", "#8B6CF0", ".3")
    pills = "".join(
        f'<g class="pl" style="animation-delay:{i * .3:.1f}s"><rect x="{x:.0f}" y="{y}" width="{pw:.0f}" height="{PILL_H}" rx="{PILL_H / 2}" fill="{fill}" stroke="{stroke}" stroke-opacity="{so}"/>'
        + BODY_B.path(name, x + 14, y + 20.8, PILL_SIZE, TEXT) + "</g>"
        for i, (name, x, y, pw) in enumerate(placed)
    )
    css = ".pl{opacity:.86;animation:pl 6s ease-in-out infinite}@keyframes pl{0%,22%,100%{opacity:.86}9%{opacity:1}}\n@media (prefers-reduced-motion: reduce){.pl{opacity:1}}"
    body = DISPLAY.path(title, 16, 35, 14.5, TEXT, track=0.1) + pills
    if note:
        body += BODY.path(note, 16, 58, 13.5, FAINT)
    label = f"{title} ({note.lower()}): " if note else f"{title}: "
    return panel(W, height, label + ", ".join(items), css, "", body, stars=seed)


# --- build ------------------------------------------------------------------

TABS = {
    "tab-highlights": "Engineering highlights",
    "tab-build": "What I build",
    "tab-projects": "Selected projects",
    "tab-tech": "Technology stack",
    "tab-engineering": "How I think",
    "tab-outside": "Outside the editor",
}
TILES = {
    "tile-backend": ("Backend & distributed systems", ".NET APIs and SQL Server behind multi-tenant reconciliation, reporting and integrations.", glyph_backend, CYAN),
    "tile-fullstack": ("Full-stack product engineering", "Angular, TypeScript and React front ends, with features owned end to end.", glyph_fullstack, VIOLET),
    "tile-ai": ("AI integration & workflows", "Assistant features that answer questions and drive existing application workflows.", glyph_ai, PINK),
    "tile-indie": ("Independent software & games", "Original products and games I design and build on my own time.", glyph_indie, EMBER),
}
PRIMARY = ["C#", "ASP.NET Core", "SQL Server", "Angular", "TypeScript", "REST APIs"]
ADDITIONAL = ["React", "Next.js", "Node.js", "PostgreSQL", "RabbitMQ", "Azure DevOps", "xUnit", "Jasmine"]
AI = ["Tool calling", "Retrieval", "Evaluation", "Orchestration"]
AI_NOTE = "Building experience"


def build():
    files = {"header": header()}
    files.update({name: tab(title) for name, title in TABS.items()})
    files.update({name: tile(t, text, g, accent, i) for i, (name, (t, text, g, accent)) in enumerate(TILES.items())})
    files["card-trace"] = card(
        "TRACE", "Developer tool", "AI engineering intelligence platform",
        "For understanding repositories and investigating issues with evidence. Planned: code search, GitHub integration and AI evaluation.",
        trace_art(), "In development", seed=31)
    files["card-reverie"] = card(
        "Reverie of Fear", "Game", "Co-op horror deck-builder",
        "An original game I'm developing. One to five players take on 80s slasher archetypes against a Slasher that runs itself.",
        reverie_art(), "In development", link="reverieoffear.com", seed=32)
    files["card-registry"] = card(
        "Imperial Deck Registry", "Web app", "Deck building for Star Wars: Unlimited",
        "A deck registry for the card game's players, built with Next.js, TypeScript, PostgreSQL and Prisma.",
        registry_art(), "Live", live=True, link="imperialdeckregistry.com", seed=33)
    files["card-noir"] = card(
        "Noir", "Editor theme", "Black-and-white theme for VS Code",
        "Uses color only where it matters. Published on the VS Code Marketplace.",
        noir_art(), "Published", live=True, link="github.com/SenpaiSumpie/Noir", seed=34)
    panels = [
        ("tech-primary", "Primary stack", PRIMARY, True, None),
        ("tech-additional", "Additional experience", ADDITIONAL, False, None),
        ("tech-ai", "AI engineering", AI, False, AI_NOTE),
    ]
    tech_h = max(tech_layout(items, 270, 78 if note else 56)[1] for _, _, items, _, note in panels)
    for i, (name, title, items, strong, note) in enumerate(panels):
        files[name] = tech(title, items, strong, tech_h, 40 + i, note)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, content in files.items():
        (OUT / f"{name}.svg").write_text(content, encoding="utf-8", newline="\n")
    total = sum(len(c.encode()) for c in files.values())
    print(f"{len(files)} files, {total / 1024:.0f} KB -> {OUT}")


if __name__ == "__main__":
    build()
