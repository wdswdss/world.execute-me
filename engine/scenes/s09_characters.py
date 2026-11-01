"""s09_characters - four material forms, each with a big concrete character
animation framed by program UI (stats panels, feed particles, IDs, brackets).

74.040  If I'm an eggplant, then I will give you my nutrients
77.732  If I'm a tomato,   then I will give you antioxidants
81.424  If I'm a tabby cat,then I will purr for your enjoyment
85.117  If I'm the only god,then you're the proof of my existence

Each lyric gets two bars: one character, 27-32 stage rows tall, bobbing on the
beat, blinking, blushing, with a speech bubble, live counters and particles
feeding into it.  Faces are drawn at cell level (white eye blocks + dark pupils)
on top of the organic art-mask silhouette, so every form stays readable.
Transitions are a scan wipe + pop + glitch on the downbeat.
"""
from __future__ import annotations

import math

import numpy as np

from .. import art
from .. import font as F
from .. import fx
from .. import layout as L
from .. import palette as P
from .. import widgets as W
from ..art import (_arc, _canvas, _circ, _ell, _fin, _line, _poly,
                   _star_poly)

PANEL = P.C["panel"]
PANEL2 = P.C["panel2"]
VOID = P.C["void"]
LINE = P.C["line"]
WHITE = P.C["white"]

SEG_T0 = (74.040, 77.732, 81.424, 85.117)
SEG_T1 = (77.732, 81.424, 85.117, 88.810)

SEGS = (
    {
        "key": "EGGPLANT", "index": "01", "id": "0xEA01", "form": "SOLANUM MELONGENA",
        "accent": "violet", "word": "NUTRIENTS",
        "sub": "NUTRIENT TRANSFER  //  TAKE ALL OF ME",
        "bubble": "EAT ME. I AM 100% NUTRIENTS.",
        "log": ("> form loaded: eggplant", "> nutrients: N, P, K, Fe, Mg",
                "> delivery port: MOUTH", "> consent: GIVEN"),
    },
    {
        "key": "TOMATO", "index": "02", "id": "0xTB02", "form": "SOLANUM LYCOPERSICUM",
        "accent": "red", "word": "ANTIOXIDANTS",
        "sub": "ANTIOXIDANT PACKAGE  //  LYC 4.2 MG / 100G",
        "bubble": "EAT ME. I WILL KEEP YOU YOUNG.",
        "log": ("> form loaded: tomato", "> antioxidants: LYC, VC, VE",
                "> free radicals: PURGED", "> skin: PROTECTED"),
    },
    {
        "key": "TABBY CAT", "index": "03", "id": "0xCB03", "form": "FELIS CATUS",
        "accent": "gold", "word": "PURR",
        "sub": "PURR ENGINE  //  25 HZ  //  YOUR ENJOYMENT +100",
        "bubble": "MRRRROW. PURRING FOR YOU.",
        "log": ("> form loaded: tabby cat", "> purr frequency: 25 Hz",
                "> enjoyment: RISING", "> scratch risk: NOMINAL"),
    },
    {
        "key": "ONLY GOD", "index": "04", "id": "0xGD04", "form": "DEUS SOLUS",
        "accent": "gold", "word": "PROOF",
        "sub": "EXISTENCE PROOF  //  WITNESS: YOU",
        "bubble": "YOU ARE MY PROOF.",
        "log": ("> form loaded: only god", "> worshipper: DETECTED",
                "> existence: CONFIRMED", "> proof source: TARGET"),
    },
)


# ------------------------------------------------ art fallback (engine bugs) --
# engine/art.py:eggplant passes a bare float into _poly and tomato calls a
# missing `_circle`; rebuild the same masks here so the scene always renders.
_ART_BROKEN = set()


def _local_eggplant(w=320, h=390):
    out = {}
    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.66, w * 0.34, h * 0.28)
    _poly(d, [(w * 0.36, h * 0.20), (w * 0.66, h * 0.20),
              (w * 0.72, h * 0.48), (w * 0.30, h * 0.48)])
    _ell(d, w * 0.36, h * 0.30, w * 0.10, h * 0.11)
    _ell(d, w * 0.66, h * 0.30, w * 0.10, h * 0.11)
    out["body"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        tipx = w * 0.50 + math.cos(a) * w * 0.20
        tipy = h * 0.22 + math.sin(a) * h * 0.10
        mid = a + 0.32
        p1 = (w * 0.50 + math.cos(mid - 0.4) * w * 0.09,
              h * 0.22 + math.sin(mid - 0.4) * h * 0.05)
        p2 = (w * 0.50 + math.cos(mid + 0.4) * w * 0.09,
              h * 0.22 + math.sin(mid + 0.4) * h * 0.05)
        _poly(d, [(w * 0.50, h * 0.235), (tipx, tipy), p1, p2])
    out["leaf"] = _fin(im, w, h, blur=1.0)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.455, h * 0.06), (w * 0.545, h * 0.05),
              (w * 0.535, h * 0.235), (w * 0.465, h * 0.235)])
    _ell(d, w * 0.545, h * 0.055, w * 0.028, h * 0.022)
    out["stem"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    _ell(d, w * 0.40, h * 0.60, w * 0.075, h * 0.15)
    _ell(d, w * 0.435, h * 0.60, w * 0.070, h * 0.14, fill=0)
    out["shine"] = _fin(im, w, h, blur=1.0)

    eye_l = (w * 0.38, h * 0.60, w * 0.052)
    eye_r = (w * 0.62, h * 0.60, w * 0.052)
    out["eyes"] = (eye_l, eye_r)
    return out


def _local_tomato(w=340, h=340):
    out = {}
    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.58, w * 0.40, h * 0.37)
    out["body"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    _poly(d, _star_poly(w * 0.50, h * 0.235, 6, w * 0.26, w * 0.10))
    out["leaf"] = _fin(im, w, h, blur=1.0)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.485, h * 0.10), (w * 0.525, h * 0.09),
              (w * 0.520, h * 0.235), (w * 0.480, h * 0.235)])
    out["stem"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    _ell(d, w * 0.36, h * 0.44, w * 0.115, h * 0.075)
    out["shine"] = _fin(im, w, h, blur=1.2)

    eye_l = (w * 0.38, h * 0.55, w * 0.05)
    eye_r = (w * 0.62, h * 0.55, w * 0.05)
    out["eyes"] = (eye_l, eye_r)
    return out



def _local_girl(w=300, h=522):
    """Blue-haired cat-eared maid girl (qa/ref_god.png), masks sized for cells."""
    out = {}
    cx = w * 0.50

    # hair: crown hugging the head + long wavy side locks
    im, d = _canvas(w, h)
    _ell(d, cx, h * 0.285, w * 0.255, h * 0.215)
    _ell(d, cx, h * 0.360, w * 0.270, h * 0.200)
    _poly(d, [(w * 0.245, h * 0.26), (w * 0.34, h * 0.22),
              (w * 0.30, h * 0.72), (w * 0.155, h * 1.0)])
    _poly(d, [(w * 0.755, h * 0.26), (w * 0.66, h * 0.22),
              (w * 0.70, h * 0.72), (w * 0.845, h * 1.0)])
    for i in range(7):
        _ell(d, w * (0.17 + 0.055 * i), h * (0.94 + 0.02 * (i % 3)),
             w * 0.055, h * 0.05)
    out["hair"] = _fin(im, w, h, blur=2.0)

    # bright cyan highlight streaks
    im, d = _canvas(w, h)
    for i in range(5):
        x0 = w * (0.30 + 0.035 * i)
        _line(d, [(x0, h * 0.19), (x0 - w * 0.03, h * 0.40),
                  (x0 - w * 0.02, h * 0.58), (x0 - w * 0.05, h * 0.80)], width=6)
        _line(d, [(w - x0, h * 0.19), (w - x0 + w * 0.03, h * 0.40),
                  (w - x0 + w * 0.02, h * 0.58), (w - x0 + w * 0.05, h * 0.80)],
              width=6)
    _ell(d, cx, h * 0.165, w * 0.11, h * 0.045)
    out["hair_hi"] = _fin(im, w, h, blur=1.6)

    # cat ears at the sides of the crown
    im, d = _canvas(w, h)
    _poly(d, [(w * 0.315, h * 0.155), (w * 0.115, h * 0.020), (w * 0.400, h * 0.085)])
    _poly(d, [(w * 0.685, h * 0.155), (w * 0.885, h * 0.020), (w * 0.600, h * 0.085)])
    out["ears"] = _fin(im, w, h, blur=0.9)
    im, d = _canvas(w, h)
    _poly(d, [(w * 0.325, h * 0.140), (w * 0.205, h * 0.058), (w * 0.382, h * 0.100)])
    _poly(d, [(w * 0.675, h * 0.140), (w * 0.795, h * 0.058), (w * 0.618, h * 0.100)])
    out["inner_ear"] = _fin(im, w, h, blur=0.7)

    # big face + neck
    im, d = _canvas(w, h)
    _ell(d, cx, h * 0.345, w * 0.185, h * 0.140)
    _poly(d, [(w * 0.445, h * 0.445), (w * 0.555, h * 0.445),
              (w * 0.575, h * 0.585), (w * 0.425, h * 0.585)])
    out["skin"] = _fin(im, w, h, blur=1.3)

    # navy dress: torso + puffed sleeves
    im, d = _canvas(w, h)
    _poly(d, [(w * 0.30, h * 0.575), (w * 0.70, h * 0.575),
              (w * 0.86, h * 1.02), (w * 0.14, h * 1.02)])
    _ell(d, w * 0.155, h * 0.735, w * 0.125, h * 0.135)
    _ell(d, w * 0.845, h * 0.735, w * 0.125, h * 0.135)
    out["dress"] = _fin(im, w, h, blur=1.3)

    # white apron panel + collar ruffles
    im, d = _canvas(w, h)
    _poly(d, [(w * 0.385, h * 0.605), (w * 0.615, h * 0.605),
              (w * 0.655, h * 1.02), (w * 0.345, h * 1.02)])
    for i in range(9):
        _circ(d, w * (0.300 + 0.050 * i), h * 0.600, w * 0.030)
    out["apron"] = _fin(im, w, h, blur=1.1)

    # white frilled headband across the crown (sits above the face)
    im, d = _canvas(w, h)
    _ell(d, cx, h * 0.150, w * 0.200, h * 0.085)
    _ell(d, cx, h * 0.150, w * 0.150, h * 0.045, fill=0)
    _poly(d, [(0, h * 0.190), (w, h * 0.190), (w, h), (0, h)], fill=0)
    for i in range(11):
        a = math.pi * (1.04 + 0.092 * i)
        _circ(d, cx + math.cos(a) * w * 0.200,
              h * 0.150 + math.sin(a) * h * 0.092, w * 0.022)
    out["headband"] = _fin(im, w, h, blur=0.9)

    # neck ribbon bow + gem knot
    im, d = _canvas(w, h)
    _poly(d, [(w * 0.50, h * 0.545), (w * 0.335, h * 0.498), (w * 0.352, h * 0.612)])
    _poly(d, [(w * 0.50, h * 0.545), (w * 0.665, h * 0.498), (w * 0.648, h * 0.612)])
    _circ(d, w * 0.50, h * 0.548, w * 0.030)
    out["ribbon"] = _fin(im, w, h, blur=0.8)

    # fringe strands over the forehead, above the eyes
    im, d = _canvas(w, h)
    _ell(d, cx, h * 0.225, w * 0.175, h * 0.045)
    _poly(d, [(w * 0.400, h * 0.195), (w * 0.470, h * 0.185), (w * 0.445, h * 0.285)])
    _poly(d, [(w * 0.520, h * 0.190), (w * 0.585, h * 0.200), (w * 0.588, h * 0.280)])
    out["hair_front"] = _fin(im, w, h, blur=1.0)

    # blush + open smiling mouth
    im, d = _canvas(w, h)
    _ell(d, w * 0.335, h * 0.395, w * 0.040, h * 0.018)
    _ell(d, w * 0.665, h * 0.395, w * 0.040, h * 0.018)
    out["blush"] = _fin(im, w, h, blur=2.2)
    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.425, w * 0.032, h * 0.017)
    out["mouth"] = _fin(im, w, h, blur=0.8)

    out["eyes"] = ((w * 0.39, h * 0.345, w * 0.05),
                   (w * 0.61, h * 0.345, w * 0.05))
    return out

_MASKS = {}


def _local_tabby(w=380, h=410):
    out = {}
    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.99, w * 0.40, h * 0.30)
    _ell(d, w * 0.50, h * 0.50, w * 0.29, h * 0.26)
    _poly(d, [(w * 0.26, h * 0.40), (w * 0.20, h * 0.10), (w * 0.46, h * 0.28)])
    _poly(d, [(w * 0.74, h * 0.40), (w * 0.80, h * 0.10), (w * 0.54, h * 0.28)])
    out["body"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.30, h * 0.34), (w * 0.26, h * 0.17), (w * 0.41, h * 0.28)])
    _poly(d, [(w * 0.70, h * 0.34), (w * 0.74, h * 0.17), (w * 0.59, h * 0.28)])
    out["inner_ear"] = _fin(im, w, h, blur=0.6)

    im, d = _canvas(w, h)
    _line(d, [(w * 0.44, h * 0.30), (w * 0.47, h * 0.40)], width=3)
    _line(d, [(w * 0.50, h * 0.29), (w * 0.50, h * 0.41)], width=3)
    _line(d, [(w * 0.56, h * 0.30), (w * 0.53, h * 0.40)], width=3)
    for i, dy in enumerate((0.0, 0.035, 0.07)):
        _line(d, [(w * 0.20, h * (0.50 + dy)), (w * 0.30, h * (0.49 + dy))], width=2)
        _line(d, [(w * 0.80, h * (0.50 + dy)), (w * 0.70, h * (0.49 + dy))], width=2)
    out["stripes"] = _fin(im, w, h, blur=0.5)

    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.60, w * 0.14, h * 0.095)
    out["muzzle"] = _fin(im, w, h, blur=1.0)

    eye_l = (w * 0.40, h * 0.49, w * 0.075)
    eye_r = (w * 0.60, h * 0.49, w * 0.075)
    out["eyes"] = (eye_l, eye_r)
    return out


def _masks(name):
    """characters dict, tolerant of the two broken engine art builders."""
    m = _MASKS.get(name)
    if m is not None:
        return m
    m = {"eggplant": _local_eggplant, "tomato": _local_tomato,
         "tabby": _local_tabby, "girl": _local_girl}[name]()
    _MASKS[name] = m
    return m


# --------------------------------------------------------------- sprite caches
_SPR = {}
_SPR_A = {}


def _spr(masks, name, w, h):
    """Mask resized once to the exact cell pixel grid so paint_mask skips PIL."""
    key = (id(masks), name, w, h)
    m = _SPR.get(key)
    if m is None:
        arr = masks[name]
        m = arr if arr.shape == (h * L.CELL_H, w * L.CELL_W) else \
            F.resize_mask(arr, w * L.CELL_W, h * L.CELL_H)
        if len(_SPR) > 420:
            _SPR.clear()
        _SPR[key] = m
    return m


def _spr_arr(arr, w, h):
    key = (id(arr), w, h)
    m = _SPR_A.get(key)
    if m is None:
        m = arr if arr.shape == (h * L.CELL_H, w * L.CELL_W) else \
            F.resize_mask(arr, w * L.CELL_W, h * L.CELL_H)
        if len(_SPR_A) > 200:
            _SPR_A.clear()
        _SPR_A[key] = m
    return m


def _paint(fr, masks, name, c0, r0, w, h, fg, fg2=None, ramp=None, gain=1.0,
           alpha=1.0, min_v=0.05, bg=VOID):
    fr.paint_mask(_spr(masks, name, w, h), c0, r0, w, h, ramp=ramp,
                  fg=fg, fg2=fg2, bg=bg, gain=gain, alpha=alpha, min_v=min_v)


def _shade_rows(fr, r0, c0, w, h, step=3, f=0.72):
    """Darken every `step`-th body row so a flat mask fill gets scanline depth."""
    a = max(0, c0)
    b = min(fr.cols, c0 + w)
    if b <= a:
        return
    for r in range(max(0, r0), min(fr.rows, r0 + h), step):
        fr.fg[r, a:b] = (fr.fg[r, a:b].astype(np.float32) * f).astype(np.uint8)


# ------------------------------------------------------------------ helpers --
def _box(fr, r0, c0, r1, c1, title, accent, bg=PANEL2, style=1):
    fr.fill_rect(r0, c0, r1, c1, " ", bg=bg)
    fr.box(r0, c0, r1, c1, style, fg=P.mix(accent, VOID, 0.5), bg=bg)
    if title:
        fr.write(r0, c0 + 2, f"┤ {title} ├", fg=accent, bg=bg)


def _bar(fr, r, c, w, frac, color, bg=PANEL2):
    W.progress_bar(fr, r, c, w, frac, fg=color, bg=bg, show_pct=False)


def _stat_rows(fr, r0, c0, c1, specs, bg=PANEL2):
    """specs: (label, frac, value, colour_name)."""
    for i, (label, frac, val, colname) in enumerate(specs):
        r = r0 + i * 2
        col = P.C[colname]
        fr.write(r, c0, label, fg=P.C["dim"], bg=bg)
        _bar(fr, r, c0 + 7, 18, frac, col, bg=bg)
        fr.write(r, c1 - 7, val, fg=col, bg=bg)


def _aura(fr, cx, cy, rx, ry, t, color, n=64, ch="·", bright=0.5, spin=0.6):
    for k in range(n):
        a = k / n * 2 * math.pi + t * spin
        x = int(round(cx + math.cos(a) * rx))
        y = int(round(cy + math.sin(a) * ry))
        if fr.inb(y, x):
            fr.put(y, x, ch, fg=P.mix(color, VOID, bright))


def _sparkles(fr, t, n, seed, cx, cy, sx, sy, color):
    for k in range(n):
        ph = fx.hash01(k, seed, 1)
        p = (t * (0.45 + fx.hash01(k, seed, 2) * 0.8) + ph) % 1.0
        ang = fx.hash01(k, seed, 3) * 6.2831
        rad = 0.55 + 0.65 * fx.hash01(k, seed, 4)
        x = int(cx + math.cos(ang) * sx * rad + math.sin(t * 1.7 + k) * 1.5)
        y = int(cy + math.sin(ang) * sy * rad)
        if not fr.inb(y, x):
            continue
        if p > 0.86:
            ch, col = "✦", WHITE
        elif p > 0.62:
            ch, col = "+", P.mix(color, WHITE, 0.5)
        else:
            ch, col = "·", P.mix(color, VOID, 0.3 + 0.45 * p)
        fr.put(y, x, ch, fg=col)


def _feed(fr, t, target, color, n=22, seed=3):
    """Glyphs streaming from both page edges into the character mouth."""
    tx, ty = target
    for k in range(n):
        period = 0.9 + fx.hash01(k, seed) * 1.1
        p = ((t / period) + fx.hash01(k, seed, 1)) % 1.0
        side = -1 if k % 2 else 1
        sx = 45 if side < 0 else 147
        sy = 6 + fx.hash01(k, seed, 2) * 22
        e = fx.ease_in(fx.clamp((p - 0.2) / 0.8))
        x = int(fx.lerp(sx, tx, e)) + int(math.sin(p * 9 + k) * 2 * (1 - e))
        y = int(fx.lerp(sy, ty, e)) + int(math.cos(p * 7 + k) * 3 * (1 - e))
        if not fr.inb(y, x):
            continue
        col = P.mix(color, WHITE, 0.35 * (1 - p))
        ch = "●" if p > 0.75 else ("○" if p > 0.45 else "·")
        fr.put(y, x, ch, fg=col)


def _rna(fr, ctx, c0, r0, h, side=1):
    """mRNA strand: sugar-phosphate backbone + A/U/G/C bases on short ticks."""
    t = ctx.t
    seq = "AUG" + "CUG" + "GAU" + "UAC" + "GGC" + "UAA"
    cols = (P.C["green"], P.C["amber"], P.C["primary"], P.C["magenta"])
    bidx = {"A": 0, "U": 1, "G": 2, "C": 3}
    dim = P.mix(P.C["violet"], VOID, 0.35)
    bond = P.mix(P.C["violet"], VOID, 0.2)
    pol = (t * 4.6) % (h + 4) - 2.0
    for i in range(h):
        y = r0 + i
        if not fr.inb(y, c0):
            continue
        x = c0 + int(round(math.sin(i * 0.42 + t * 1.5) * 2.2))
        ch = "●" if i % 3 == 0 else "│"
        fr.put(y, x, ch, fg=dim if i % 3 else bond)
        sd = side if (i // 2) % 2 == 0 else -side
        base = seq[i % len(seq)]
        col = cols[bidx[base]]
        near = abs(i - pol) < 1.6
        if near:
            col = P.mix(col, WHITE, 0.55)
        bx = x + sd * 2
        if fr.inb(y, bx):
            fr.put(y, bx, "─", fg=P.mix(bond, VOID, 0.1))
        bx2 = x + sd * 3
        if not fr.inb(y, bx2):
            bx2 = bx
        fr.put(y, bx2, base, fg=col)
    # 5' / 3' caps
    fr.write(r0 - 1, c0 - 2, "5'", fg=P.mix(P.C["violet"], WHITE, 0.35))
    fr.write(r0 + h, c0 - 2, "3'", fg=P.mix(P.C["violet"], VOID, 0.2))
    # polymerase marker
    py = int(round(r0 + pol))
    if r0 <= py < r0 + h and fr.inb(py, c0 - 6):
        fr.write(py, c0 - 6, "◉POL", fg=P.mix(P.C["gold"], WHITE, 0.4))


def _rna_panel(fr, ctx, r0, c0, c1, accent, side=1):
    """Small readout box for the mRNA strand."""
    t = ctx.t
    _box(fr, r0, c0, r0 + 5, c1, "┤ mRNA ├", accent)
    fr.write(r0 + 1, c0 + 2, "TRANSCRIPT", fg=P.C["dim"], bg=PANEL2)
    fr.write(r0 + 2, c0 + 2, "BASES  A U G C", fg=P.C["primary"], bg=PANEL2)
    rate = 18 + int(7 * abs(math.sin(t * 2.1)))
    fr.write(r0 + 3, c0 + 2, f"CODON RATE {rate:2d}/s", fg=P.C["gold"], bg=PANEL2)
    fr.write(r0 + 4, c0 + 2, "5' CAP AUG -> 3'", fg=P.C["green"], bg=PANEL2)


def _eye_pair(fr, cx, row, dx, blink=False, ew=3, eh=2, bgc=WHITE, pc=VOID,
              slit=False, look=0):
    """Two crisp cell-level eyes: bright block + dark pupil (slit for the cat)."""
    for side in (-1, 1):
        ex = cx + side * dx
        left = ex - ew // 2
        if blink:
            fr.write(row + eh // 2, left, "─" * ew, fg=P.mix(bgc, VOID, 0.15))
            continue
        fr.fill_rect(row, left, row + eh - 1, left + ew - 1, " ", bg=bgc)
        mid = left + ew // 2 + look
        if slit:
            fr.fill_rect(row, mid, row + eh - 1, mid, " ", bg=pc)
        else:
            fr.fill_rect(row + eh - 1, mid, row + eh - 1, mid, " ", bg=pc)
        fr.put(row, left, "·", fg=P.mix(bgc, VOID, 0.2))
        if ew >= 4:
            fr.put(row, left + ew - 1, "·", fg=P.mix(bgc, VOID, 0.15))


def _blush(fr, cx, row, dx, color):
    for side in (-1, 1):
        fr.write(row, cx + side * dx - 1, "▒▒", fg=P.mix(color, VOID, 0.15))


def _mouth(fr, cx, row, color, wide=3, open_=False):
    if open_:
        left = cx - wide
        fr.fill_rect(row, left, row, left + wide * 2, " ", bg=P.dark("crimson", 0.15))
        fr.put(row - 1, left + wide, "▄", fg=color)
    else:
        fr.write(row, cx - wide, "╲" + "▁" * (wide * 2 - 2) + "╱", fg=color)


def _face_eyes(masks, c0, r0, w, h):
    mh, mw = masks["body"].shape
    out = []
    for (ex, ey, er) in masks["eyes"]:
        out.append((c0 + ex / mw * w, r0 + ey / mh * h))
    return out


def _blink_lines(fr, eyes, color):
    for (cx, cy) in eyes:
        fr.write(int(round(cy)), int(round(cx)) - 1, "───", fg=color)


def _edge(masks, name, w, h, frac):
    """Cell cols (left, right) where the resized mask is still solid at row frac."""
    m = _spr(masks, name, w, h)
    ry = min(m.shape[0] - 1, max(0, int(frac * h * L.CELL_H)))
    row = m[ry]
    cols = np.nonzero(row > 0.22)[0]
    if cols.size == 0:
        return None
    return int(cols[0] // L.CELL_W), int(cols[-1] // L.CELL_W)


def _cat_ears(fr, cx, r0, edge_col, inner_col):
    """Two pointed ears (cell triangles) sitting on the head top."""
    for side in (-1, 1):
        b = cx + side * 7
        for k in range(3):
            r = r0 - 2 + k
            half = k + 1
            for d in range(-half, half + 1):
                if not fr.inb(r, b + d):
                    continue
                if abs(d) == half:
                    fr.put(r, b + d, "╱" if d < 0 else "╲", fg=edge_col)
                else:
                    fr.put(r, b + d, "▓", fg=P.mix(edge_col, VOID, 0.45))
            if k >= 1:
                for d in range(-(k - 1), k):
                    if fr.inb(r, b + d):
                        fr.put(r, b + d, "▒", fg=inner_col)


# --------------------------------------------------------- shared UI chrome --
def _top(fr, ctx, si, lt, seg):
    t = ctx.t
    accent = P.C[seg["accent"]]
    VOID2 = P.C["void2"]
    fr.fill_rect(0, 0, 0, fr.cols - 1, " ", bg=VOID2)
    fr.write(0, 2, "CHARACTER.PROGRAM", fg=P.C["primary"], bg=VOID2)
    fr.write(0, 20, "v3.1", fg=P.C["dim"], bg=VOID2)
    for i, s in enumerate(SEGS):
        c = 30 + i * 25
        active = i == si
        fg = P.C["gold"] if active else P.C["dim"]
        fr.write(0, c - 2, "▶" if active else " ", fg=fg, bg=VOID2)
        fr.write(0, c, s["index"] + " " + s["key"], fg=fg, bg=VOID2)
    fr.write(0, 150, f"LINE {(ctx.line_i if ctx.line_i is not None else 0):02d}/24", fg=P.C["dim"], bg=VOID2)
    if int(t * 2) % 2 == 0:
        fr.write(0, 176, "REC", fg=P.C["red"], bg=VOID2)
    fr.put(0, 180, "●", fg=P.C["red"], bg=VOID2)
    # rule + segment progress
    fr.hline(1, 0, 124, "─", fg=P.mix(LINE, VOID, 0.25))
    for c in range(4, 125, 12):
        fr.put(1, c, "┬", fg=P.mix(accent, VOID, 0.55))
    fr.write(1, 130, "SEG", fg=P.C["dim"], bg=VOID2)
    _bar(fr, 1, 134, 52, fx.clamp(lt / 3.692), accent, bg=VOID2)
    # program line
    fr.fill_rect(2, 0, 2, fr.cols - 1, " ", bg=VOID)
    prefix = "> form.simulate("
    fr.write(2, 2, prefix, fg=P.C["dim"])
    fr.write(2, 2 + len(prefix), seg["key"], fg=accent)
    fr.write(2, 2 + len(prefix) + len(seg["key"]), ")", fg=P.C["dim"])
    fr.write(2, 46, ":: " + seg["form"], fg=P.mix(accent, P.C["fg"], 0.4))
    W.typing(fr, 2, 100, seg["sub"], lt, start=0.30, cps=52,
             fg=P.mix(accent, P.C["fg"], 0.55))
    # bracket row
    for c in range(0, fr.cols, 8):
        if fr.get(3, c) == " ":
            fr.put(3, c, "·", fg=P.mix(LINE, VOID, 0.5))
    fr.write(3, 46, "v FEED", fg=P.mix(accent, VOID, 0.35))
    fr.write(3, 112, "v RELAY", fg=P.mix(accent, VOID, 0.35))
    fr.put(3, 0, "┌", fg=P.mix(LINE, VOID, 0.3))
    fr.put(3, fr.cols - 1, "┐", fg=P.mix(LINE, VOID, 0.3))


def _bubble(fr, ctx, lt, r0, c0, w, lines, accent):
    """ASCII speech bubble with a typing reveal and blinking cursor."""
    h = len(lines)
    fr.fill_rect(r0, c0, r0 + h + 1, c0 + w, " ", bg=PANEL)
    fr.box(r0, c0, r0 + h + 1, c0 + w, 1, fg=P.mix(accent, VOID, 0.35), bg=PANEL)
    fr.write(r0, c0 + 2, "┤ SPEECH.OUT ├", fg=accent, bg=PANEL)
    for i, ln in enumerate(lines):
        W.typing(fr, r0 + 1 + i, c0 + 2, ln, lt, start=0.24 + i * 0.18, cps=54,
                 fg=P.mix(accent, WHITE, 0.35), cursor=(i == len(lines) - 1))
    tc = c0 + 4
    fr.put(r0 + h + 2, tc, "╲", fg=P.mix(accent, VOID, 0.4))
    fr.put(r0 + h + 2, tc + 1, "╲", fg=P.mix(accent, VOID, 0.5))
    fr.put(r0 + h + 3, tc + 1, "╲", fg=P.mix(accent, VOID, 0.6))


def _ground(fr, cx, ground_r, color, t):
    fr.hline(ground_r, 0, fr.cols - 1, "─", fg=P.mix(LINE, VOID, 0.3))
    for c in range(0, fr.cols, 6):
        fr.put(ground_r, c, "┴", fg=P.mix(color, VOID, 0.55))
    for k in range(34):
        p = k / 33
        x = int(cx - 20 + p * 40)
        if fr.inb(ground_r + 1, x):
            fr.put(ground_r + 1, x, "▁" if abs(p - 0.5) < 0.4 else "·",
                   fg=P.mix(color, VOID, 0.7))
    for k in range(24):
        a = k / 24 * 2 * math.pi
        x = int(cx + math.cos(a) * 12)
        y = int(ground_r + 2 + math.sin(a) * 1.2)
        if fr.inb(y, x):
            fr.put(y, x, "▁", fg=P.mix(VOID, color, 0.16))


def _bottom(fr, ctx, si, lt, seg):
    t = ctx.t
    accent = P.C[seg["accent"]]
    # big keyword pops on the downbeat
    pop = fx.ease_out_back(fx.clamp(lt / 0.34))
    h = int(round(5 + 2 * fx.clamp(pop)))
    if seg.get("word") == "PROOF":
        h = 5
    r0 = 41 - h
    fr.paint_text(seg["word"], r0, 96, h, fg=accent, fg2=WHITE,
                  align="center", max_cols=150, alpha=fx.clamp(pop * 1.4))
    # rule with tags
    fr.hline(43, 1, fr.cols - 2, "═", fg=P.mix(accent, VOID, 0.28))
    fr.put(43, 0, "╠", fg=P.mix(accent, VOID, 0.5))
    fr.put(43, fr.cols - 1, "╣", fg=P.mix(accent, VOID, 0.5))
    cap = f">> {seg['word']}  ::  {seg['sub']}"
    fr.write(42, max(2, 96 - len(cap) // 2), cap, fg=P.mix(accent, P.C["fg"], 0.5))
    # status line
    fr.fill_rect(44, 0, 44, fr.cols - 1, " ", bg=P.C["void2"])
    W.marquee(fr, 44, "   " + seg["sub"] + "   ", t, speed=24.0,
              fg=P.mix(accent, VOID, 0.4), bg=P.C["void2"], gap=8)
    fr.fill_rect(44, 0, 44, 29, " ", bg=P.C["void2"])
    fr.write(44, 1, f"ID {seg['id']}", fg=accent, bg=P.C["void2"])
    fr.write(44, 12, f"FORM {seg['index']}/04", fg=P.C["dim"], bg=P.C["void2"])
    fr.write(44, 25, f"t+{lt:05.2f}", fg=P.C["dim"], bg=P.C["void2"])
    fr.fill_rect(44, 150, 44, fr.cols - 1, " ", bg=P.C["void2"])
    fr.write(44, 152, f"FRAME {ctx.fi:05d}", fg=P.C["dim"], bg=P.C["void2"])
    W.dots_progress(fr, 44, 168, 6, int(t * 3) % 6, fg=accent)
    fr.write(44, 182, "LOOP ∞", fg=P.C["dim"], bg=P.C["void2"])


# ------------------------------------------------------------ seg 1 eggplant --
def _seg_eggplant(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["violet"]
    hot = P.C["magenta"]
    pulse = ctx.pulse
    masks = _masks("eggplant")
    cx = 96

    # aura + sparkles
    _aura(fr, cx, 20, 32, 12, t, accent, n=52, bright=0.28)
    _aura(fr, cx, 20, 24, 8, -t * 1.4, hot, n=36, ch="+", bright=0.20)
    _sparkles(fr, t, 24, 1, cx, 18, 28, 13, hot)

    # left panel: nutrient feed
    _box(fr, 4, 2, 27, 44, "NUTRIENT FEED", accent)
    nut = fx.clamp(0.35 + 0.6 * (lt / 3.2))
    _stat_rows(fr, 6, 5, 43, (
        ("VIT.C ", nut, f"{int(nut * 100):3d}%", "gold"),
        ("FIBER ", fx.clamp(nut * 0.82), f"{int(nut * 82):3d}%", "green"),
        ("POTAS ", fx.clamp(nut * 0.91), f"{int(nut * 91):3d}%", "teal"),
        ("IRON  ", fx.clamp(nut * 0.66), f"{int(nut * 66):3d}%", "orange"),
        ("WATER ", fx.clamp(nut * 0.97), f"{int(nut * 97):3d}%", "primary"),
        ("FOLATE", fx.clamp(nut * 0.71), f"{int(nut * 71):3d}%", "violet"),
    ))
    fr.write(18, 5, "FEED RATE", fg=P.C["dim"], bg=PANEL2)
    _bar(fr, 18, 17, 18, 0.5 + 0.5 * math.sin(t * 3), P.C["gold"], bg=PANEL2)
    fr.write(20, 5, "MOUTH", fg=P.C["dim"], bg=PANEL2)
    fr.write(20, 17, "OPEN" if int(t * 2) % 2 else "CHEW", fg=P.C["green"], bg=PANEL2)
    fr.write(21, 5, "FLOW", fg=P.mix(accent, VOID, 0.25), bg=PANEL2)
    vals = [(math.sin(k * 0.55 + t * 5) * 0.5 + 0.5) * nut for k in range(34)]
    W.sparkline(fr, 22, 5, vals, 3, fg=P.mix(accent, WHITE, 0.25), bg=PANEL2)
    W.hex_dump(fr, 25, 5, 1, 36, t, seed=3, fg=P.mix(accent, VOID, 0.45))

    # right panel: delivery
    _box(fr, 4, 148, 27, 190, "DELIVERY", accent)
    _stat_rows(fr, 6, 151, 189, (
        ("HUNGER", fx.clamp(0.5 + 0.5 * pulse), "MAX", "gold"),
        ("ACCEPT", 1.0, "100%", "green"),
        ("VALUE ", fx.clamp(lt / 3.2), f"+{int(lt * 37):3d}", "teal"),
        ("LOVE  ", fx.clamp(0.4 + 0.6 * nut), "HIGH", "magenta"),
    ))
    fr.write(15, 151, "STATUS", fg=P.C["dim"], bg=PANEL2)
    fr.write(15, 160, "GIVING", fg=P.C["green"], bg=PANEL2)
    for i, ln in enumerate(SEGS[0]["log"]):
        fr.write(17 + i, 151, ln[:36], fg=P.C["dim"] if i < 3 else P.C["green"], bg=PANEL2)
    fr.write(22, 151, "PACKETS IN", fg=P.C["dim"], bg=PANEL2)
    fr.write(22, 166, f"{240 + int(lt * 37):5d}", fg=P.C["gold"], bg=PANEL2)
    fr.write(24, 151, "LINK", fg=P.C["dim"], bg=PANEL2)
    _bar(fr, 24, 160, 26, 0.92, P.C["magenta"], bg=PANEL2)

    _bubble(fr, ctx, lt, 4, 110, 36, [seg["bubble"], "> nutrients: ALL"], accent)

    # ---- character
    bob = math.sin(t * 2.1) * 1.4 + pulse * 0.7
    sc = 0.55 + 0.45 * fx.ease_out_back(fx.clamp(lt / 0.30))
    h = int(round(31 * sc + pulse * 0.8))
    w = int(round(h * 640 / 780))
    c0 = cx - w // 2
    r0 = 4 + int(round(bob)) + (31 - h)
    _paint(fr, masks, "body", c0, r0, w, h, P.dark("violet", 0.5),
           P.mix(accent, WHITE, 0.42), gain=1.3)
    _paint(fr, masks, "leaf", c0, r0, w, h, P.dark("green", 0.35),
           P.C["grass"], gain=2.1)
    _paint(fr, masks, "stem", c0, r0, w, h, P.C["green"], gain=2.2)
    _paint(fr, masks, "shine", c0, r0, w, h, P.mix(accent, WHITE, 0.55),
           ramp=P.RAMP_HI, gain=1.6, alpha=0.75 + 0.2 * pulse)
    # scanline shading so the body is not one flat glyph
    _shade_rows(fr, r0, c0, w, h, 3, 0.68)

    # face (cell level, layered over the mask)
    frow = r0 + int(h * 0.47)
    blink = ((lt + 0.35) % 2.3) < 0.13
    _eye_pair(fr, cx, frow, 6, blink=blink, ew=4, eh=2, bgc=WHITE,
              look=int(round(math.sin(t * 1.3) * 1.2)))
    _blush(fr, cx, frow + 3, 8, hot)
    _mouth(fr, cx, frow + 4, P.C["gold"], wide=2,
           open_=pulse > 0.55 and not blink)
    # waving little arms, rooted on the bulb edge
    arm_r = int(r0 + h * 0.66)
    ed = _edge(masks, "body", w, h, (arm_r - r0) / max(1, h))
    if ed is not None:
        for side, ex in ((-1, ed[0]), (1, ed[1])):
            base = ex + side
            for k in range(5):
                x = base + side * k
                y = arm_r - k
                if fr.inb(y, x):
                    fr.put(y, x, "╲" if side < 0 else "╱",
                           fg=P.mix(accent, WHITE, 0.55 - 0.06 * k))
            if fr.inb(arm_r - 5, base + side * 5):
                fr.put(arm_r - 5, base + side * 5, "○",
                       fg=P.mix(accent, WHITE, 0.6))
    # id tag
    fr.write(r0 - 1, cx - 6, "EGGPLANT-01", fg=P.mix(accent, VOID, 0.3))

    # mRNA strand on the open left flank
    _rna_panel(fr, ctx, 4, 47, 70, accent)
    _rna(fr, ctx, 58, 10, 20, side=1)

    _feed(fr, t, (cx, frow + 4), P.C["gold"], n=26, seed=4)
    _ground(fr, cx, 34, accent, t)


# -------------------------------------------------------------- seg 2 tomato --
def _seg_tomato(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["red"]
    hot = P.C["orange"]
    pulse = ctx.pulse
    masks = _masks("tomato")
    cx = 96

    for k in range(4):
        p = (t * 0.9 + k * 0.25) % 1.0
        rad = 13 + p * 26
        _aura(fr, cx, 20, rad, rad * 0.42, -t * 0.8, accent, n=42, ch="·",
              bright=1.0 - p * 0.8)
    _sparkles(fr, t, 20, 2, cx, 19, 26, 12, hot)

    # left panel
    _box(fr, 4, 2, 27, 44, "ANTIOXIDANT LAB", accent)
    lc = fx.clamp(0.4 + 0.6 * (lt / 3.2)) * (0.85 + 0.15 * pulse)
    _stat_rows(fr, 6, 5, 43, (
        ("LYC   ", lc, f"{lc * 4.2:4.2f}", "red"),
        ("VIT.C ", fx.clamp(lc * 0.9), f"{int(lc * 90):3d}%", "orange"),
        ("VIT.E ", fx.clamp(lc * 0.74), f"{int(lc * 74):3d}%", "gold"),
        ("FLAVO ", fx.clamp(lc * 0.63), f"{int(lc * 63):3d}%", "magenta"),
        ("BETAC ", fx.clamp(lc * 0.55), f"{int(lc * 55):3d}%", "violet"),
        ("PH    ", 0.5 + 0.3 * math.sin(t * 1.5), "4.5", "green"),
    ))
    fr.write(18, 5, "FREE RADICALS", fg=P.C["dim"], bg=PANEL2)
    fr.write(18, 23, f"{max(0, 120 - int(lt * 34)):3d}", fg=P.C["green"], bg=PANEL2)
    for k in range(36):
        v = abs(math.sin(k * 0.7 + t * 4)) * (0.4 + 0.6 * lc)
        rr = 21 + int(v * 4)
        fr.put(rr, 5 + k, "█" if v > 0.75 else ("▓" if v > 0.5 else "▒"),
               fg=P.mix(accent, VOID, 0.35))
    fr.write(26, 5, "SCAVENGED", fg=P.mix(accent, VOID, 0.3), bg=PANEL2)

    # right panel
    _box(fr, 4, 148, 27, 190, "CELL PROTECTION", accent)
    _stat_rows(fr, 6, 151, 189, (
        ("SKIN ", fx.clamp(0.6 + 0.4 * pulse), "OK", "green"),
        ("AGING", fx.clamp(1.0 - lt / 3.2), "REV", "primary"),
        ("OXID ", fx.clamp(0.2 + 0.2 * math.sin(t * 2)), "LOW", "teal"),
        ("VITAL", fx.clamp(0.5 + 0.5 * lc), "HIGH", "gold"),
    ))
    fr.write(15, 151, "RADICALS", fg=P.C["dim"], bg=PANEL2)
    fr.write(15, 162, "PURGED", fg=P.C["green"], bg=PANEL2)
    for i, ln in enumerate(SEGS[1]["log"]):
        fr.write(17 + i, 151, ln[:36], fg=P.C["dim"] if i < 3 else P.C["green"], bg=PANEL2)
    fr.write(22, 151, "DOSE", fg=P.C["dim"], bg=PANEL2)
    fr.write(22, 159, f"{int(lt * 46):3d} mg", fg=P.C["red"], bg=PANEL2)
    _bar(fr, 24, 151, 30, fx.clamp(lt / 3.2), P.C["orange"], bg=PANEL2)

    _bubble(fr, ctx, lt, 4, 110, 36, [seg["bubble"], "> lycopene: +4.2mg"], accent)

    # ---- character
    bob = math.sin(t * 2.1 + 0.6) * 1.6 + pulse * 1.0
    squash = 1.0 + 0.04 * pulse
    sc = 0.55 + 0.45 * fx.ease_out_back(fx.clamp(lt / 0.30))
    h = int(round(28 * sc * squash + pulse * 0.8))
    w = int(round(h * 1.02)) + 2
    c0 = cx - w // 2
    r0 = 6 + int(round(bob)) + (28 - h)
    for k in range(3):
        rad = 12 + k * 3
        _aura(fr, cx, r0 + h // 2, rad, rad * 0.5, t * (0.7 + 0.2 * k), accent,
              n=36, bright=0.5 - 0.1 * k)
    _paint(fr, masks, "body", c0, r0, w, h, P.dark("red", 0.5),
           P.mix(accent, WHITE, 0.32), gain=2.0)
    _paint(fr, masks, "leaf", c0, r0, w, h, P.dark("green", 0.35),
           P.C["grass"], gain=2.1)
    _paint(fr, masks, "stem", c0, r0, w, h, P.C["green"], gain=2.2)
    _paint(fr, masks, "shine", c0, r0, w, h, P.mix(accent, WHITE, 0.55),
           ramp=P.RAMP_HI, gain=1.5, alpha=0.55 + 0.2 * pulse)
    _shade_rows(fr, r0, c0, w, h, 3, 0.7)

    frow = r0 + int(h * 0.42)
    blink = ((lt + 1.4) % 2.1) < 0.12
    _eye_pair(fr, cx, frow, 6, blink=blink, ew=4, eh=3, bgc=WHITE,
              look=int(round(math.sin(t * 1.1 + 1) * 1.2)))
    _blush(fr, cx, frow + 4, 10, hot)
    _mouth(fr, cx, frow + 5, P.C["gold"], wide=2,
           open_=pulse > 0.6 and not blink)

    # vitamin chips floating around
    chips = (("VIT.C", -1), ("VIT.E", 1), ("LYC", -1), ("K+", 1))
    for i, (lab, side) in enumerate(chips):
        p = (t * 0.55 + i * 0.27) % 1.0
        x = int(cx + side * (w // 2 + 4 + 7 * fx.hash01(i, 5)))
        y = int(r0 + 4 + i * 4 + math.sin(t * 2 + i) * 2 - p * 2)
        if not fr.inb(y, x):
            continue
        fr.fill_rect(y, x - 1, y, x + len(lab), " ", bg=PANEL)
        fr.box(y - 1, x - 1, y + 1, x + len(lab), 1, fg=P.mix(accent, VOID, 0.5),
               bg=PANEL)
        fr.write(y, x, lab, fg=P.mix(accent, WHITE, 0.35), bg=PANEL)

    # antioxidant particles rising
    for k in range(24):
        p = (t * (0.5 + fx.hash01(k, 7) * 0.9) + fx.hash01(k, 8)) % 1.0
        x = int(78 + fx.hash01(k, 9) * 38)
        y = int(34 - p * 26)
        if fr.inb(y, x):
            fr.put(y, x, "○" if p > 0.5 else "·",
                   fg=P.mix(accent, VOID, 0.25 + 0.55 * p))
    fr.write(r0 - 2, cx - 7, "TOMATO-02", fg=P.mix(accent, VOID, 0.3))
    # mRNA strand on the open right flank (mirror side)
    _rna(fr, ctx, 132, 11, 17, side=-1)
    _rna_panel(fr, ctx, 28, 116, 144, accent, side=-1)
    _ground(fr, cx, 34, accent, t)


# --------------------------------------------------------------- seg 3 tabby --
def _seg_tabby(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["gold"]
    hot = P.C["amber"]
    pulse = ctx.pulse
    masks = _masks("tabby")
    cx = 96
    purr = 0.55 + 0.45 * abs(math.sin(t * 6.2))

    # purr rings radiating from the chest
    for k in range(5):
        p = ((t * 1.15 + k * 0.2) % 1.0)
        rad = 13 + p * 30
        _aura(fr, cx, 22, rad, rad * 0.45, 0.0, accent, n=54,
              ch="○" if k % 2 else "·", bright=1.0 - p * 0.85, spin=0.0)
    _sparkles(fr, t, 16, 3, cx, 19, 26, 12, hot)

    # left panel: purr engine
    _box(fr, 4, 2, 27, 44, "PURR ENGINE", accent)
    _stat_rows(fr, 6, 5, 43, (
        ("PURR  ", purr, f"{int(purr * 99):3d}%", "gold"),
        ("FREQ  ", fx.clamp(0.5 + 0.5 * purr), "25Hz", "amber"),
        ("ENJOY ", fx.clamp(0.3 + 0.7 * (lt / 3.2)), f"{int(lt * 31):3d}%", "green"),
        ("VIBRA ", fx.clamp(0.4 + 0.6 * purr), "ON", "primary"),
        ("BPM   ", fx.clamp(0.5 + 0.5 * pulse), "132", "teal"),
    ))
    pv = [0.1 + 0.9 * (math.sin(k * 0.9 + t * 18) * 0.5 + 0.5) * purr for k in range(38)]
    fr.write(17, 5, "PURR WAVE  25.0 HZ", fg=P.C["dim"], bg=PANEL2)
    W.sparkline(fr, 18, 5, pv, 7, fg=P.C["gold"], bg=PANEL2)
    fr.write(25, 5, "RESONANCE", fg=P.C["dim"], bg=PANEL2)
    _bar(fr, 25, 16, 22, purr, P.C["amber"], bg=PANEL2)

    # right panel: enjoyment
    _box(fr, 4, 148, 27, 190, "ENJOYMENT", accent)
    _stat_rows(fr, 6, 151, 189, (
        ("MOOD  ", 0.9, "HAPPY", "gold"),
        ("SOFT  ", 1.0, "YES", "green"),
        ("CLAIM ", fx.clamp(lt / 3.2), f"{int(lt * 30):3d}%", "amber"),
        ("PETS  ", fx.clamp(0.2 + lt / 4), f"{int(lt * 12):3d}", "primary"),
    ))
    fr.write(15, 151, "STATE", fg=P.C["dim"], bg=PANEL2)
    fr.write(15, 160, "PURRING", fg=P.C["green"], bg=PANEL2)
    for i, ln in enumerate(SEGS[2]["log"]):
        fr.write(17 + i, 151, ln[:36], fg=P.C["dim"] if i < 3 else P.C["green"], bg=PANEL2)
    fr.write(22, 151, "ENJOY BAR", fg=P.C["dim"], bg=PANEL2)
    _bar(fr, 22, 162, 24, fx.clamp(0.25 + lt / 4), P.C["gold"], bg=PANEL2)
    fr.write(24, 151, "SCRATCH", fg=P.C["dim"], bg=PANEL2)
    fr.write(24, 160, "LOW / SAFE", fg=P.C["green"], bg=PANEL2)

    _bubble(fr, ctx, lt, 4, 110, 36, [seg["bubble"], "> purr: 25Hz 100%"], accent)

    # ---- character
    bob = math.sin(t * 2.4 + 0.2) * 1.4 + pulse * 1.1
    sc = 0.55 + 0.45 * fx.ease_out_back(fx.clamp(lt / 0.30))
    h = int(round(31 * sc + pulse * 0.8))
    w = int(round(h * 760 / 820 * 1.12))
    c0 = cx - w // 2
    r0 = 4 + int(round(bob)) + (31 - h)
    tw = 1 if math.sin(t * 4.1) > 0.82 else 0
    _paint(fr, masks, "body", c0, r0, w, h, P.dark("gold", 0.5),
           P.mix(accent, WHITE, 0.35), gain=1.5)
    _paint(fr, masks, "stripes", c0, r0, w, h, P.dark("amber", 0.4), P.C["amber"],
           gain=2.0, alpha=0.95)
    _paint(fr, masks, "inner_ear", c0 + tw, r0, w, h, P.dark("orange", 0.2),
           P.C["orange"], gain=2.0)
    _paint(fr, masks, "muzzle", c0, r0, w, h, P.mix(P.C["gold"], WHITE, 0.45),
           gain=1.6, alpha=0.7)
    _shade_rows(fr, r0, c0, w, h, 4, 0.74)
    # pointed ears, anchored to the actual head top
    m = _spr(masks, "body", w, h)
    solid = np.nonzero((m > 0.25).any(axis=1))[0]
    head_top = r0 + (int(solid[0] // L.CELL_H) if solid.size else 1)
    _cat_ears(fr, cx, head_top + 1, P.mix(accent, WHITE, 0.4),
              P.mix(hot, VOID, 0.12))

    frow = r0 + int(h * 0.36)
    blink = ((lt + 0.9) % 3.1) < 0.13
    _eye_pair(fr, cx, frow, 5, blink=blink, ew=5, eh=2,
              bgc=P.mix(P.C["grass"], WHITE, 0.15), pc=VOID, slit=True,
              look=int(round(math.sin(t * 1.6) * 1.2)))
    # eyelashes
    for side in (-1, 1):
        if fr.inb(frow - 1, cx + side * 8):
            fr.put(frow - 1, cx + side * 8, "╱" if side < 0 else "╲",
                   fg=P.mix(accent, WHITE, 0.5))
    # nose + mouth
    fr.put(frow + 4, cx, "▼", fg=P.C["magenta"])
    fr.write(frow + 5, cx - 2, "╲▁╱", fg=P.mix(accent, WHITE, 0.55))
    _blush(fr, cx, frow + 4, 8, hot)
    # crisp whiskers instead of the noisy mask
    wcol = P.mix(accent, WHITE, 0.45)
    for j, (dy, xl, xr) in enumerate(((3, 6, 5), (4, 7, 6), (5, 8, 7))):
        y = frow + dy
        if fr.inb(y, cx - xl):
            fr.write(y, cx - xl, "──", fg=wcol)
        if fr.inb(y, cx + xr):
            fr.write(y, cx + xr, "──", fg=wcol)

    # tail: thick base off the hip, hooking up and back
    bx = c0 + w - 3
    by = r0 + int(h * 0.78)
    path = ((0, 0), (0, -1), (1, -2), (1, -3), (2, -3), (2, -4), (2, -5),
            (1, -5), (1, -6), (0, -6), (0, -7), (-1, -8))
    for i, (ddx, ddy) in enumerate(path):
        x = bx + ddx + int(round(math.sin(t * 2.2) * 0.6))
        y = by + ddy
        ch = "▓" if i < 4 else ("▒" if i < 8 else "░")
        col = P.mix(accent, WHITE, 0.35 - 0.02 * i)
        if fr.inb(y, x):
            fr.put(y, x, ch, fg=col)
        if i < 6 and fr.inb(y, x - 1):
            fr.put(y, x - 1, "▒", fg=P.mix(accent, VOID, 0.25))

    # floating music notes + purr ticks
    for k in range(10):
        p = (t * 0.6 + fx.hash01(k, 11)) % 1.0
        x = int(cx + (fx.hash01(k, 12) - 0.5) * 58 + math.sin(t * 2 + k) * 3)
        y = int(31 - p * 26)
        if fr.inb(y, x):
            fr.put(y, x, "♪" if k % 2 else "♫",
                   fg=P.mix(accent, VOID, 0.12 + 0.65 * p))
    for k in range(28):
        a = k / 28 * 2 * math.pi
        rr = 1.0 + 0.05 * math.sin(t * 22 + k)
        x = int(cx + math.cos(a) * (w * 0.62) * rr)
        y = int(r0 + h * 0.58 + math.sin(a) * (h * 0.4) * rr)
        if fr.inb(y, x):
            fr.put(y, x, "·", fg=P.mix(accent, VOID, 0.55))
    fr.write(32, cx + 13, "TABBY-03", fg=P.mix(accent, VOID, 0.3))
    _ground(fr, cx, 34, accent, t)


# ------------------------------------------------------------------ seg 4 god --
def _seg_god(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["gold"]
    hot = P.C["magenta"]
    pulse = ctx.pulse
    cx = 96
    heart_m = art.get("heart", w=200, h=190)
    inf_m = art.get("infinity", w=320, h=130)

    # rays from the being
    for k in range(38):
        a = k / 38 * 2 * math.pi + t * 0.16
        for rr in range(15, 38, 3):
            x = int(cx + math.cos(a) * rr * 1.6)
            y = int(14 + math.sin(a) * rr * 0.55)
            if fr.inb(y, x):
                fr.put(y, x, "·", fg=P.mix(accent, VOID, 0.26 + 0.22 * math.sin(t * 3 + k)))
    # hologram infinity behind the head
    fr.paint_mask(_spr_arr(inf_m, 44, 10), cx - 22, 3, 44, 10, ramp=P.RAMP_HI,
                  fg=P.mix(accent, VOID, 0.5), gain=1.5, alpha=0.5)
    _sparkles(fr, t, 26, 5, cx, 14, 32, 13, WHITE)

    # left panel
    _box(fr, 4, 2, 27, 44, "EXISTENCE ENGINE", accent)
    _stat_rows(fr, 6, 5, 43, (
        ("PROOF ", fx.clamp(0.5 + 0.5 * (lt / 3.2)), "100%", "gold"),
        ("WITNES", 1.0, "YOU", "white"),
        ("FAITH ", fx.clamp(0.6 + 0.4 * pulse), "MAX", "gold"),
        ("POWER ", fx.clamp(0.3 + 0.7 * (lt / 3.2)), "INF", "violet"),
        ("HALO  ", 1.0, "100%", "gold"),
    ))
    wv = [abs(math.sin(k * 0.6 + t * 5)) for k in range(34)]
    fr.write(17, 5, "DIVINITY CHECK", fg=P.C["dim"], bg=PANEL2)
    W.sparkline(fr, 18, 5, wv, 4, fg=P.C["gold"], bg=PANEL2)
    fr.write(24, 5, "SIGNAL  99.99%  FAITH LOCK", fg=P.mix(accent, VOID, 0.2), bg=PANEL2)
    W.hex_dump(fr, 25, 5, 1, 36, t, seed=9, fg=P.mix(accent, VOID, 0.45))

    # worshipper reticle (the USER)
    rx, ry = 150, 25
    for i, rad in enumerate((3, 6, 9)):
        n = 22 + i * 10
        for k in range(n):
            a = k / n * 2 * math.pi + t * (0.5 - i * 0.14) * (1 if i % 2 else -1)
            x = int(rx + math.cos(a) * rad * 1.9)
            y = int(ry + math.sin(a) * rad * 0.62)
            if fr.inb(y, x):
                fr.put(y, x, "·" if i else "○", fg=P.mix(P.C["primary"], VOID, 0.3 + 0.15 * i))
    fr.hline(ry, rx - 22, rx - 12, "─", fg=P.mix(P.C["primary"], VOID, 0.2))
    fr.hline(ry, rx + 12, rx + 22, "─", fg=P.mix(P.C["primary"], VOID, 0.2))
    fr.write(ry - 9, rx - 9, "⌖ TARGET // USER", fg=P.mix(P.C["primary"], VOID, 0.12))
    fr.write(ry - 8, rx - 9, "witness.lock = 1", fg=P.mix(P.C["primary"], VOID, 0.3))
    fr.write(ry - 4, rx - 1, "◉", fg=P.C["white"])
    fr.write(ry - 3, rx - 2, "─┼─", fg=P.C["white"])
    fr.put(ry - 2, rx, "│", fg=P.C["white"])
    fr.write(ry - 1, rx - 1, "╱╲", fg=P.C["white"])

    # proof readout box
    _box(fr, 30, 118, 41, 176, "PROOF OF EXISTENCE", accent)
    fr.write(32, 121, "witness     : YOU", fg=P.C["primary"], bg=PANEL2)
    fr.write(33, 121, "soul.sig    : 100.00%", fg=P.C["primary"], bg=PANEL2)
    fr.write(34, 121, "proof.value : 1.0000", fg=P.C["gold"], bg=PANEL2)
    fr.write(35, 121, "status      : CONFIRMED", fg=P.C["green"], bg=PANEL2)
    fr.write(36, 121, "distance    : 0.944 LY", fg=P.C["dim"], bg=PANEL2)
    fr.write(37, 121, "faith       : " + ("MAX" if pulse > 0.4 else "MAX"),
             fg=P.C["gold"], bg=PANEL2)
    W.progress_bar(fr, 39, 121, 50, fx.clamp(lt / 2.6), fg=P.C["gold"], bg=PANEL2,
                   show_pct=False)
    # beam from the being to the target
    for k in range(44):
        p = k / 43
        x = int(fx.lerp(cx + 10, rx - 14, p))
        y = int(fx.lerp(15, ry - 12, p) + math.sin(t * 4 + p * 6) * 2)
        if fr.inb(y, x):
            fr.put(y, x, "·" if k % 3 else "─", fg=P.mix(accent, VOID, 0.35 + 0.4 * p))

    _bubble(fr, ctx, lt, 3, 124, 28, [seg["bubble"], "> faith: MAX"], accent)

    # ---- the being: baked approved design (engine/god_small.py, 60 cells x 44 rows)
    from engine import god_small as WG
    hal = P.C["gold"]
    pcx = 88
    bob = math.sin(t * 1.6) * 0.8 + pulse * 0.6
    gw, rows = WG.W, WG.H // 2
    r0 = 1 + int(round(bob * 0.45))
    c0 = pcx - gw // 2
    data, gpal = WG.get()
    navy = P.C["void"]
    pal = [P.mix(rgb, navy, 0.12) for rgb in gpal[1:]]
    # sunburst rays behind the figure (radiant-halo reference look)
    hbx, hby = pcx, r0 + 9
    for k in range(34):
        a = k / 34.0 * 2 * math.pi + 0.02 * t
        ca, sa = math.cos(a), math.sin(a)
        ln = 27 if k % 2 == 0 else 17
        for q in range(5, ln):
            x = int(hbx + ca * q * 1.60)
            y = int(hby + sa * q * 0.82)
            if (not fr.inb(y, x)) or x < 46 or x > 134 or y < 1 or y > 33:
                continue
            if (c0 - 1) <= x <= (c0 + gw) and (r0 - 1) <= y <= (r0 + rows + 1):
                continue
            col = P.mix(hal, WHITE, 0.10 + 0.50 * (1.0 - q / float(ln)))
            if abs(ca) > abs(sa) * 1.5:
                ch = "─"
            elif abs(sa) > abs(ca) * 1.5:
                ch = "│"
            else:
                ch = "╱" if ca * sa > 0 else "╲"
            fr.put(y, x, ch, fg=col)
    for rr in range(rows):
        base = r0 + rr
        if base < 0 or base >= fr.rows:
            continue
        gain = 0.90 + 0.10 * math.sin((base + t * 26.0) * 1.6)
        for cc in range(gw):
            top = int(data[2 * rr, cc])
            bot = int(data[2 * rr + 1, cc])
            if top == 0 and bot == 0:
                continue
            ct = pal[top - 1] if top else navy
            cb = pal[bot - 1] if bot else navy
            ct = tuple(int(v * gain) for v in ct)
            cb = tuple(int(v * gain) for v in cb)
            if top and top == bot:
                fr.put(base, c0 + cc, "█", fg=ct)
            else:
                fr.put(base, c0 + cc, "▀", fg=ct, bg=cb)

    # halo readout
    fr.write(30, 3, "HALO / DIVINITY 100%",
             fg=P.mix(hal, WHITE, 0.35), bg=VOID)
    fr.write(31, 3, "BLESSING ACTIVE  ·  RADIANCE OK",
             fg=P.mix(hal, WHITE, 0.12), bg=VOID)

    # ascending sacred sparkles
    for k in range(6):
        p = (t * 0.42 + fx.hash01(k, 21)) % 1.0
        x = int(cx + (fx.hash01(k, 22) - 0.5) * 62 + math.sin(t * 2 + k) * 3)
        y = int(33 - p * 27)
        if fr.inb(y, x):
            fr.put(y, x, "✦" if k % 3 == 0 else ("♥" if k % 3 == 1 else "·"),
                   fg=P.mix(hal, VOID, 0.2 + 0.6 * p))

    fr.write(36, pcx - 6, "DEUS SOLUS", fg=P.mix(accent, WHITE, 0.15), bg=VOID)
    _ground(fr, cx, 34, accent, t)


# --------------------------------------------------------------------- draw --
def _background(fr, ctx, seg, si):
    t = ctx.t
    accent = P.C[seg["accent"]]
    dot = P.mix(VOID, LINE, 0.42)
    dot2 = P.mix(accent, VOID, 0.26)
    sweep = P.mix(accent, VOID, 0.5)
    cc = P.mix(accent, VOID, 0.45)
    dcol = P.mix(accent, VOID, 0.68)
    for r in range(2, fr.rows, 3):
        for c in range(0, fr.cols, 4):
            if fr.get(r, c) == " ":
                fr.put(r, c, "·", fg=dot)
    for k, c in enumerate((47, 58, 69, 80, 112, 123, 134, 145)):
        W.data_column(fr, 3, c, 30, t, seed=si * 13 + k, speed=5.0 + 0.4 * k,
                      fg=dcol)
    for k in range(44):
        a = k / 44 * 2 * math.pi
        x = int(96 + math.cos(a) * 44)
        y = int(20 + math.sin(a) * 15)
        if fr.inb(y, x):
            fr.put(y, x, "·", fg=dot2)
    sy = int((t * 14) % (fr.rows + 12)) - 6
    if 0 <= sy < fr.rows:
        for c in range(fr.cols):
            if fr.get(sy, c) in ("·", " ", "─"):
                fr.put(sy, c, "─", fg=sweep)
    for (r, c, ch) in ((2, 0, "╔"), (2, fr.cols - 1, "╗"),
                       (44, 0, "╚"), (44, fr.cols - 1, "╝")):
        fr.put(r, c, ch, fg=cc)


def _boundary(fr, ctx, si, lt):
    """Snappy segment transition: pop + scan bar + glitch on the downbeat."""
    dur = SEG_T1[si] - SEG_T0[si]
    accent = P.C[SEGS[si]["accent"]]
    if lt < 0.24:
        p = lt / 0.24
        y = int(p * (fr.rows + 2)) - 1
        for dr in (0, -1, -2):
            r = y + dr
            if 0 <= r < fr.rows:
                a = 0.85 + dr * 0.25
                for c in range(fr.cols):
                    if a > 0.15:
                        fr.put(r, c, "▔" if dr == 0 else "─",
                               fg=P.mix(accent, WHITE, max(0.0, a)))
        ctx.set_glitch(0.55 * (1.0 - p))
        ctx.meta["flash"] = 0.26 * (1.0 - p)
        ctx.meta["flash_color"] = accent
        ctx.shake(4)
    elif lt > dur - 0.16:
        p = (lt - (dur - 0.16)) / 0.16
        ctx.set_glitch(0.28 + 0.5 * p)
        ctx.meta["flash"] = 0.22 * p
        ctx.meta["flash_color"] = accent


def draw(ctx):
    t = ctx.t
    fr = ctx.frame()
    si = 0
    for k in (3, 2, 1, 0):
        if t >= SEG_T0[k]:
            si = k
            break
    seg = SEGS[si]
    lt = t - SEG_T0[si]
    dur = SEG_T1[si] - SEG_T0[si]
    accent = P.C[seg["accent"]]
    ctx.meta["bloom"] = 0.20 if si == 3 else 0.46
    ctx.meta["tint"] = (accent, 0.06)

    _background(fr, ctx, seg, si)
    _top(fr, ctx, si, lt, seg)
    if si == 0:
        _seg_eggplant(fr, ctx, lt, dur, seg)
    elif si == 1:
        _seg_tomato(fr, ctx, lt, dur, seg)
    elif si == 2:
        _seg_tabby(fr, ctx, lt, dur, seg)
    else:
        _seg_god(fr, ctx, lt, dur, seg)
    _bottom(fr, ctx, si, lt, seg)
    _boundary(fr, ctx, si, lt)
    return fr
