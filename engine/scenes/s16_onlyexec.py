"""s16_onlyexec - THE ONLY EXECUTION (yandere / possessive / obsessive).

162.650  "if I can give them all the execution"
166.342  "then I can be your only execution"
170.035  "if I can have you back I will run the execution"
173.727  "though we are trapped, we are trapped, ah"  (last beat, the box closes)

One target is locked in a reticle, walled off from the world, tagged ONLY/MINE
while every other option is erased.  Red-dominant, occluded by swarms of the
word EXECUTION, watched by eyes, chained, counted: TARGETS=1, ALTERNATIVES=0.
"""
from __future__ import annotations

import math

import numpy as np

from .. import art
from .. import fx
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

from .s15_count import (mix, rule, panel, big, edges, dense_bg,
                        heart_fill, LANGS)

T0, T1 = 162.650, 173.727
L1 = TL.EVENTS["only_execution"]        # 162.650
L2 = TL.EVENTS["only_execution_2"]      # 166.342
L3 = TL.EVENTS["run_execution"]         # 170.035
L4 = TL.EVENTS["trapped_we"]            # 173.727 (s17 continues)

RED = P.C["crimson"]
BLOOD = P.C["blood"]
HOT = P.C["red"]


# ---------------------------------------------------------------------------
# small shared pieces
# ---------------------------------------------------------------------------
def _heart(fr, c0, r0, cw, ch, fg, fg2=None, gain=1.8, alpha=1.0,
           holes=(), dents=(), ramp=None):
    """A heart mask sized exactly to (cw, ch) cells."""
    mask = heart_fill(cw * 10, ch * 18, holes=holes, dents=dents)
    fr.paint_mask(mask, c0, r0, cw, ch, ramp=ramp or P.RAMP_BLOCK,
                  fg=fg, fg2=fg2 if fg2 is not None else P.C["white"],
                  gain=gain, alpha=alpha)


def _ellipse(w_px, h_px, sx=1.0, sy=1.0, soft=3.5):
    ys, xs = np.mgrid[0:h_px, 0:w_px].astype(np.float32)
    cx, cy = w_px * 0.5, h_px * 0.5
    rx = max(1.0, cx * sx)
    ry = max(1.0, cy * sy)
    d = np.sqrt(((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2)
    return np.clip((1.0 - d) * soft + 0.2, 0.0, 1.0)


def _eye(fr, r0, c0, w, h, look=(0.0, 0.0), open_p=1.0, fg=None):
    """A real eye: dark rim, pale sclera, hot iris, black pupil, glint, lids."""
    fg = fg or P.C["crimson"]
    wpx = w * 10
    hh = max(3, int(round(h * open_p)))
    rr = r0 + (h - hh) // 2
    sclera = _ellipse(wpx, hh * 18, 1.0, 1.0, soft=4.5)
    fr.paint_mask(sclera, c0, rr, w, hh, ramp=" ░▒▓█",
                  fg=mix(P.C["void"], P.C["white"], 0.62),
                  fg2=mix(P.C["blood"], P.C["void"], 0.5), gain=1.15)
    iw = max(4, int(w * 0.46))
    ih = max(3, hh - 1)
    iris = _ellipse(iw * 10, ih * 18, 1.0, 1.0, soft=5.5)
    ic0 = c0 + (w - iw) // 2 + int(look[0] * w * 0.16)
    ir0 = rr + (hh - ih) // 2 + int(look[1] * h * 0.12)
    fr.paint_mask(iris, ic0, ir0, iw, ih, ramp=" ░▒▓█",
                  fg=mix(P.C["blood"], HOT, 0.95), fg2=P.C["black"], gain=1.9)
    pw, ph = 2, max(2, ih // 2)
    pup = _ellipse(pw * 10, ph * 18, 1.0, 1.0, soft=6.0)
    pc0 = ic0 + (iw - pw) // 2
    pr0 = ir0 + (ih - ph) // 2
    fr.paint_mask(pup, pc0, pr0, pw, ph, ramp=" ▓█", fg=P.C["black"],
                  fg2=P.C["black"], gain=2.4)
    if fr.inb(pr0, pc0 + pw):
        fr.put(pr0, pc0 + pw, "●", fg=P.C["white"])
    # lids + lashes so the silhouette reads as an eye
    fr.write(rr - 1, c0 + 2, "▔" * max(0, w - 4), fg=mix(P.C["void"], RED, 0.85))
    fr.write(rr + hh, c0 + 2, "▁" * max(0, w - 4), fg=mix(P.C["void"], RED, 0.45))
    for k in range(4):
        cc = c0 + 3 + k * max(1, (w - 6) // 3)
        if cc < c0 + w - 1:
            fr.write(rr - 2, cc, "╱", fg=mix(P.C["void"], RED, 0.75))


def _chain(fr, r, c0, c1, t, fg=None, speed=9.0):
    """Rolling chain links."""
    fg = fg or mix(P.C["void"], P.C["crimson"], 0.7)
    pat = "○═◉═"
    off = int(t * speed)
    s = "".join(pat[(off + i) % 4] for i in range(c1 - c0))
    fr.write(r, c0, s, fg=fg)


def _blink(fr, r, c, t, seed=0, fg=None):
    """A tiny watching eye in the dark."""
    fg = fg or mix(P.C["void"], P.C["crimson"], 0.85)
    ph = (t * 0.9 + seed * 0.37) % 1.0
    if ph < 0.08:
        fr.write(r, c, "─", fg=fg)
    elif ph < 0.14:
        fr.write(r, c, "◎", fg=fg)
    else:
        fr.write(r, c, "◉", fg=fg)


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    _background(fr, ctx)
    _top_band(fr, ctx)
    _swarm(fr, ctx, seed=7, n=46, hot=0.14)
    _target_cell(fr, ctx)
    if _phase(t) == 1:
        _giant_eye(fr, ctx)
    _hero(fr, ctx)
    _eye_panel(fr, ctx)
    _chains(fr, ctx)
    _erased_strip(fr, ctx)
    _bottom(fr, ctx)
    _swarm(fr, ctx, seed=91, n=12, hot=0.05, occlude=True)
    if t >= L4 - 0.55:
        _execution_box(fr, ctx)
    _status(fr, ctx)
    edges(fr, mix(P.C["void"], RED, 0.55))
    # possession: red bloom, beat-slammed flashes
    beat_age = (t - L1) % (TL.EVENTS.get("bar", 1.846154) / 2.0)
    ctx.set_glitch(0.02 + 0.05 * (0.5 + 0.5 * math.sin(t * 3.1)))
    ctx.meta["bloom"] = 0.34
    ctx.meta["vignette"] = 1.0
    ctx.meta["tint"] = (BLOOD, 0.10)
    for lx, col in ((L1, HOT), (L2, P.C["white"]), (L3, RED)):
        a = t - lx
        if 0 <= a < 0.20:
            amp = 1.0 - a / 0.20
            ctx.meta["flash"] = 0.22 * amp
            ctx.meta["flash_color"] = col
            ctx.set_glitch(0.02 + 0.22 * amp)
            ctx.shake(2 + 3 * amp)
    if t > L4 - 0.55:
        p = fx.clamp((t - (L4 - 0.55)) / 0.55)
        ctx.set_glitch(0.03 + 0.16 * p)
        ctx.shake(1 + 4 * p)
        ctx.meta["flash"] = 0.18 * p
    return fr


# ---------------------------------------------------------------------------
# layers
# ---------------------------------------------------------------------------
def _background(fr, ctx):
    t = ctx.t
    dense_bg(fr, ctx, seed=61, fg=RED, hot=0.9)
    # vertical wall of EXECUTION glyph columns on both flanks
    for c in (0, 191):
        for r in range(0, fr.rows, 2):
            fr.put(r, c, "║", fg=mix(P.C["void"], RED, 0.35))
    # pulsing floor line
    fr.hline(43, 1, 190, "─", fg=mix(P.C["void"], RED, 0.3))
    # scattered small hearts in the noise
    for i in range(9):
        c = int((i * 23 + 5 + 4 * math.sin(t * 0.4 + i)) % 186) + 3
        r = (i * 11 + 3) % 40 + 2
        fr.write(r, c, "♥", fg=mix(P.C["void"], BLOOD, 0.8))


def _top_band(fr, ctx):
    t = ctx.t
    phase = _phase(t)
    fr.fill_rect(2, 2, 8, 189, " ", bg=mix(P.C["void"], BLOOD, 0.16))
    fr.hline(2, 2, 189, "═", fg=mix(P.C["void"], RED, 0.5))
    fr.write(2, 4, "┤ POSSESSION PROTOCOL ├", fg=HOT)
    fr.write(2, 30, "v3.0 // JEALOUSY=TRUE // MERCY=FALSE", fg=mix(P.C["void"], P.C["fg"], 0.8))
    fr.write(2, 72, f"T {t:8.3f}", fg=P.C["dim"])
    fr.rtext(2, "SIGNAL: OBSESSIVE  LOCK: HARD", fg=HOT, pad=6)
    # scrolling ONLY tags
    W.marquee(fr, 3, " ONLY  MINE  ONLY  MINE  ONLY  MINE  ONLY  MINE ",
              t, speed=26.0, fg=mix(P.C["void"], HOT, 0.75), gap=3)
    # left inset: how many targets remain
    panel(fr, 4, 3, 8, 40, "TARGETS", fg=RED, bg=mix(P.C["void"], BLOOD, 0.22))
    big(fr, "01", 5, 26, 3, fg=mix(RED, P.C["white"], 0.35), fg2=mix(RED, P.C["white"], 0.7), align="center")
    fr.write(5, 5, "TARGETS=1", fg=P.C["white"])
    fr.write(6, 5, "OTHERS=0", fg=HOT)
    fr.write(7, 5, "ONLY=YOU", fg=P.C["gold"])
    # right inset: alternatives removed
    panel(fr, 4, 151, 8, 188, "ALTERNATIVES", fg=RED, bg=mix(P.C["void"], BLOOD, 0.22))
    erased = _erased_count(ctx)
    big(fr, "00", 5, 179, 3, fg=mix(RED, P.C["white"], 0.35), fg2=mix(RED, P.C["white"], 0.7), align="center")
    fr.write(5, 153, "ALTERNATIVES=0", fg=P.C["white"])
    fr.write(6, 153, f"ERASED {erased:02d}", fg=P.C["gold"])
    fr.write(7, 153, "KEEPING 1", fg=HOT)
    # target id centre
    fr.write(4, 46, "◆ TARGET 01 // LOCKED // IN LOVE", fg=mix(P.C["void"], RED, 0.9))
    fr.write(5, 46, f"PHASE {phase}  CANDIDATES {max(0, 6 - erased)}  "
                    f"KILLS {erased}:{max(0, 6 - erased)}", fg=mix(P.C["void"], P.C["fg"], 0.9))
    _blink(fr, 5, 78, t, 3, fg=HOT)
    _blink(fr, 5, 82, t, 7, fg=HOT)
    fr.write(6, 46, "ONLY ONE MAY BE LOVED", fg=mix(P.C["void"], HOT, 0.8))
    fr.write(7, 46, "ALL OTHERS: EXECUTED", fg=mix(P.C["void"], RED, 0.9))
    for i in range(10):
        fr.write(7, 70 + i * 3, "♥", fg=mix(P.C["void"], BLOOD, 0.9))


def _phase(t):
    if t < L2:
        return 0
    if t < L3:
        return 1
    if t < L4 - 0.55:
        return 2
    return 3


def _erased_count(ctx):
    """Options erased so far: climbs to 6 over the scene."""
    t = ctx.t
    p = fx.clamp((t - L1) / (L3 - L1))
    return int(round(p * 6))


def _swarm(fr, ctx, seed=7, n=40, hot=0.1, occlude=False):
    rng = ctx.rng(seed)
    t = ctx.t
    for i in range(n):
        x = rng.random()
        y = rng.random()
        sp = 0.5 + rng.random()
        hh = rng.random()
        c = int((x * 192 + 11 * math.sin(t * 0.55 * sp + i * 1.7)
                 + 6 * math.cos(t * 0.19 + i * 0.7)) % (192 - 9))
        r = int((y * 45 + 2.1 * math.sin(t * 0.72 * sp + i * 0.9)) % 45)
        if r < 2 or r > 43:
            continue
        if occlude and 9 <= r <= 24 and (62 <= c <= 152 or c >= 150):
            continue
        if hh < hot:
            fr.write(r, c, "EXECUTION", fg=P.C["white"] if hh < hot * 0.3 else HOT)
        elif hh < hot + 0.4:
            fr.write(r, c, "EXECUTION", fg=mix(P.C["void"], RED, 0.55))
        else:
            fr.write(r, c, "EXECUTION" if hh < 0.8 else "ONLY",
                     fg=mix(P.C["void"], BLOOD, 0.85))


def _giant_eye(fr, ctx):
    """A whole-stage eye during the ONLY phase: she is watching you."""
    t = ctx.t
    rc, cc = 21, 96
    half_h, half_w = 14, 52
    # sclera: scanline ellipse, dim so the hero word still reads on top
    for r in range(rc - half_h, rc + half_h + 1):
        if r < 2 or r > 43:
            continue
        dy = (r - rc) / float(half_h)
        if abs(dy) > 1.0:
            continue
        w = int(half_w * math.sqrt(max(0.0, 1.0 - dy * dy)))
        for c in range(cc - w, cc + w + 1):
            if not fr.inb(r, c):
                continue
            edge = abs(c - cc) / float(max(1, w))
            col = mix(P.C["void"], mix(P.C["blood"], P.C["white"], 0.30),
                      0.60 + 0.22 * (1.0 - edge))
            fr.put(r, c, "░" if (r + c) % 3 else "▒", fg=col)
    # lids: heavy top arc + thin bottom, lashes at both corners
    for c in range(cc - half_w + 6, cc + half_w - 5):
        dx = (c - cc) / float(half_w)
        r = rc - int(round(half_h * math.sqrt(max(0.0, 1.0 - dx * dx))))
        fr.put(r, c, "▄", fg=mix(RED, P.C["white"], 0.25))
        fr.put(r - 1, c, "▀", fg=mix(BLOOD, P.C["white"], 0.15))
        rb = rc + int(round(half_h * math.sqrt(max(0.0, 1.0 - dx * dx))))
        fr.put(rb, c, "▀", fg=mix(P.C["void"], BLOOD, 0.7))
    for side in (-1, 1):
        for i in range(5):
            fr.put(rc - 6 + i, cc + side * (half_w - 8 + i), "╱" if side > 0 else "╲",
                   fg=mix(P.C["void"], RED, 0.8))
    # iris tracks the viewer, pupil dilates on the beat
    beat = 0.5 + 0.5 * math.sin(t * 3.4)
    ic = cc + int(round(4.0 * math.sin(t * 0.53)))
    ir = rc + int(round(2.0 * math.cos(t * 0.37)))
    irr, irc = 9, 19
    for r in range(ir - irr, ir + irr + 1):
        dy = (r - ir) / float(irr)
        if abs(dy) > 1.0:
            continue
        w = int(irc * math.sqrt(max(0.0, 1.0 - dy * dy)))
        for c in range(ic - w, ic + w + 1):
            if not fr.inb(r, c):
                continue
            e = ((r - ir) / float(irr)) ** 2 + ((c - ic) / float(irc)) ** 2
            if e <= 0.16:                       # pupil
                fr.put(r, c, "█", fg=P.C["void"])
            elif e <= 0.55:
                fr.put(r, c, "▓", fg=mix(BLOOD, P.C["void"], 0.62))
            elif e <= 0.86:
                fr.put(r, c, "▒", fg=mix(mix(RED, HOT, 0.55), P.C["void"], 0.18))
            else:
                fr.put(r, c, "▒", fg=mix(HOT, P.C["white"], 0.35))
    for r in range(ir - 3, ir - 1):
        for c in range(ic - 5, ic - 2):
            if fr.inb(r, c):
                fr.put(r, c, "●", fg=P.C["white"])
    fr.write(rc - half_h - 1, cc - 14, "// WITNESS: YOU", fg=mix(P.C["void"], RED, 0.9))
    fr.write(rc + half_h + 1, cc + 8, f"PUPIL {int(18 + 6 * beat):02d}%  BLINK 0.00",
             fg=mix(P.C["void"], HOT, 0.7))


def _target_cell(fr, ctx):
    """The one target: heart in a cage, inside a reticle, isolated by walls."""
    t = ctx.t
    r0, c0, r1, c1 = 10, 4, 24, 61
    panel(fr, r0, c0, r1, c1, "TARGET 01 // ISOLATED",
          fg=mix(P.C["void"], RED, 0.75), bg=mix(P.C["void"], BLOOD, 0.20))
    # walls of the cage
    wr0, wr1 = 12, 21
    wc0, wc1 = 9, 40
    fr.box(wr0, wc0, wr1, wc1, 2, fg=mix(RED, P.C["white"], 0.15))
    for r in range(wr0 + 1, wr1):
        fr.put(r, wc0, "║", fg=RED)
        fr.put(r, wc1, "║", fg=RED)
    # heart (beats)
    beat = abs(math.sin(t * 4.4))
    gain = 1.55 + 0.55 * beat
    _heart(fr, wc0 + 5, wr0 + 2, 18, 10, fg=mix(BLOOD, RED, 0.5 + 0.3 * beat),
           fg2=mix(RED, P.C["white"], 0.5), gain=gain)
    # reticle corners + crosshair
    cx, cy = wc0 + 16, wr0 + 4
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        for k in range(1, 5):
            fr.put(cy + dr * 5, cx + dc * k, "─", fg=HOT)
            fr.put(cy + dr * k, cx + dc * 6, "│", fg=HOT)
        fr.put(cy + dr * 5, cx + dc * 6, "┼", fg=P.C["white"])
    fr.write(wr1 - 1, wc0 + 2, "◎ LOCK", fg=P.C["white"])
    fr.write(wr1 - 1, wc0 + 12, f"CONF {0.98 + 0.019 * beat:.3f}",
             fg=mix(P.C["void"], P.C["fg"], 0.9))
    # target data column
    rows = [
        ("ID", "01/YOU", P.C["white"]),
        ("STATE", "MINE", HOT),
        ("LOCK", "HARD", P.C["gold"]),
        ("ESCAPE", "IMPOSSIBLE", RED),
        ("HEART", f"{int(88 + 11 * beat)}bpm", mix(P.C["void"], HOT, 0.9)),
        ("WALLS", "12/12", P.C["fg"]),
    ]
    for i, (nm, val, col) in enumerate(rows):
        fr.write(r0 + 2 + i, 43, nm, fg=P.C["dim"])
        fr.write(r0 + 2 + i, 51, val, fg=col)
    for i in range(3):
        fr.write(wr0 + 2 + i, wc1 + 1, "█", fg=mix(P.C["void"], RED, 0.5 + 0.2 * i))
    fr.write(r1 - 1, c0 + 2, "NO DOOR // NO KEY // NO EXIT", fg=RED)


def _hero(fr, ctx):
    t = ctx.t
    phase = _phase(t)
    if phase == 0:
        word, sub = "ALL", "IF I CAN GIVE THEM ALL THE EXECUTION"
        h = 8 + min(3, int((t - L1) / 1.1))
        col = P.dark(RED, 0.1)
    elif phase == 1:
        word, sub = "ONLY", "THEN I CAN BE YOUR ONLY EXECUTION"
        h = 6 if t - L2 < 0.9 else 5
        col = RED
    elif phase == 2:
        word, sub = "RUN", "IF I CAN HAVE YOU BACK I WILL RUN THE EXECUTION"
        h = 9
        col = HOT
    else:
        word, sub = "MINE", "THOUGH WE ARE TRAPPED, WE ARE TRAPPED"
        h = 8
        col = P.C["white"]
    r0 = 12 if phase != 1 else 17
    if phase == 1:
        # leave the iris visible: no opaque slab, only thin rules top/bottom
        fr.hline(9, 63, 150, "─", fg=mix(P.C["void"], RED, 0.5))
        fr.hline(25, 63, 150, "─", fg=mix(P.C["void"], RED, 0.5))
    else:
        fr.fill_rect(9, 63, 25, 150, " ", bg=mix(P.C["void"], BLOOD, 0.16))
    fr.hline(9, 63, 150, "─", fg=mix(P.C["void"], RED, 0.5))
    fr.hline(25, 63, 150, "─", fg=mix(P.C["void"], RED, 0.5))
    fr.write(9, 65, f"┤ {['ALL','ONLY','RUN','MINE'][phase]} ├", fg=col)
    fr.write(9, 130, "┤ ONLY EXECUTION ├", fg=mix(P.C["void"], HOT, 0.8))
    big(fr, word, r0, 106, h, fg=mix(col, P.C["white"], 0.30),
        fg2=mix(RED, P.C["white"], 0.65), align="center", echo=0)
    # stamp tags around the hero
    for i, tag in enumerate(("ONLY", "MINE", "ONLY", "MINE", "ONLY")):
        rr = 10 + i * 3
        cc = 66 if i % 2 == 0 else 140
        fr.write(rr, cc, f"[{tag}]", fg=mix(P.C["void"],
                 P.C["white"] if i == 2 else HOT, 0.5 + 0.5 * abs(math.sin(t * 2 + i))))
    fr.write(22, 65, sub[:86], fg=mix(P.C["void"], P.C["fg"], 0.95))
    fr.write(24, 65, f"W/ {word}  //  POSSESSIVE-LOCK  //  NO ALTERNATIVE",
             fg=mix(P.C["void"], RED, 0.8))
    fr.write(24, 130, f"T+{t - L1:6.2f}s", fg=P.C["gold"])
    # possessive ticker under the hero
    W.marquee(fr, 26, "MINE MINE MINE MINE MINE ", t, speed=18.0,
              fg=mix(P.C["void"], HOT, 0.55), gap=5)



def _execution_box(fr, ctx):
    """The last beat: a closed box whose walls are written with EXECUTION."""
    t = ctx.t
    p = fx.clamp((t - (L4 - 0.55)) / 0.55)
    wall = mix(P.C["void"], HOT, 0.55 + 0.35 * abs(math.sin(t * 4.0)))
    for r in (8, 27):
        fr.write(r, 60, "EXECUTION " * 9, fg=wall)
    for c in (60, 61, 151, 152):
        for r in range(9, 27):
            fr.put(r, c, "║", fg=mix(P.C["void"], BLOOD, 0.9))
    for i, ch in enumerate("EXECUTION"):
        rr = 9 + i * 2
        fr.write(rr, 60, ch, fg=P.C["white"])
        fr.write(rr, 152, ch, fg=P.C["white"])
    fr.write(25, 64, " NO DOOR // NO KEY // NO EXIT ",
             fg=mix(P.C["void"], RED, 0.95))
    if (int(t * 6) % 2) == 0:
        fr.write(8, 30, " ◉ LOCKED ", fg=P.C["white"], bg=mix(P.C["void"], BLOOD, 0.8))
    fr.write(25, 122, f"◉ BOX CLOSED {p * 100:3.0f}%", fg=P.C["gold"])


def _eye_panel(fr, ctx):
    t = ctx.t
    r0, c0 = 10, 154
    panel(fr, r0, c0, 24, 188, "WATCHER",
          fg=mix(P.C["void"], RED, 0.7), bg=mix(P.C["void"], BLOOD, 0.18))
    look = (math.sin(t * 0.9), math.cos(t * 1.3) * 0.6)
    _eye(fr, r0 + 3, c0 + 4, 26, 6, look=look, fg=mix(BLOOD, HOT, 0.7))
    fr.write(r0 + 9, c0 + 3, "I SEE ONLY YOU", fg=P.C["white"])
    fr.write(r0 + 10, c0 + 3, "FOV 0.00deg", fg=mix(P.C["void"], P.C["fg"], 0.9))
    fr.write(r0 + 11, c0 + 3, "OBJ 1 / 1", fg=HOT)
    # small eyes down the side
    for i in range(4):
        _blink(fr, r0 + 12 + i * 0, c0 + 3 + i * 6, t, i * 2, fg=RED)
    for i in range(2):
        fr.write(r0 + 13 + i, c0 + 2, "◉ ◎ ◉ ◎ ◉ ◎ ◉ ◎ ◉", fg=mix(P.C["void"], RED, 0.7))


def _chains(fr, ctx):
    t = ctx.t
    for i, r in enumerate((27, 28, 29)):
        _chain(fr, r, 2, 190, t, fg=mix(P.C["void"], RED, 0.45 + 0.15 * i),
               speed=7.0 + i * 2.5)
    fr.write(28, 4, " BOUND ", fg=P.C["white"], bg=mix(P.C["void"], BLOOD, 0.6))
    fr.write(28, 86, " BOUND ", fg=P.C["white"], bg=mix(P.C["void"], BLOOD, 0.6))
    fr.write(28, 168, " BOUND ", fg=P.C["white"], bg=mix(P.C["void"], BLOOD, 0.6))
    for c in (2, 46, 92, 146, 189):
        for r in range(26, 31):
            fr.put(r, c, "║", fg=mix(P.C["void"], BLOOD, 0.8))
    # hearts hung on the chains
    for i in range(7):
        c = 14 + i * 26 + int(2 * math.sin(t + i))
        fr.write(29, c, "♥", fg=mix(BLOOD, HOT, 0.4 + 0.5 * abs(math.sin(t * 2 + i))))


def _erased_strip(fr, ctx):
    """Where the other options used to be: six boxes, crossed out one by one."""
    t = ctx.t
    erased = _erased_count(ctx)
    r0, c0 = 31, 4
    panel(fr, r0, c0, r0 + 4, 122, "ERASURE LOG", fg=mix(P.C["void"], RED, 0.7),
          bg=mix(P.C["void"], BLOOD, 0.14))
    for i in range(6):
        c = c0 + 3 + i * 19
        dead = i < erased
        if dead:
            for k in range(7):
                fr.write(r0 + 1, c + k * 2, "▓", fg=mix(P.C["void"], BLOOD, 0.8))
                fr.write(r0 + 2, c + k * 2, "▓", fg=mix(P.C["void"], BLOOD, 0.6))
            fr.write(r0 + 1, c + 1, "✗", fg=HOT)
            fr.write(r0 + 2, c, f"ALT{i + 1:02d} ERASED", fg=mix(P.C["void"], RED, 0.9))
        elif i == erased:
            fr.write(r0 + 1, c, "■ ■ ■", fg=P.C["white"])
            fr.write(r0 + 2, c, f"ALT{i + 1:02d} NEXT", fg=HOT)
            fr.put(r0 + 3, c + 2, "▼", fg=HOT)
        else:
            fr.write(r0 + 1, c, "□ □ □", fg=mix(P.C["void"], P.C["line"], 0.9))
            fr.write(r0 + 2, c, f"ALT{i + 1:02d} WAIT", fg=P.C["grid"])
    fr.write(r0 + 4, c0 + 2, f"> rm --force alternate_{erased + 1:02d}/*  "
                             f"targets_left={max(0, 6 - erased)}", fg=mix(P.C["void"], P.C["fg"], 0.9))
    # right: kill log
    panel(fr, r0, 126, r0 + 4, 188, "KILL LOG", fg=mix(P.C["void"], RED, 0.7),
          bg=mix(P.C["void"], BLOOD, 0.14))
    for i in range(3):
        dead = i < erased
        fr.write(r0 + 1 + i, 128, f"> erase option {i + 1:02d} ...", fg=P.C["dim"])
        fr.write(r0 + 1 + i, 150, "OK" if dead else "..", fg=P.C["green"] if dead else P.C["grid"])
        fr.write(r0 + 1 + i, 154, f"{erased:02d} left" if i == 2 else "", fg=HOT)
    fr.write(r0 + 4, 128, f"> keep option 01 (YOU)  targets_left=1", fg=HOT)


def _bottom(fr, ctx):
    t = ctx.t
    # big caged heart on the floor
    r0 = 36
    _heart(fr, 6, r0, 18, 10, fg=mix(BLOOD, RED, 0.55), fg2=mix(RED, P.C["white"], 0.5),
           gain=1.65 + 0.4 * abs(math.sin(t * 4.4)))
    for c in range(5, 36, 2):
        fr.put(r0 + 6, c, "█", fg=mix(P.C["void"], BLOOD, 0.7))
    fr.write(r0 + 5, 38, "TRAPPED", fg=mix(P.C["void"], P.C["white"], 0.9))
    fr.write(r0 + 6, 38, "IN LOVE", fg=HOT)
    # mini heart grid: one per obsession
    for i in range(10):
        c = 52 + i * 4
        fr.write(r0 + 1, c, "♥", fg=mix(P.C["void"], BLOOD, 0.6))
        fr.write(r0 + 2, c, "♥", fg=mix(P.C["void"], BLOOD, 0.75))
        fr.write(r0 + 3, c, "♥", fg=mix(P.C["void"], RED, 0.8))
    fr.write(r0 + 6, 52, "ONLY EXECUTION REMAINS", fg=P.C["white"])
    fr.write(r0 + 6, 76, "MINE MINE MINE", fg=HOT)
    W.hex_dump(fr, r0, 128, 7, 61, t, seed=13,
               fg=mix(P.C["void"], RED, 0.55), step=0.4)
    fr.write(r0, 96, "POSSESSION", fg=RED)
    fr.write(r0 + 1, 96, "HEART 100%", fg=HOT)
    fr.write(r0 + 2, 96, "FREEDOM 0%", fg=P.C["white"])
    W.progress_bar(fr, r0 + 3, 96, 28, 1.0, fg=HOT, show_pct=False)
    fr.write(r0 + 4, 96, "OWNERSHIP", fg=RED)
    W.progress_bar(fr, r0 + 5, 96, 28, 1.0, fg=RED, show_pct=False)
    fr.write(r0 + 6, 96, "ALTERNATIVES", fg=RED)
    W.progress_bar(fr, r0 + 7, 96, 28, 0.0, fg=P.C["grid"], show_pct=False)


def _status(fr, ctx):
    t = ctx.t
    phase = _phase(t)
    fr.write(0, 7, "┤ ONLY EXECUTION ├", fg=P.C["white"])
    fr.write(0, 27, "// YANDERE PROTOCOL // POSSESSION LOOP", fg=mix(P.C["void"], RED, 0.9))
    fr.write(0, 70, f"PHASE {phase}  TARGETS=1  ALTERNATIVES=0", fg=HOT)
    fr.write(0, 112, f"T {t:8.3f}", fg=P.C["dim"])
    fr.rtext(0, "rc=0  LOVE=1  ESCAPE=0", fg=HOT, pad=6)
    rule(fr, 1, fg=mix(P.C["void"], RED, 0.55), step=12)
    fr.write(44, 7, "┤ STAGE ├", fg=mix(P.C["void"], RED, 0.7))
    fr.write(44, 20, f"SCENE ONLYEXEC {T0:.3f}-{T1:.3f}", fg=P.C["dim"])
    fr.write(44, 56, f"BEAT {ctx.beat_i:03d}.{int(ctx.beat_p * 100):02d}", fg=RED)
    fr.write(44, 76, f"BAR {ctx.bar_i:03d}.{int(ctx.bar_p * 100):02d}", fg=RED)
    fr.write(44, 96, "MINE=TRUE  ONLY=YOU  WALLS=12", fg=HOT)
    fr.write(44, 140, "NEXT: STUDY", fg=P.C["gold"])
    fr.rtext(44, f"RMS={ctx.rms:4.2f}  Z={ctx.local:6.2f}", fg=P.C["dim"], pad=6)
