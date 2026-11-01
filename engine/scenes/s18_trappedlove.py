"""s18_trappedlove - "Though you are free, I am trapped, trapped in love".

188.496 -> 192.190

Left half: the other one is FREE - a bird flies out of a broken cage, feathers
trailing, the door hanging open.  Right half: you are TRAPPED - a heart behind
hearts and bars, scanned for exactly the defects s14 repaired (one hole + three
dents), patched to 100% integrity ... and still caged.  Ends on the trapped heart.
"""
from __future__ import annotations

import math

import numpy as np

from .. import art
from .. import fx
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

from .s15_count import mix, rule, panel, big, edges, dense_bg, heart_fill

T0, T1 = 188.496, 192.190
LINE = TL.EVENTS["trapped_in_love"]      # 188.496

FREE = P.C["primary"]
SKY = P.C["teal"]
CAGE = P.C["crimson"]
HEART_FG = P.C["red"]
GOLD = P.C["gold"]

# the exact defects s14 found in this heart: one hole, three dents
HOLES = ((0.50, 0.46, 0.105),)
DENTS = ((0.26, 0.30, 0.075), (0.73, 0.32, 0.070), (0.50, 0.74, 0.065))


def _heart_mask(cw, ch, defects=True):
    if defects:
        return heart_fill(cw * 10, ch * 18, holes=HOLES, dents=DENTS)
    return heart_fill(cw * 10, ch * 18)


def _bird(fr, r, c, t, fg=None):
    """A small bird in flight (4 rows) + motion ticks."""
    fg = fg or P.C["white"]
    fr.write(r, c, " ▄   ▄", fg=fg)
    fr.write(r + 1, c, "  ▀▄▀", fg=fg)
    fr.write(r + 2, c, "  ███", fg=fg)
    fr.write(r + 3, c, "   ▀", fg=fg)
    for i in range(3):
        ph = int(t * 12 + i * 2) % 6
        fr.write(r + 2, c - 6 + i * 2, "·~-"[ph % 3], fg=mix(P.C["void"], SKY, 0.7))


# ---------------------------------------------------------------------------
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    p = fx.clamp((t - T0) / (T1 - T0))
    _background(fr, ctx, p)
    _top(fr, ctx, p)
    _free_side(fr, ctx, p)
    _trapped_side(fr, ctx, p)
    _hud(fr, ctx, p)
    _bottom(fr, ctx, p)
    _status(fr, ctx, p)
    edges(fr, mix(P.C["void"], CAGE, 0.45))
    ctx.meta["bloom"] = 0.30
    ctx.meta["vignette"] = 0.95
    if t - T0 < 0.18:
        amp = 1.0 - (t - T0) / 0.18
        ctx.meta["flash"] = 0.16 * amp
        ctx.meta["flash_color"] = P.C["white"]
        ctx.shake(2)
    repair = _repair_p(t)
    if 0.55 < repair < 0.75:
        ctx.meta["flash"] = 0.10
        ctx.meta["flash_color"] = GOLD
    ctx.set_glitch(0.02 + 0.03 * math.sin(t * 3.0))
    return fr


# ---------------------------------------------------------------------------
def _repair_p(t):
    return fx.clamp((t - (T0 + 1.15)) / 1.45)


def _background(fr, ctx, p):
    t = ctx.t
    dense_bg(fr, ctx, seed=81, fg=SKY, hot=0.3, base=mix(P.C["void"], P.C["blood"], 0.03))
    # horizon split: free sky left, cage darkness right
    fr.fill_rect(9, 2, 26, 92, " ", bg=mix(P.C["void"], SKY, 0.03 + 0.03 * p))
    fr.fill_rect(9, 96, 26, 189, " ", bg=mix(P.C["void"], P.C["blood"], 0.10))
    for c in range(2, 190, 4):
        for r in range(2, 44, 3):
            fr.put(r, c, "·", fg=mix(P.C["void"], P.C["line"], 0.4))
    # stars on the free side
    rng = ctx.rng(13)
    for i in range(28):
        r = int(rng.random() * 14) + 10
        c = int(rng.random() * 86) + 4
        fr.put(r, c, "*" if i % 5 == 0 else "·", fg=mix(P.C["void"], SKY, 0.4 + 0.5 * rng.random()))


def _top(fr, ctx, p):
    t = ctx.t
    panel(fr, 2, 2, 8, 92, "FREEDOM", fg=mix(P.C["void"], SKY, 0.8),
          bg=mix(P.C["void"], SKY, 0.03))
    panel(fr, 2, 96, 8, 189, "TRAPPED", fg=mix(P.C["void"], CAGE, 0.8),
          bg=mix(P.C["void"], CAGE, 0.05))
    fr.write(3, 4, "YOU:   FREE", fg=P.C["white"])
    fr.write(4, 4, "WINGS: OPEN", fg=SKY)
    fr.write(5, 4, "CAGE:  BROKEN", fg=FREE)
    fr.write(6, 4, "ESCAPE: 100%", fg=P.C["green"])
    fr.write(3, 98, "ME:    TRAPPED", fg=P.C["white"])
    fr.write(4, 98, "WALLS: 12/12", fg=CAGE)
    fr.write(5, 98, "DOOR:  BOLTED", fg=HEART_FG)
    fr.write(6, 98, "ESCAPE: 0%", fg=P.C["crimson"])
    fr.write(3, 40, "THOUGH YOU ARE FREE", fg=mix(P.C["void"], SKY, 0.95))
    fr.write(5, 40, ">>> one flies, one is kept <<<", fg=P.C["dim"])
    fr.write(3, 130, "I AM TRAPPED", fg=mix(P.C["void"], CAGE, 1.0))
    fr.write(5, 130, "TRAPPED IN LOVE", fg=P.C["white"])
    fr.write(6, 68, f"T+{ctx.t - T0:5.2f}s", fg=GOLD)


# ---------------------------------------------------------------------------
# left: freedom
# ---------------------------------------------------------------------------
def _free_side(fr, ctx, p):
    t = ctx.t
    # broken cage + open door
    fr.box(15, 8, 24, 34, 1, fg=mix(P.C["void"], SKY, 0.6))
    for c in range(10, 33, 3):
        for r in range(16, 24):
            if c == 22 and r < 19:          # broken bars
                continue
            fr.put(r, c, "║", fg=mix(P.C["void"], SKY, 0.5))
    fr.write(15, 22, "┛  ┗", fg=mix(P.C["void"], SKY, 0.8))
    fr.write(24, 8, "[ CAGE 0xDEAD ]  BROKEN", fg=FREE)
    # the bird: flies out on the left side and up
    bp = fx.ease_inout(fx.clamp(p * 1.25))
    br = int(round(fx.lerp(20, 10, bp)))
    bc = int(round(fx.lerp(14, 56, bp)))
    _bird(fr, br, bc, t, fg=P.C["white"] if p < 0.5 else SKY)
    # feather trail
    for i in range(14):
        q = fx.clamp(bp - i * 0.045)
        if q <= 0:
            continue
        rr = int(round(fx.lerp(20, 10, q)))
        cc = int(round(fx.lerp(14, 56, q)))
        fr.put(rr + 2, cc - 5 - i, "·" if i % 3 else "~",
               fg=mix(P.C["void"], SKY, max(0.15, 0.8 - i * 0.05)))
    fr.write(10, 4, "FREE", fg=P.C["white"])
    # open sky: drifting wind streaks + big FREE word out where the bird goes
    for i in range(16):
        rr = 13 + (i * 7) % 11
        cc = int((i * 29 + t * 14 + 6) % 84) + 4
        fr.write(rr, cc, "~" if i % 3 else "≈",
                 fg=mix(P.C["void"], SKY, 0.25 + 0.3 * (i % 3) / 2))
    big(fr, "FREE", 18, 71, 5, fg=mix(P.C["void"], SKY, 0.85),
        fg2=P.C["white"], align="center")
    fr.write(22, 40, "NO WALLS // NO CAGE // NO ONE HOLDS THIS", fg=mix(P.C["void"], SKY, 0.9))
    fr.write(23, 40, "the whole sky is an open door", fg=mix(P.C["void"], SKY, 0.65))
    fr.write(11, 4, "00:00  no walls", fg=P.C["dim"])
    # altitude meter
    alt = fx.clamp((20 - br) / 10.0)
    fr.write(10, 62, "ALT", fg=P.C["dim"])
    W.progress_bar(fr, 11, 62, 26, alt, fg=SKY, show_pct=False, label="")
    fr.write(12, 62, f"{alt * 100:5.1f}%", fg=SKY)
    for i in range(12):
        c = 6 + i * 7
        fr.write(25, c, "▁▂▃▄▅▆▇█"[min(7, int(abs(math.sin(t * 2 + i)) * 7))],
                 fg=mix(P.C["void"], SKY, 0.5))
    fr.write(25, 4, "WIND", fg=P.C["dim"])


# ---------------------------------------------------------------------------
# right: trapped
# ---------------------------------------------------------------------------
def _trapped_side(fr, ctx, p):
    t = ctx.t
    rp = _repair_p(t)
    # cage of hearts / bars
    for c in range(100, 188, 6):
        for r in range(10, 26):
            if r % 6 == 0:
                continue
            fr.put(r, c, "║", fg=mix(P.C["void"], CAGE, 0.30))
    # walls of HEART words
    for i in range(6):
        fr.write(11, 102 + i * 15, "♥", fg=mix(P.C["void"], CAGE, 0.5))
        fr.write(25, 102 + i * 15, "♥", fg=mix(P.C["void"], CAGE, 0.5))
    for r in (12, 16, 20, 24):
        fr.write(r, 100, "CAGE", fg=mix(P.C["void"], CAGE, 0.45))
        fr.write(r, 184, "MINE", fg=mix(P.C["void"], CAGE, 0.55))
    # the heart
    hw, hh = 20, 11
    hc0, hr0 = 126, 12
    beat = 0.5 + 0.5 * math.sin(t * 4.4)
    # damaged heart during the scan, whole heart after the patches
    mask = _heart_mask(hw, hh, defects=rp < 0.62)
    fr.paint_mask(mask, hc0, hr0, hw, hh, ramp=P.RAMP_BLOCK,
                  fg=mix(P.C["blood"], HEART_FG, 0.45 + 0.35 * beat),
                  fg2=mix(HEART_FG, P.C["white"], 0.55), gain=1.05 + 0.3 * beat)
    # scan line
    if rp < 0.62:
        sy = hr0 + int(round(fx.clamp(rp / 0.62) * (hh - 1)))
        for c in range(hc0 - 2, hc0 + hw + 2):
            fr.put(sy, c, "▔" if c % 2 else "▔", fg=P.C["white"])
        fr.write(sy, hc0 - 6, "SCAN", fg=GOLD)
        # defects light up behind the scan line
        for k, (fx0, fy0, fr0) in enumerate(HOLES + DENTS):
            dc = hc0 + int(fx0 * hw)
            dr = hr0 + int(fy0 * hh)
            if dr <= sy:
                fr.write(dr, dc - 1, "▓", fg=P.C["white"])
                fr.write(dr + 1, dc - 2, f"!{k}", fg=GOLD)
    else:
        # patched cells glow for a moment
        q = fx.clamp((rp - 0.62) / 0.20)
        for k, (fx0, fy0, fr0) in enumerate(HOLES + DENTS):
            dc = hc0 + int(fx0 * hw)
            dr = hr0 + int(fy0 * hh)
            fr.write(dr, dc - 1, "■", fg=mix(GOLD, P.C["white"], 1 - q * 0.5))
    for i in range(7):
        fr.write(24 + (i % 2), 102 + i * 4, "♥",
                 fg=mix(P.C["void"], CAGE, 0.35 + 0.1 * (i % 3)))
    fr.write(hr0 - 1, hc0 + 4, "TARGET HEART // IN LOVE", fg=mix(P.C["void"], CAGE, 0.9))
    fr.write(hr0 + hh, hc0 + 2, f"INTEGRITY {int(min(100.0, 100 * rp / 0.62)):3d}%  "
                                f"BOUND 100%", fg=P.C["white"])
    # bolts / chains around
    for i in range(10):
        fr.write(hr0 + 2 + (i % 4) * 2, hc0 - 4 - (i // 4) * 2, "○", fg=CAGE)
        fr.write(hr0 + 2 + (i % 4) * 2, hc0 + hw + 3 + (i // 4) * 2, "○", fg=CAGE)


# ---------------------------------------------------------------------------
def _hud(fr, ctx, p):
    t = ctx.t
    rp = _repair_p(t)
    r0 = 27
    panel(fr, r0, 2, r0 + 7, 92, "HEART SCAN // DEFECT REPORT",
          fg=mix(P.C["void"], SKY, 0.8), bg=mix(P.C["void"], SKY, 0.03))
    fr.write(r0 + 1, 4, "> scan heart ........................ DONE", fg=P.C["mid"])
    names = [("HOLE ", 0.50, 0.46, 0.105), ("DENT1", 0.26, 0.30, 0.075),
             ("DENT2", 0.73, 0.32, 0.070), ("DENT3", 0.50, 0.74, 0.065)]
    for i, (nm, fx0, fy0, fr0) in enumerate(names):
        r = r0 + 2 + i
        fixed = rp > 0.25 + i * 0.10
        col = P.C["green"] if fixed else P.C["gold"]
        fr.write(r, 4, f"  {nm}", fg=P.C["white"])
        fr.write(r, 11, f"@({fx0:.2f},{fy0:.2f}) r{fr0:.3f}", fg=P.C["dim"])
        fr.write(r, 34, "PATCH" if fixed else "SCAN ", fg=col)
        fr.write(r, 40, "FIXED ✓" if fixed else "......", fg=col)
        W.segmented_bar(fr, r, 50, 18, 1.0 if fixed else 0.1, cells=9,
                        fg=col if fixed else P.C["grid"])
    fr.write(r0 + 6, 4, f"  heart integrity {int(min(100.0, 100 * rp / 0.62)):3d}% "
                        f"// {int(4 * min(1.0, rp / 0.62))}/4 patches // same defects as s14", fg=P.C["fg"])
    fr.write(r0 + 7, 4, "  ... but the cage was never part of the scan", fg=P.C["crimson"])
    # right: trap telemetry
    panel(fr, r0, 96, r0 + 7, 189, "LOVE TRAP", fg=mix(P.C["void"], CAGE, 0.85),
          bg=mix(P.C["void"], CAGE, 0.05))
    fr.write(r0 + 1, 98, "YOU  FREE ....... 100%", fg=SKY)
    fr.write(r0 + 2, 98, "ME   TRAPPED ..... 100%", fg=CAGE)
    fr.write(r0 + 3, 98, "HEART REPAIRED .. 100%", fg=P.C["green"])
    fr.write(r0 + 4, 98, "HEART ESCAPED ..... 0%", fg=P.C["crimson"])
    W.progress_bar(fr, r0 + 5, 98, 44, 1.0, fg=CAGE, show_pct=False)
    fr.write(r0 + 5, 146, "CAGE 12/12", fg=P.C["white"])
    W.progress_bar(fr, r0 + 6, 98, 44, 0.0, fg=P.C["grid"], show_pct=False)
    fr.write(r0 + 6, 146, "DOOR 0/1", fg=CAGE)
    fr.write(r0 + 7, 98, "trapped in love // trapped in love // ah",
             fg=mix(P.C["void"], P.C["fg"], 0.95))


# ---------------------------------------------------------------------------
def _bottom(fr, ctx, p):
    t = ctx.t
    r0 = 36
    # the final trapped heart, chained down
    beat = 0.5 + 0.5 * math.sin(t * 4.4)
    _m = _heart_mask(26, 7, defects=False)
    fr.paint_mask(_m, 8, r0, 26, 7, ramp=P.RAMP_BLOCK,
                  fg=mix(P.C["blood"], HEART_FG, 0.55 + 0.3 * beat),
                  fg2=P.C["white"], gain=1.6 + 0.4 * beat)
    for i in range(9):
        fr.write(r0 + 1 + (i % 3), 6 + i * 4, "○═" if i % 2 else "═○",
                 fg=mix(P.C["void"], CAGE, 0.6))
    fr.write(r0 + 4, 8, "TRAPPED IN LOVE", fg=P.C["white"])
    fr.write(r0 + 5, 8, "the heart is whole, the walls are not", fg=P.C["dim"])
    # small hearts rising from the cage
    for i in range(9):
        rr = int(r0 + 6 - ((t * 6 + i * 3) % 8))
        cc = 44 + i * 4
        fr.write(rr, cc, "♥", fg=mix(P.C["void"], HEART_FG, 0.5 + 0.4 * abs(math.sin(t + i))))
    fr.write(r0 + 6, 44, "FREE 1  /  TRAPPED 1", fg=SKY)
    # counters
    panel(fr, r0, 96, 43, 130, "COUNT", fg=mix(P.C["void"], CAGE, 0.8),
          bg=mix(P.C["void"], CAGE, 0.05))
    for i, (nm, val, col) in enumerate((("FREE", "1", SKY), ("TRAPPED", "1", CAGE),
                                        ("WALLS", "12", P.C["white"]),
                                        ("DOORS", "0", P.C["crimson"]))):
        fr.write(r0 + 1 + i, 98, nm, fg=P.C["dim"])
        fr.write(r0 + 1 + i, 112, val, fg=col)
    fr.write(r0 + 5, 98, f"LOVE = CAGE", fg=P.C["white"])
    W.hex_dump(fr, r0, 134, 7, 55, t, seed=17,
               fg=mix(P.C["void"], CAGE, 0.55), step=0.4)


def _status(fr, ctx, p):
    t = ctx.t
    fr.write(0, 7, "┤ FREE vs TRAPPED ├", fg=mix(P.C["void"], SKY, 0.9))
    fr.write(0, 30, "// FINAL DUET // HEART SCAN // CAGE", fg=P.C["dim"])
    fr.write(0, 70, "YOU=FREE  ME=TRAPPED", fg=P.C["white"])
    fr.write(0, 96, f"T {t:8.3f}", fg=P.C["dim"])
    fr.write(0, 112, f"SCAN {int(min(100.0, 100 * _repair_p(t) / 0.62)):3d}%",
             fg=GOLD)
    fr.rtext(0, "rc=0  LOVE=1  ESCAPE=0", fg=CAGE, pad=6)
    rule(fr, 1, fg=mix(P.C["void"], SKY, 0.4), step=12)
    fr.write(44, 7, "┤ STAGE ├", fg=mix(P.C["void"], CAGE, 0.7))
    fr.write(44, 20, f"SCENE TRAPPEDLOVE {T0:.3f}-{T1:.3f}", fg=P.C["dim"])
    fr.write(44, 56, f"BEAT {ctx.beat_i:03d}.{int(ctx.beat_p * 100):02d}", fg=CAGE)
    fr.write(44, 76, f"BAR {ctx.bar_i:03d}.{int(ctx.bar_p * 100):02d}", fg=CAGE)
    fr.write(44, 96, "HEART 100%  CAGE 100%  ESCAPE 0%", fg=P.C["white"])
    fr.write(44, 140, "NEXT: OUTRO 99", fg=GOLD)
    fr.rtext(44, f"RMS={ctx.rms:4.2f}  Z={ctx.local:6.2f}", fg=P.C["dim"], pad=6)
