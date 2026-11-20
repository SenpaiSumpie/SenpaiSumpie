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
PLUM = "#1A1228"
WELL = "#150E22"
DUSK = "#2A1740"
RAISED = "#2B1F42"
VIOLET = "#8B6CF0"
PINK = "#F26CA7"
CYAN = "#6FE3E1"
EMBER = "#F7A259"
TEXT = "#EFE8FA"
MUTED = "#BDB0D6"
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


def svg(w, h, label, css, defs, body, rx=12, fill=PLUM, stroke=HAIR):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{html.escape(label)}">
<style>
{css}
{REDUCED}
</style>
<defs><clipPath id="frame"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>{defs}</defs>
<g clip-path="url(#frame)">
<rect width="{w}" height="{h}" fill="{fill}"/>
{body}
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx - .5}" fill="none" stroke="{stroke}"/>
</g>
</svg>
"""


def conifers(rng, x0, x1, base, lo, hi, half=3.2):
    out, x = [], x0
    while x < x1:
        y = base(x) if callable(base) else base
        h = rng.uniform(lo, hi)
        out.append(f"M{x - half:.1f},{y:.1f} L{x:.1f},{y - h:.1f} L{x + half:.1f},{y:.1f} Z")
        x += rng.uniform(4, 9)
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
    far, mid, near = ridge(rng, W, 212, 20), ridge(rng, W, 240, 24), ridge(rng, W, 274, 10)
    tx = 664
    ty = y_at(mid, tx)
    top = ty - 50

    stars = []
    for i in range(70):
        x, y = rng.uniform(8, W - 8), rng.uniform(8, 180)
        if 30 < x < 560 and 56 < y < 194:
            continue
        r = rng.choice([0.6, 0.7, 0.9, 1.2])
        tw = f' class="tw" style="animation-duration:{rng.uniform(4, 8):.1f}s;animation-delay:-{rng.uniform(0, 6):.1f}s"' if i % 4 == 0 else ""
        stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{rng.uniform(.35, .9):.2f}"{tw}/>')

    trees = conifers(rng, 0, W, lambda x: y_at(near, x) + 2, 7, 19)
    arcs = "".join(f'<circle class="arc" cx="{tx}" cy="{top}" r="96" style="animation-delay:-{d}s"/>' for d in (0, 1.6, 3.2))
    tower = (
        f'<g stroke="#0B0714" stroke-width="1.3" fill="none">'
        f'<path d="M{tx - 6},{ty + 3} L{tx},{top} L{tx + 6},{ty + 3}"/>'
        f'<path d="M{tx - 4.6},{ty - 9} L{tx + 3.2},{ty - 22} M{tx + 4.6},{ty - 9} L{tx - 3.2},{ty - 22} '
        f'M{tx - 3.2},{ty - 22} L{tx + 1.8},{ty - 35} M{tx + 3.2},{ty - 22} L{tx - 1.8},{ty - 35}"/></g>'
        f'<circle class="beacon" cx="{tx}" cy="{top}" r="2.4" fill="{PINK}"/>'
    )
    css = f""".tw{{animation:tw 6s ease-in-out infinite}}
@keyframes tw{{50%{{opacity:.12}}}}
.arc{{fill:none;stroke:{PINK};stroke-width:1.3;vector-effect:non-scaling-stroke;transform-box:fill-box;transform-origin:center;opacity:0;animation:arc 4.8s linear infinite}}
@keyframes arc{{0%{{transform:scale(.04);opacity:.75}}100%{{transform:scale(1);opacity:0}}}}
.beacon{{animation:bk 2.4s ease-in-out infinite}}
@keyframes bk{{50%{{opacity:.25}}}}
.au{{animation:au 22s ease-in-out infinite alternate}}
@keyframes au{{to{{transform:translateX(46px)}}}}
@media (prefers-reduced-motion: reduce){{.arc{{opacity:.3}}.arc:nth-of-type(2){{transform:scale(.66)}}.arc:nth-of-type(3){{transform:scale(.33)}}}}"""
    defs = (
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}"/><stop offset=".62" stop-color="{DUSK}"/><stop offset="1" stop-color="#4A2256"/></linearGradient>'
        f'<radialGradient id="glow" cx="{tx}" cy="246" r="340" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{EMBER}" stop-opacity=".85"/><stop offset=".22" stop-color="{PINK}" stop-opacity=".5"/><stop offset=".6" stop-color="{VIOLET}" stop-opacity=".12"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
        '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="26"/></filter>'
    )
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
        f'<g class="au" filter="url(#blur)" opacity=".5"><ellipse cx="250" cy="34" rx="210" ry="20" fill="{VIOLET}"/><ellipse cx="560" cy="60" rx="150" ry="13" fill="{CYAN}" opacity=".35"/></g>'
        + "".join(stars)
        + f'<rect width="{W}" height="{H}" fill="url(#glow)"/>'
        + poly(far, H, "#4B2C63") + arcs + poly(mid, H, "#27163B") + tower + poly(near, H, "#120B1E")
        + f'<path d="{trees}" fill="#120B1E"/>'
        + DISPLAY.path("Max Mosier", 46, 116, 56, TEXT, track=-0.6)
        + BODY.path("Building reliable systems, intelligent tools,", 48, 153, 22, "#D9CDEE")
        + BODY.path("and ambitious software.", 48, 181, 22, "#D9CDEE")
    )
    label = ("Max Mosier. Building reliable systems, intelligent tools, and ambitious software. "
             "A night sky over mountain ridgelines with a radio tower sending out a signal.")
    return svg(W, H, label, css, defs, body, rx=14, fill=INK, stroke="#ffffff14")


# --- section headings -------------------------------------------------------

def tab(title):
    W, H = 410, 46
    x0 = 18 + DISPLAY.width(title, 15, 0.1) + 14
    x1 = W - 18
    css = f""".run{{animation:run 4.6s linear infinite}}
@keyframes run{{0%{{transform:translateX(0);opacity:0}}12%{{opacity:1}}88%{{opacity:1}}100%{{transform:translateX({x1 - x0 - 28:.0f}px);opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.run{{opacity:0}}}}"""
    defs = f'<linearGradient id="pulse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PINK}" stop-opacity="0"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
    body = (
        DISPLAY.path(title, 18, 28.5, 15, TEXT, track=0.1)
        + f'<rect x="{x0:.0f}" y="22.5" width="{x1 - x0:.0f}" height="1" fill="{HAIR}"/>'
        + f'<rect class="run" x="{x0:.0f}" y="22" width="28" height="2" rx="1" fill="url(#pulse)"/>'
        + f'<circle cx="{x1}" cy="23" r="2.6" fill="{PINK}"/>'
    )
    return svg(W, H, title, css, defs, body, rx=10)


# --- focus tiles ------------------------------------------------------------

def glyph_backend():
    rows = "".join(
        f'<rect x="33" y="{y}" width="38" height="10" rx="3" fill="{RAISED}" stroke="{VIOLET}" stroke-opacity=".8"/>'
        f'<circle class="led" cx="40" cy="{y + 5}" r="1.8" style="animation-delay:{i * .45}s"/>'
        f'<rect x="46" y="{y + 4}" width="{w}" height="2" rx="1" fill="{HAIR}"/>'
        for i, (y, w) in enumerate([(32, 18), (47, 12), (62, 20)])
    )
    css = f".led{{fill:{HAIR};animation:led 3.2s ease-in-out infinite}}@keyframes led{{0%,40%,100%{{fill:{HAIR}}}12%,26%{{fill:{CYAN}}}}}"
    return css, rows


def glyph_fullstack():
    def layer(dy, stroke, cls):
        return f'<path class="{cls}" d="M52,{28 + dy} L73,{38 + dy} L52,{48 + dy} L31,{38 + dy} Z" fill="{RAISED}" stroke="{stroke}" stroke-width="1.4" stroke-linejoin="round"/>'
    css = ".l1{animation:fl 4.4s ease-in-out infinite alternate}.l2{animation:fl 4.4s ease-in-out infinite alternate -1.4s}@keyframes fl{to{transform:translateY(-2.6px)}}"
    return css, layer(22, HAIR, "l3") + layer(11, VIOLET, "l2") + layer(0, CYAN, "l1")


def glyph_ai():
    outer = [(34, 36), (72, 40), (48, 72)]
    lines = "".join(f'<path d="M52,53 L{x},{y}" stroke="{HAIR}" stroke-width="1.4"/>' for x, y in outer)
    nodes = "".join(f'<circle class="tool" cx="{x}" cy="{y}" r="4.2" style="animation-delay:{i * .9}s"/>' for i, (x, y) in enumerate(outer))
    css = f".tool{{fill:{RAISED};stroke:{VIOLET};stroke-width:1.4;animation:tool 3.6s ease-in-out infinite}}@keyframes tool{{0%,34%,100%{{fill:{RAISED}}}10%,22%{{fill:{CYAN}}}}}.core{{animation:core 3.6s ease-in-out infinite}}@keyframes core{{50%{{opacity:.55}}}}"
    return css, lines + nodes + f'<circle class="core" cx="52" cy="53" r="6.4" fill="{PINK}"/>'


def glyph_indie():
    css = ".go{animation:go 3.4s ease-in-out infinite}@keyframes go{50%{opacity:.35}}"
    art = (
        f'<rect x="31" y="35" width="42" height="34" rx="5" fill="{RAISED}" stroke="{VIOLET}" stroke-width="1.4"/>'
        f'<rect x="31" y="43" width="42" height="1" fill="{VIOLET}" opacity=".6"/>'
        f'<circle cx="36.5" cy="39.4" r="1.3" fill="{CYAN}"/><circle cx="41" cy="39.4" r="1.3" fill="{HAIR}"/>'
        f'<path class="go" d="M48,49.5 L59,56 L48,62.5 Z" fill="{PINK}"/>'
    )
    return css, art


def tile(title, text, glyph):
    W, H = 410, 128
    css, art = glyph
    room = W - 100 - 20
    size = 14.0
    while DISPLAY.width(title, size, 0.1) > room:
        size -= 0.25
    lines = BODY.wrap(text, 14.5, room)
    body = (
        f'<g transform="translate(0,12)"><rect x="20" y="20" width="64" height="64" rx="10" fill="{WELL}" stroke="{HAIR}"/>{art}</g>'
        + DISPLAY.path(title, 100, 41, size, TEXT, track=0.1)
        + "".join(BODY.path(l, 100, 66 + i * 20, 14.5, MUTED) for i, l in enumerate(lines))
    )
    return svg(W, H, f"{title}: {text}", css, "", body)


# --- project cards ----------------------------------------------------------

def card(title, kind, desc, art, label, status="In development", live=False, link=None):
    W, H = 410, 304
    css, defs, scene = art
    lines = BODY.wrap(desc, 15, W - 48)
    pill_w = BODY_B.width(status, 12.5) + 32
    css = ".dot{animation:dot 2.6s ease-in-out infinite}@keyframes dot{50%{opacity:.3}}\n" + css
    defs += '<clipPath id="band"><rect width="410" height="104"/></clipPath>'
    foot = H - 44
    body = (
        f'<g clip-path="url(#band)">{scene}</g>'
        f'<rect y="104" width="{W}" height="1" fill="{HAIR}"/>'
        + DISPLAY.path(title, 24, 142, 21, TEXT, track=0.2)
        + BODY.path(kind, 24, 165, 14, "#A999C8")
        + "".join(BODY.path(l, 24, 194 + i * 21.5, 15, "#CFC4E4") for i, l in enumerate(lines))
        + f'<g transform="translate(24,{foot})"><rect width="{pill_w:.0f}" height="26" rx="13" fill="{INK}" fill-opacity=".6" stroke="#fff" stroke-opacity=".12"/>'
        + f'<circle class="dot" cx="14" cy="13" r="3.4" fill="{CYAN if live else PINK}"/>' + BODY_B.path(status, 24, 17.4, 12.5, TEXT) + "</g>"
    )
    if link:
        body += BODY_B.path(link, W - 24 - BODY_B.width(link, 13.5), foot + 17.6, 13.5, CYAN)
    return svg(W, H, label, css, defs, body)


def trace_art():
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1" fill="#fff" opacity=".1"/>' for x in range(14, 410, 20) for y in range(12, 104, 20))
    nodes = [(34, 74), (94, 34), (154, 74), (214, 54), (274, 34), (334, 74), (376, 54)]
    side = [((94, 34), (134, 14)), ((154, 74), (194, 94)), ((214, 54), (254, 74)), ((274, 34), (314, 14)), ((334, 74), (294, 94))]
    d = "M" + " L".join(f"{x},{y}" for x, y in nodes)
    branches = "".join(
        f'<path d="M{a[0]},{a[1]} L{b[0]},{b[1]}" stroke="{HAIR}" stroke-width="1.4"/><circle cx="{b[0]}" cy="{b[1]}" r="3" fill="{RAISED}" stroke="{HAIR}"/>'
        for a, b in side
    )
    n = len(nodes) - 1
    lit = "".join(f'<circle class="nd" cx="{x}" cy="{y}" r="4.2" style="animation-delay:{i / n * 4.2:.2f}s"/>' for i, (x, y) in enumerate(nodes))
    css = f""".tr{{stroke-dasharray:100;stroke-dashoffset:100;animation:tr 7s ease-in-out infinite}}
@keyframes tr{{0%{{stroke-dashoffset:100;opacity:1}}60%{{stroke-dashoffset:0;opacity:1}}88%{{stroke-dashoffset:0;opacity:1}}100%{{stroke-dashoffset:0;opacity:0}}}}
.nd{{fill:{RAISED};stroke:{VIOLET};stroke-width:1.4;animation:nd 7s linear infinite}}
@keyframes nd{{0%{{fill:{RAISED}}}4%{{fill:{CYAN}}}82%{{fill:{CYAN}}}100%{{fill:{RAISED}}}}}
@media (prefers-reduced-motion: reduce){{.tr{{stroke-dashoffset:0}}.nd{{fill:{CYAN}}}}}"""
    defs = f'<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
    scene = (
        f'<rect width="410" height="104" fill="{WELL}"/>{dots}{branches}'
        f'<path d="{d}" fill="none" stroke="{HAIR}" stroke-width="1.6"/>'
        f'<path class="tr" d="{d}" pathLength="100" fill="none" stroke="url(#tg)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>{lit}'
    )
    return css, defs, scene


def reverie_art():
    """A lakeside cabin seen on a worn VHS tape, with a hand of cards held in front."""
    rng = random.Random(9)
    horizon = 68
    trees = conifers(rng, 0, 410, horizon, 8, 24, half=4)
    ripples = "".join(
        f'<rect class="rp" x="{104 - w / 2:.0f}" y="{y}" width="{w}" height="1.4" rx=".7" fill="#F6DCE6" opacity="{o}" style="animation-delay:-{i * .9}s"/>'
        for i, (y, w, o) in enumerate([(74, 30, .55), (80, 22, .4), (86, 26, .28), (92, 14, .18)])
    )
    cabin = (
        f'<path d="M172,{horizon} V54 L168,54 L187,41 L206,54 L202,54 V{horizon} Z" fill="#0F0714"/>'
        f'<rect class="lamp" x="189" y="57" width="6" height="6" fill="{EMBER}"/>'
        f'<g opacity=".2"><rect class="lamp" x="189" y="73" width="6" height="14" fill="{EMBER}"/></g>'
    )

    def held(rot, delay):
        return (
            f'<g transform="translate(306,176) rotate({rot})"><g class="sway" style="animation-delay:-{delay}s">'
            f'<rect x="-25" y="-142" width="50" height="72" rx="5" fill="#2A1238" stroke="#8A4470" stroke-width="1.2"/>'
            f'<rect x="-20" y="-137" width="40" height="62" rx="3" fill="none" stroke="#8A4470" stroke-opacity=".55"/>'
            f'<path d="M0,-116 L7,-106 L0,-96 L-7,-106 Z" fill="none" stroke="{PINK}" stroke-opacity=".75" stroke-width="1.2"/></g></g>'
        )

    play = DISPLAY.path("PLAY", 30, 23, 9.5, "#F4E6EC", track=0.6)
    clock = BODY_B.path("0:13:13", 410 - 16 - BODY_B.width("0:13:13", 11), 23, 11, "#F4E6EC")
    css = """.sway{transform-origin:0 0;animation:sway 6s ease-in-out infinite alternate}
@keyframes sway{from{transform:rotate(-1.4deg)}to{transform:rotate(1.4deg)}}
.gl{animation:gl 5s ease-in-out infinite}
@keyframes gl{50%{opacity:.4}}
.rp{animation:rp 3.6s ease-in-out infinite alternate}
@keyframes rp{to{transform:translateX(5px)}}
.lamp{animation:lamp 6.5s ease-in-out infinite}
@keyframes lamp{0%,100%{opacity:1}46%{opacity:.92}50%{opacity:.45}56%{opacity:.95}}
.track{animation:track 9s linear infinite}
@keyframes track{from{transform:translateY(-14px)}to{transform:translateY(112px)}}
@media (prefers-reduced-motion: reduce){.track{opacity:0}}"""
    defs = (
        f'<linearGradient id="ns" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#140A1E"/><stop offset=".65" stop-color="#3D1332"/><stop offset=".66" stop-color="#241029"/><stop offset="1" stop-color="#150A1A"/></linearGradient>'
        '<radialGradient id="rg" cx="306" cy="70" r="150" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#E0325C" stop-opacity=".5"/><stop offset="1" stop-color="#E0325C" stop-opacity="0"/></radialGradient>'
        '<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".2"/></pattern>'
    )
    scene = (
        '<rect width="410" height="104" fill="url(#ns)"/>'
        '<circle cx="104" cy="38" r="13" fill="#F6DCE6"/><circle cx="109" cy="34" r="11.5" fill="#140A1E" opacity=".2"/>'
        f'<path d="{trees}" fill="#0F0714"/>{cabin}{ripples}'
        '<rect class="gl" width="410" height="104" fill="url(#rg)"/>'
        + held(-19, 0) + held(19, 4) + held(0, 2.2)
        + '<rect width="410" height="104" fill="url(#scan)"/>'
        '<rect class="track" width="410" height="9" fill="#fff" opacity=".07"/>'
        f'<path d="M16,15.5 L24,19.5 L16,23.5 Z" fill="#F4E6EC"/>{play}{clock}'
    )
    return css, defs, scene


def registry_art():
    """Rows of deck cards being checked off one at a time."""
    rng = random.Random(21)
    tints = [VIOLET, CYAN, PINK, EMBER]
    cards = []
    for n in range(20):
        col, row = n % 10, n // 10
        x, y = 22 + col * 37.4, 13 + row * 42
        tint = rng.choice(tints)
        cards.append(
            f'<g class="dk" style="animation-delay:{n * .22:.2f}s"><rect x="{x:.1f}" y="{y}" width="29" height="36" rx="4" fill="{RAISED}" stroke="{HAIR}"/>'
            f'<circle cx="{x + 7:.1f}" cy="{y + 8}" r="2.6" fill="{tint}"/>'
            f'<rect x="{x + 5:.1f}" y="{y + 18}" width="19" height="2" rx="1" fill="#fff" opacity=".28"/>'
            f'<rect x="{x + 5:.1f}" y="{y + 24}" width="{rng.choice([9, 12, 15])}" height="2" rx="1" fill="#fff" opacity=".16"/></g>'
        )
    css = ".dk{opacity:.5;animation:dk 7s ease-in-out infinite}@keyframes dk{0%,100%{opacity:.5}6%,70%{opacity:1}86%{opacity:.5}}\n@media (prefers-reduced-motion: reduce){.dk{opacity:1}}"
    return css, "", f'<rect width="410" height="104" fill="{WELL}"/>' + "".join(cards)


def noir_art():
    """A black-and-white editor with a single coloured token."""
    rng = random.Random(5)
    rows = []
    for n in range(6):
        y = 24 + n * 12.5
        x = 46 + rng.choice([0, 0, 14, 28])
        rows.append(f'<rect x="22" y="{y}" width="8" height="3" rx="1.5" fill="#4a4a4a"/>')
        for k in range(rng.randint(2, 4)):
            w = rng.choice([18, 26, 34, 46, 58])
            tone = PINK if (n, k) == (2, 1) else rng.choice(["#f2f2f2", "#9a9a9a", "#9a9a9a", "#5e5e5e"])
            rows.append(f'<rect x="{x}" y="{y}" width="{w}" height="3" rx="1.5" fill="{tone}"/>')
            x += w + 7
        if n == 4:
            rows.append(f'<rect class="cur" x="{x}" y="{y - 3.5}" width="5" height="10" fill="#f2f2f2"/>')
    css = ".cur{animation:cur 1.8s ease-in-out infinite}@keyframes cur{0%,45%{opacity:1}55%,95%{opacity:0}}"
    scene = (
        '<rect width="410" height="104" fill="#121212"/>'
        '<rect width="410" height="14" fill="#1c1c1c"/><circle cx="14" cy="7" r="2.4" fill="#4a4a4a"/><circle cx="23" cy="7" r="2.4" fill="#4a4a4a"/><circle cx="32" cy="7" r="2.4" fill="#4a4a4a"/>'
        '<rect x="37" y="14" width="1" height="90" fill="#262626"/>' + "".join(rows)
    )
    return css, "", scene


# --- technology panels ------------------------------------------------------

def tech_layout(items, w, top):
    x, y, out = 16, top, []
    for name in items:
        pw = BODY_B.width(name, 13.5) + 24
        if x + pw > w - 16:
            x, y = 16, y + 38
        out.append((name, x, y, pw))
        x += pw + 7
    return out, y + 30 + 18


def tech(title, items, strong, height, note=None):
    W = 270
    top = 68 if note else 48
    placed, _ = tech_layout(items, W, top)
    fill, stroke = (RAISED, VIOLET) if strong else ("#1F1630", "#55407A")
    pills = "".join(
        f'<g class="pl" style="animation-delay:{i * .3:.1f}s"><rect x="{x:.0f}" y="{y}" width="{pw:.0f}" height="30" rx="15" fill="{fill}" stroke="{stroke}"/>'
        + BODY_B.path(name, x + 12, y + 19.8, 13.5, TEXT) + "</g>"
        for i, (name, x, y, pw) in enumerate(placed)
    )
    css = ".pl{opacity:.84;animation:pl 6s ease-in-out infinite}@keyframes pl{0%,22%,100%{opacity:.84}9%{opacity:1}}\n@media (prefers-reduced-motion: reduce){.pl{opacity:1}}"
    body = DISPLAY.path(title, 16, 31, 13, TEXT, track=0.1) + pills
    if note:
        body += BODY.path(note, 16, 52, 13.5, "#A999C8")
    label = f"{title} ({note.lower()}): " if note else f"{title}: "
    return svg(W, height, label + ", ".join(items), css, "", body)


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
    "tile-backend": ("Backend & distributed systems", ".NET APIs and SQL Server behind multi-tenant reconciliation, reporting and integrations.", glyph_backend),
    "tile-fullstack": ("Full-stack product engineering", "Angular, TypeScript and React front ends, with features owned end to end.", glyph_fullstack),
    "tile-ai": ("AI integration & workflows", "Assistant features that answer questions and drive existing application workflows.", glyph_ai),
    "tile-indie": ("Independent software & games", "Original products and games I design and build on my own time.", glyph_indie),
}
PRIMARY = ["C#", "ASP.NET Core", "SQL Server", "Angular", "TypeScript", "REST APIs"]
ADDITIONAL = ["React", "Next.js", "Node.js", "PostgreSQL", "RabbitMQ", "Azure DevOps", "xUnit", "Jasmine"]
AI = ["Tool calling", "Retrieval", "Evaluation", "Orchestration"]
AI_NOTE = "Building experience"


def build():
    files = {"header": header()}
    files.update({name: tab(title) for name, title in TABS.items()})
    files.update({name: tile(t, text, g()) for name, (t, text, g) in TILES.items()})
    files["card-trace"] = card(
        "TRACE", "AI engineering intelligence platform",
        "A platform for understanding repositories and investigating issues with evidence. Planned: code search, GitHub integration and AI evaluation.",
        trace_art(), "TRACE, an AI engineering intelligence platform. In development.")
    files["card-reverie"] = card(
        "Reverie of Fear", "Co-op horror deck-building game",
        "An original game I'm developing. One to five players take on 80s slasher archetypes against a Slasher that runs itself.",
        reverie_art(), "Reverie of Fear, a co-op horror deck-building game. In development.", link="reverieoffear.com")
    files["card-registry"] = card(
        "Imperial Deck Registry", "Deck-building web app",
        "A deck registry for Star Wars: Unlimited players, built with Next.js, TypeScript, PostgreSQL and Prisma.",
        registry_art(), "Imperial Deck Registry, a deck-building web app. Live.", status="Live", live=True, link="imperialdeckregistry.com")
    files["card-noir"] = card(
        "Noir", "VS Code theme",
        "A black-and-white editor theme that uses color only where it matters. Published on the VS Code Marketplace.",
        noir_art(), "Noir, a VS Code theme. Published.", status="Published", live=True, link="github.com/SenpaiSumpie/Noir")
    panels = [
        ("tech-primary", "Primary stack", PRIMARY, True, None),
        ("tech-additional", "Additional experience", ADDITIONAL, False, None),
        ("tech-ai", "AI engineering", AI, False, AI_NOTE),
    ]
    tech_h = max(tech_layout(items, 270, 68 if note else 48)[1] for _, _, items, _, note in panels)
    for name, title, items, strong, note in panels:
        files[name] = tech(title, items, strong, tech_h, note)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, content in files.items():
        (OUT / f"{name}.svg").write_text(content, encoding="utf-8", newline="\n")
    total = sum(len(c.encode()) for c in files.values())
    print(f"{len(files)} files, {total / 1024:.0f} KB -> {OUT}")


if __name__ == "__main__":
    build()
