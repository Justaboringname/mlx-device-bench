#!/usr/bin/env python3
"""Generate the README SVGs (hero / thermal / nax, each dark + light).

Built on the shared README image kit; the repo's own figures are at the bottom.
The thermal figure reads its points from the two iPhone logs in results/.
Each figure is ONE layout function fed a theme dict, so the dark and light
variants share geometry exactly and differ only in colour.

Run from the repo root:  python3 assets/build/gen.py
Writes assets/<name>-dark.svg and assets/<name>-light.svg.
Standard library only.
"""
import math
import os
import sys

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SANS = ('-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, '
        '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif')
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'

# Same palette as claude-code-model-routing. Do not add colours: two accents only
# (clay = the thing that matters / warm, sage = the supporting / healthy side).
THEMES = {
    "dark": dict(
        bg="#181818", panel="#212121", hair="#2f2f2f",
        text="#ecece8", muted="#9b9a94",
        clay="#d97757", sage="#9bb07c",
        grid="#2a2a2a", axis="#4b4a46", conn="#5a5955", dots="#3b3b39", node="#333332",
        band="#ecece8", band_op="0.055", band_label="#9b9a94",
    ),
    "light": dict(
        bg="#faf9f5", panel="#ffffff", hair="#e6e3d9",
        text="#1f1e1c", muted="#6f6d66",
        clay="#b3532f", sage="#5f7347",
        grid="#ebe8df", axis="#c4c0b4", conn="#c4bfb2", dots="#dcd8cd", node="#dedacf",
        band="#1f1e1c", band_op="0.045", band_label="#67655e",
    ),
}

# Hero geometry (keep identical across repos so the profile reads as one set)
HERO_W, HERO_H = 1280, 420
LEFT_X = 72                 # eyebrow / tagline x; title sits 4px left of it
TITLE_MAX_W = 560           # title must end before x = 632
RIGHT_X0, RIGHT_X1 = 660, 1216   # right-hand diagram lives in this band
DIAG_Y0, DIAG_Y1 = 56, 364


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_open(w, h, title, desc=None):
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">',
        f'<title id="t">{esc(title)}</title>',
    ]
    if desc:
        out.append(f"<desc>{esc(desc)}</desc>")
    return out


def base_style(t, extra=""):
    return f"""<style>
.sans {{ font-family: {SANS}; }}
.mono {{ font-family: {MONO}; }}
.tx {{ fill: {t['text']}; }}
.mu {{ fill: {t['muted']}; }}
.clay {{ fill: {t['clay']}; }}
.sage {{ fill: {t['sage']}; }}
.eyebrow {{ font-size: 22px; letter-spacing: 4px; }}
.title {{ font-weight: 700; letter-spacing: -1.5px; }}
.tag {{ font-size: 28px; }}
.node {{ font-size: 24px; font-weight: 600; }}
.sub {{ font-size: 22px; }}
.cap {{ font-size: 22px; }}
.small {{ font-size: 20px; }}
.num {{ font-variant-numeric: tabular-nums; }}
{extra}</style>"""


def card(w, h, t):
    # 1px hairline border drawn on the half-pixel so it stays crisp.
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="20" '
            f'fill="{t["bg"]}" stroke="{t["hair"]}" stroke-width="1"/>')


def hero_left(eyebrow, title, taglines, title_size=76):
    """Left block of the hero: mono eyebrow, big wordmark, up to 3 tagline lines.

    eyebrow: short category in CAPS, e.g. "MACOS MENU-BAR APP" (<= ~24 chars)
    title:   the wordmark, usually the repo name or a shorter form of it
    taglines: 1-3 short lines (<= ~34 characters each at 28px)
    title_size: lower it (min 56) if the title would pass TITLE_MAX_W.
    """
    out = [f'<text class="mono eyebrow mu" x="{LEFT_X}" y="104">{esc(eyebrow)}</text>',
           f'<text class="sans title tx" x="{LEFT_X - 4}" y="190" '
           f'style="font-size:{title_size}px">{esc(title)}</text>']
    for i, line in enumerate(taglines[:3]):
        out.append(f'<text class="sans tag mu" x="{LEFT_X}" y="{250 + 40 * i}">{esc(line)}</text>')
    return out


# ---------------------------------------------------------------- primitives
def node(t, x, y, w, h, label, sub=None, dot="clay", rx=14):
    """Rounded panel with a coloured dot, a bold label and an optional muted sub-line.
    (x, y) is the top-left corner. Height 48 fits a label only; 100 fits label + sub."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
           f'fill="{t["panel"]}" stroke="{t["node"]}" stroke-width="1.5"/>']
    if sub is None:
        cy = y + h / 2
        if dot:
            out.append(f'<circle cx="{x + 22}" cy="{cy}" r="5" fill="{t[dot]}"/>')
        out.append(f'<text class="sans node tx" x="{x + (36 if dot else 20)}" y="{cy + 8}">{esc(label)}</text>')
    else:
        if dot:
            out.append(f'<circle cx="{x + 22}" cy="{y + 32}" r="5" fill="{t[dot]}"/>')
        out.append(f'<text class="sans node tx" x="{x + (36 if dot else 20)}" y="{y + 40}">{esc(label)}</text>')
        out.append(f'<text class="sans sub mu" x="{x + (36 if dot else 20)}" y="{y + 72}">{esc(sub)}</text>')
    return out


def curve(x1, y1, x2, y2, stem=22):
    """Horizontal S-curve connector path data from (x1,y1) to (x2,y2)."""
    s = x1 + stem
    c = (s + x2) / 2
    return f"M{x1} {y1} H{s} C{c} {y1} {c} {y2} {x2} {y2}"


def connectors(t, paths, width=2):
    out = [f'<g fill="none" stroke="{t["conn"]}" stroke-width="{width}" '
           'stroke-linecap="round" stroke-linejoin="round">']
    out += [f'<path d="{d}"/>' for d in paths]
    out.append("</g>")
    return out


def bar(t, x, y, w, h, frac, color="clay", track=True, rx=None):
    """Horizontal meter: a recessive track plus a filled part (0..1, may exceed 1)."""
    rx = h / 2 if rx is None else rx
    out = []
    if track:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{t["grid"]}"/>')
    fw = max(h, w * frac)
    out.append(f'<rect x="{x}" y="{y}" width="{fw:.1f}" height="{h}" rx="{rx}" fill="{t[color]}"/>')
    return out


def arc_path(cx, cy, r, a0, a1):
    """SVG arc path, angles in degrees (0 = 3 o'clock, clockwise positive)."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return f"M{x0:.1f} {y0:.1f} A{r} {r} 0 {large} {sweep} {x1:.1f} {y1:.1f}"


def monotone(xs, ys, step=0.25):
    """Fritsch-Carlson monotone cubic interpolation, sampled every `step`."""
    n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0] * (n - 2) + [d[-1]]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        h = a * a + b * b
        if h > 9:
            tau = 3 / math.sqrt(h)
            m[i], m[i + 1] = tau * a * d[i], tau * b * d[i]
    out = []
    for i in range(n - 1):
        x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
        hh = x1 - x0
        k = max(1, int(round(hh / step)))
        for j in range(k):
            tt = j / k
            h00 = 2 * tt**3 - 3 * tt**2 + 1
            h10 = tt**3 - 2 * tt**2 + tt
            h01 = -2 * tt**3 + 3 * tt**2
            h11 = tt**3 - tt**2
            out.append((x0 + tt * hh, h00 * y0 + h10 * hh * m[i] + h01 * y1 + h11 * hh * m[i + 1]))
    out.append((xs[-1], ys[-1]))
    return out


def terminal(t, title, lines, markup=None, W=1280, bar_h=60, lh=35, size=23):
    """Terminal-window figure. `lines` are plain strings copied VERBATIM from the repo
    (README code blocks or real program output already in the repo, never invented).
    `markup(i, line)` may return inner markup for colouring a line (escape text with esc)."""
    first = bar_h + 56
    H = first + lh * (len(lines) - 1) + 46
    s = svg_open(W, H, f"Terminal: {title}. " + " / ".join(lines)[:600])
    s.append(base_style(t, f".term {{ font-size: {size}px; white-space: pre; }}\n"
                           ".wtitle { font-size: 22px; font-weight: 500; }\n"))
    s.append(f'<defs><clipPath id="win"><rect x="0.5" y="0.5" width="{W - 1}" '
             f'height="{H - 1}" rx="20"/></clipPath></defs>')
    s.append(card(W, H, t))
    s.append(f'<rect x="0" y="0" width="{W}" height="{bar_h}" fill="{t["panel"]}" clip-path="url(#win)"/>')
    s.append(f'<line x1="0" y1="{bar_h - 0.5}" x2="{W}" y2="{bar_h - 0.5}" stroke="{t["hair"]}" stroke-width="1"/>')
    s.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" '
             f'stroke="{t["hair"]}" stroke-width="1"/>')
    for k in range(3):
        s.append(f'<circle cx="{38 + 26 * k}" cy="{bar_h / 2}" r="7" fill="{t["dots"]}"/>')
    s.append(f'<text class="sans wtitle mu" x="{W / 2}" y="{bar_h / 2 + 8}" text-anchor="middle">{esc(title)}</text>')
    for i, line in enumerate(lines):
        inner = markup(i, line) if markup else esc(line)
        if markup is None and line.startswith("$ "):
            inner = f'<tspan class="mu">$</tspan>{esc(line[1:])}'
        s.append(f'<text class="mono term tx" xml:space="preserve" x="48" y="{first + lh * i}">{inner}</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


# ------------------------------------------------------------------ writer
def write_all(builders):
    """builders: {"hero": fn(t) -> svg string, ...}. Writes <name>-{dark,light}.svg."""
    for name, fn in builders.items():
        for mode, t in THEMES.items():
            path = os.path.join(OUT, f"{name}-{mode}.svg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(fn(t))
            print("wrote", os.path.relpath(path))


# ============================================================================
# mlx-device-bench figures. Every number is copied from README.md (which takes
# it from results/summaries/) or read from the logs in results/.
# ============================================================================
REPO = os.path.dirname(OUT)


def hero(t):
    W, H = HERO_W, HERO_H
    s = svg_open(W, H, "mlx-device-bench: the same greedy MLX workload on a Mac Studio (M5 Max) "
                       "and an iPhone 18 Pro Max. Median generation speed: Qwen3-1.7B-4bit 304.7 "
                       "tokens/s on the Mac and 99.7 on the iPhone; Qwen3-4B-4bit 147.9 and 44.6.")
    s.append(base_style(t))
    s.append(card(W, H, t))
    s += hero_left("ON-DEVICE LLM BENCHMARK", "mlx-device-bench",
                   ["Apple MLX on a Mac and an iPhone.",
                    "Speed, power, thermal throttling.",
                    "Neural-accelerator on/off ablation."], title_size=64)

    x0 = 700                     # bar origin
    k = 400 / 304.7              # px per token/s: the Mac's 1.7B bar is 400px long
    s.append(f'<text class="mono cap mu" x="{x0}" y="104">generation · median tokens/s</text>')
    groups = [("Qwen3-1.7B-4bit", 304.7, "304.7", 99.7, "99.7", 152),
              ("Qwen3-4B-4bit", 147.9, "147.9", 44.6, "44.6", 254)]
    for name, mac, mac_s, ip, ip_s, gy in groups:
        s.append(f'<text class="sans node tx" x="{x0}" y="{gy}">{esc(name)}</text>')
        for j, (v, lab, col) in enumerate(((mac, mac_s, "clay"), (ip, ip_s, "sage"))):
            by = gy + 14 + 28 * j
            s += bar(t, x0, by, v * k, 20, 1.0, color=col, track=False, rx=4)
            s.append(f'<text class="mono small num tx" x="{x0 + v * k + 14:.1f}" y="{by + 17}">{lab}</text>')
    # legend
    s.append(f'<circle cx="{x0 + 6}" cy="349" r="6" fill="{t["clay"]}"/>')
    s.append(f'<text class="sans small mu" x="{x0 + 22}" y="356">Mac Studio · M5 Max</text>')
    s.append(f'<circle cx="{x0 + 256}" cy="349" r="6" fill="{t["sage"]}"/>')
    s.append(f'<text class="sans small mu" x="{x0 + 272}" y="356">iPhone 18 Pro Max</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


# ---------------------------------------------------------------- thermal
def sustain_points(log, model="Qwen3-4B-4bit"):
    """(seconds into the sustain phase, tokens/s) of every sustain iteration in a log."""
    import json
    pts = []
    with open(os.path.join(REPO, "results", log), encoding="utf-8") as f:
        for line in f:
            if not line.startswith("BENCH "):
                continue
            e = json.loads(line[6:])
            if (e.get("event") == "run" and e.get("workload") == "sustain"
                    and e.get("model", "").endswith(model)):
                pts.append((e["elapsedInPhase"], e["tokensPerSecond"]))
    return pts


def thermal(t):
    W, H = 1280, 540
    run1 = sustain_points("iphone18promax.log")
    run2 = sustain_points("iphone18promax-cooled.log")
    assert run1 and run2
    X0, X1, XD = 128, 1084, 106.0          # x: 0 .. 106 s
    YB, YT, Y0, Y1 = 436, 116, 34.0, 47.0   # y: 34 .. 47 tokens/s

    def px(x):
        return X0 + (X1 - X0) * x / XD

    def py(y):
        return YB - (YB - YT) * (y - Y0) / (Y1 - Y0)

    s = svg_open(W, H, "Qwen3-4B-4bit on the iPhone 18 Pro Max, tokens/s of each iteration during "
                       "100 s of continuous generation. Run 1 (in a case, no cooler) holds 44.5 for "
                       "about 40 s, then drops to about 39 and ends at 39.5 while the thermal state "
                       "rises from 1 to 2. Run 2 (no case, external cooler) stays at 44.7 with "
                       "thermal state 0.")
    s.append(base_style(t, ".tick { font-size: 22px; }\n.lab { font-size: 22px; }\n.labb { font-weight: 600; }\n"))
    s.append(card(W, H, t))
    s.append(f'<g stroke="{t["grid"]}" stroke-width="1.5" fill="none">')
    for v in (40, 45):
        s.append(f'<line x1="{X0}" y1="{py(v):.1f}" x2="{X1}" y2="{py(v):.1f}"/>')
    for v in (20, 40, 60, 80, 100):
        s.append(f'<line x1="{px(v):.1f}" y1="{YT}" x2="{px(v):.1f}" y2="{YB}"/>')
    s.append("</g>")
    s.append(f'<path d="M{X0} {YT} V{YB} H{X1}" fill="none" stroke="{t["axis"]}" stroke-width="1.5"/>')
    for v in (35, 40, 45):
        s.append(f'<text class="sans tick mu num" x="{X0 - 16}" y="{py(v) + 8:.1f}" text-anchor="end">{v}</text>')
    for v in (0, 20, 40, 60, 80, 100):
        s.append(f'<text class="sans tick mu num" x="{px(v):.1f}" y="{YB + 38}" text-anchor="middle">{v} s</text>')
    s.append(f'<text class="sans tick mu" x="40" y="64">Qwen3-4B-4bit on iPhone · tokens/s per iteration</text>')
    s.append(f'<text class="sans tick mu" x="{X1}" y="{YB + 82}" text-anchor="end">time into the 100 s sustain phase</text>')

    for pts, col in ((run2, "sage"), (run1, "clay")):
        d = "M" + " L".join(f"{px(x):.1f} {py(y):.1f}" for x, y in pts)
        s.append(f'<path d="{d}" fill="none" stroke="{t[col]}" stroke-width="3" '
                 'stroke-linejoin="round" stroke-linecap="round"/>')
        for x, y in pts:
            s.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4.5" fill="{t[col]}" '
                     f'stroke="{t["bg"]}" stroke-width="2"/>')
    # end values (README: run 1 first -> last 44.5 -> 39.5; run 2 44.7 -> 44.7)
    ex = px(max(run1[-1][0], run2[-1][0])) + 22
    s.append(f'<text class="sans lab labb num" x="{ex:.1f}" y="{py(run2[-1][1]) + 8:.1f}" fill="{t["sage"]}">44.7</text>')
    s.append(f'<text class="sans lab labb num" x="{ex:.1f}" y="{py(run1[-1][1]) + 8:.1f}" fill="{t["clay"]}">39.5</text>')
    # direct labels
    s.append(f'<text class="sans lab mu" x="{px(49):.1f}" y="{py(44.7) - 26:.1f}">'
             f'<tspan class="labb sage">run 2</tspan> · no case, external cooler · thermal state 0</text>')
    s.append(f'<text class="sans lab mu" x="{px(49):.1f}" y="{py(39.4) - 34:.1f}">'
             f'<tspan class="labb clay">run 1</tspan> · in a case, no cooler · thermal state 1 → 2</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


# ---------------------------------------------------------------- NAX ablation
def nax(t):
    W, H = 1280, 600
    s = svg_open(W, H, "NAX ablation on the Mac, three runs in the order NAX on, NAX off, NAX on. "
                       "Prompt processing (sustain-prefill, per-iteration median, prompt tokens/s): "
                       "Qwen3-1.7B-4bit 8,837 / 2,489 / 8,785, off divided by mean(on) 0.28; "
                       "Qwen3-4B-4bit 3,672 / 1,027 / 3,669, 0.28. Decode (sustain, per-iteration "
                       "median, tokens/s): 1.7B 302.3 / 296.0 / 300.9, 0.98; 4B 145.3 / 139.4 / 138.9, 0.98.")
    s.append(base_style(t, ".ptitle { font-size: 26px; font-weight: 700; }\n.val { font-size: 21px; }\n"))
    s.append(card(W, H, t))
    YB, HMAX = 426, 250
    panels = [
        (72, "Prompt processing", "sustain-prefill · prompt tokens/s", 9000.0,
         [("Qwen3-1.7B-4bit", [8837, 2489, 8785], "0.28"),
          ("Qwen3-4B-4bit", [3672, 1027, 3669], "0.28")], "{:,.0f}"),
        (680, "Decode", "sustain · tokens/s", 320.0,
         [("Qwen3-1.7B-4bit", [302.3, 296.0, 300.9], "0.98"),
          ("Qwen3-4B-4bit", [145.3, 139.4, 138.9], "0.98")], "{:.1f}"),
    ]
    BW, GAP, GGAP = 58, 14, 92
    for x, title, sub, vmax, groups, fmt in panels:
        s.append(f'<text class="sans ptitle tx" x="{x}" y="76">{esc(title)}</text>')
        s.append(f'<text class="sans small mu" x="{x}" y="108">per-iteration median · {esc(sub)}</text>')
        gx = x + 16
        for name, vals, ratio in groups:
            for j, v in enumerate(vals):
                bx = gx + j * (BW + GAP)
                h = HMAX * v / vmax
                col = "clay" if j == 1 else "sage"
                s.append(f'<rect x="{bx}" y="{YB - h:.1f}" width="{BW}" height="{h:.1f}" rx="4" fill="{t[col]}"/>')
                s.append(f'<text class="sans val tx num" x="{bx + BW / 2}" y="{YB - h - 12:.1f}" '
                         f'text-anchor="middle">{fmt.format(v)}</text>')
                lab = ("on 1", "off", "on 2")[j]
                s.append(f'<text class="mono small {col}" x="{bx + BW / 2}" y="{YB + 32}" '
                         f'text-anchor="middle">{lab}</text>')
            gw = 3 * BW + 2 * GAP
            s.append(f'<text class="sans sub tx" x="{gx + gw / 2}" y="{YB + 74}" text-anchor="middle">{esc(name)}</text>')
            s.append(f'<text class="sans small mu" x="{gx + gw / 2}" y="{YB + 106}" text-anchor="middle">'
                     f'off ÷ mean(on): <tspan class="clay">{ratio}</tspan></text>')
            gx += gw + GGAP
        s.append(f'<line x1="{x}" y1="{YB + 0.75}" x2="{x + 16 + 2 * (3 * BW + 2 * GAP) + GGAP + 16}" '
                 f'y2="{YB + 0.75}" stroke="{t["axis"]}" stroke-width="1.5"/>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


BUILDERS = {"hero": hero, "thermal": thermal, "nax": nax}

if __name__ == "__main__":
    sys.exit(write_all(BUILDERS))
