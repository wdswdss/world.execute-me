"""s13 fragments — memories erased, the heart cracks and falls, god is challenged.

"erase all the pointless fragments" / "you won't leave me so disheartened" /
"Challenging your God, you have made some illegal arguments"
"""
from __future__ import annotations

import math

import numpy as np

from .. import palette as P, fx, widgets as W, art
from .. import font as F
from ..assets import BEAT, T0

C_VOID = P.C["void"]
C_VOID2 = P.C["void2"]
C_PANEL = P.C["panel"]
C_PANEL2 = P.C["panel2"]
C_GRID = P.C["grid"]
C_LINE = P.C["line"]
C_DIM = P.C["dim"]
C_MID = P.C["mid"]
C_FG = P.C["fg"]
C_WHITE = P.C["white"]
C_PRIMARY = P.C["primary"]
C_TEAL = P.C["teal"]
C_GOLD = P.C["gold"]
C_AMBER = P.C["amber"]
C_RED = P.C["red"]
C_CRIMSON = P.C["crimson"]
C_BLOOD = P.C["blood"]
C_MAGENTA = P.C["magenta"]
C_BLUE = P.C["blue"]
C_VIOLET = P.C["violet"]

I_DOT = F.char_index("·")
I_CELL = F.char_index("▪")
I_RING = F.char_index("○")
I_BLOCK = F.char_index("█")
I_HALF = F.char_index("▄")
I_H = F.char_index("─")
I_V = F.char_index("│")
I_D1 = F.char_index("╱")
I_D2 = F.char_index("╲")
I_X = F.char_index("×")
I_SPARK = F.char_index("◆")

W_IDX = 192
T_S = 122.041
DUR = 11.069
T_CRACK = 125.734
T_ILLEGAL = 129.426

# ------------------------------------------------------------------ fragments --
_MEM = ["you said hello", "3:14 am call", "first snow", "hand in hand",
        "the promise", "room 402", "last message", "i'll wait",
        "wake me up", "same dream", "your voice", "cursor blinking",
        "hello? you there", "loading ...", "1 new message", "delete?",
        "hold me", "don't go", "see you soon", "goodnight"]
_SCR = "░▒▓#@%&*+=/\\<>|"

_FR = []
_rng = np.random.default_rng(4242)
_rows = (4, 11, 18, 25, 32)
_cols = (2, 50, 98, 146)
for k in range(20):
    r = _rows[k // 4] + int(_rng.integers(-1, 2))
    c = _cols[k % 4] + int(_rng.integers(-1, 2))
    _FR.append(dict(r=r, c=c, w=42, h=4, mem=_MEM[k % len(_MEM)],
                    tag=f"FRAG_{k:03d}", hsh=float(_rng.random())))
N_FR = len(_FR)


def _erase_t(f):
    return 0.55 + (f["c"] + f["w"] * 0.5) / W_IDX * 2.75 + 0.16 * f["hsh"]


def _beam_col(lt):
    return 2.0 + lt / 2.95 * (W_IDX - 4)


def _beam_heart(lt):
    return fx.clamp((lt - 3.75) / 0.60) * (_HH + 3)


# --------------------------------------------------------------------- heart --
_HW, _HH = 42, 24


def _heart_mask(w_px, h_px):
    """Solid classic heart silhouette (engine art.heart_fill)."""
    return art.heart_fill(w_px, h_px)


_hm = _heart_mask(_HW * 10, _HH * 18)
HEART = np.clip(_hm.reshape(_HH, 18, _HW, 10).mean(axis=(1, 3)), 0, 1)
_heart_rows, _heart_cols = np.nonzero(HEART > 0.14)
HEART_IDX = (np.clip(HEART[_heart_rows, _heart_cols] * 4 + 0.5, 0, 4)).astype(np.int16)
_HRAMP = " ░▒▓█"
HEART_CH = np.array([F.char_index(_HRAMP[i]) for i in range(5)], np.int16)

# cracks wander down through the heart
_CRACKS = []
_crng = np.random.default_rng(77)
for k in range(4):
    pts = []
    r = 1 + k * 2
    c = 8 + k * 9 + int(_crng.integers(-3, 4))
    for step in range(18):
        pts.append((r, c))
        r += 1
        c += int(_crng.integers(-1, 2))
        c = max(1, min(_HW - 2, c))
        if r >= _HH - 1:
            break
    _CRACKS.append(pts)


def _plot(fr, rs, cs, ch, fg, mask=None):
    rs = np.asarray(rs, np.int32)
    cs = np.asarray(cs, np.int32)
    rcl = np.clip(rs, 0, fr.rows - 1)
    ccl = np.clip(cs, 0, fr.cols - 1)
    good = (rs == rcl) & (cs == ccl)
    if mask is not None:
        good &= np.asarray(mask, bool)
    if not good.any():
        return
    cha = np.asarray(ch)
    if cha.ndim == 0:
        fr.ch[rcl[good], ccl[good]] = cha
    else:
        if cha.shape[0] == good.shape[0]:
            fr.ch[rcl[good], ccl[good]] = cha[good]
        else:
            fr.ch[rcl[good], ccl[good]] = cha
    fga = np.asarray(fg, np.uint8)
    if fga.ndim == 1:
        fr.fg[rcl[good], ccl[good]] = fga
    else:
        if fga.shape[0] == good.shape[0]:
            fr.fg[rcl[good], ccl[good]] = fga[good]
        else:
            fr.fg[rcl[good], ccl[good]] = fga


def _scramble(text, salt, fi, amount):
    if amount <= 0:
        return text
    out = []
    state = (fi * 1103515245 + salt * 12345) & 0x7FFFFFFF
    for i, ch in enumerate(text):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        if ch != " " and (state & 0xFF) / 255.0 < amount:
            out.append(_SCR[(state >> 8) % len(_SCR)])
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------- page --
def _bg(fr, ctx):
    t = ctx.t
    lt = t - T_S
    fr.fill_rect(0, 0, 44, W_IDX - 1, " ", bg=C_VOID)
    # memory grid + drifting hex noise
    for r in range(2, 45, 3):
        fr.fill_rect(r, 0, r, W_IDX - 1, "·", fg=P.mix(C_GRID, C_VOID, 0.42))
    rng = np.random.default_rng(31)
    for k in range(16):
        r = int(rng.integers(2, 44))
        c = int((t * (3.0 + 6.0 * rng.random()) + rng.random() * 60) % 60) + \
            int(rng.integers(0, 130))
        txt = "".join(_SCR[(int(rng.integers(0, len(_SCR))) + k) % len(_SCR)]
                      for _ in range(14))
        fr.write(r, c, txt, fg=P.mix(C_GRID, C_VOID, 0.55))
    # vertical scan sweep
    sr = int((t * 36.0) % (W_IDX + 40)) - 20
    for c in range(max(0, sr - 2), min(W_IDX, sr + 3)):
        a = 1.0 - abs(c - sr) / 3.0
        fr.fill_rect(2, c, 44, c, " ", bg=P.mix(C_BLUE, C_VOID, 1.0 - 0.10 * a))
    gl = 0.020 + 0.030 * ctx.pulse
    if t >= T_CRACK:
        gl += 0.030 * fx.smoothstep(t, T_CRACK, T_CRACK + 1.5)
    if t >= T_ILLEGAL:
        storm = fx.smoothstep(t, T_ILLEGAL, T_ILLEGAL + 3.0)
        gl += 0.020 + 0.075 * storm
        # red error rain, denser as the storm grows
        rng2 = np.random.default_rng(991)
        for k in range(46):
            c = int(rng2.integers(0, W_IDX))
            head = (t * (10.0 + 22.0 * rng2.random()) + rng2.random() * 40) % 46
            for q in range(4 + int(6 * storm)):
                r = int(head) - q
                if 2 <= r < 45:
                    fr.put(r, c, "░" if q else "▒",
                           fg=P.mix(C_CRIMSON, C_VOID, 0.35 + 0.10 * q))
        for k in range(14):
            rr = int(rng2.integers(3, 40))
            cc = int(rng2.integers(0, W_IDX - 24))
            fr.write(rr, cc, "".join(_SCR[int(rng2.integers(0, len(_SCR)))]
                                     for _ in range(12)),
                     fg=P.mix(C_BLOOD, C_VOID, 0.55))
    ctx.set_glitch(min(0.140, gl))


def _big_words(fr, ctx, t):
    lt = t - T_S
    a = fx.smoothstep(lt, 0.25, 1.20) * (1.0 - fx.smoothstep(lt, 3.1, 3.9))
    if a > 0.02:
        fr.paint_text("FRAGMENTS", 17, 96, 5, P.mix(C_VIOLET, C_VOID, 0.60),
                      P.mix(C_VIOLET, C_WHITE, 0.35), align="center",
                      ramp=P.RAMP_BLOCK, alpha=min(1.0, a * 0.55))
    a = fx.smoothstep(lt, 4.1, 5.0) * (1.0 - fx.smoothstep(lt, 7.0, 7.9))
    if a > 0.02:
        fr.paint_text("DISHEARTENED", 19, 96, 5, P.mix(C_GOLD, C_VOID, 0.62),
                      P.mix(C_GOLD, C_WHITE, 0.28), align="center",
                      ramp=P.RAMP_BLOCK, alpha=min(1.0, a * 0.52))
    a = fx.smoothstep(lt, 7.55, 8.10)
    if a > 0.02:
        q = fx.smoothstep(lt, 7.6, 9.6)
        h = int(round(4 + 3 * q))
        fr.paint_text("ILLEGAL", 9, 96, h, P.mix(C_RED, C_VOID, 0.50),
                      P.mix(C_RED, C_WHITE, 0.45), align="center",
                      ramp=P.RAMP_BLOCK, alpha=min(1.0, a * 0.55))
        fr.paint_text("ARGUMENT", 9 + h + 1, 96, h,
                      P.mix(C_RED, C_VOID, 0.52),
                      P.mix(C_RED, C_WHITE, 0.40), align="center",
                      ramp=P.RAMP_BLOCK, alpha=min(1.0, a * 0.50))


def _fragments(fr, ctx, t):
    lt = t - T_S
    beam = _beam_col(lt)
    fi = ctx.fi
    rng = np.random.default_rng(fi * 977 + 13)
    for f in _FR:
        et = _erase_t(f)
        r, c, w, h = f["r"], f["c"], f["w"], f["h"]
        if lt > et + 1.15:
            # erased: only dotted outline remains
            if lt < et + 2.6:
                fade = 1.0 - fx.smoothstep(lt, et + 1.15, et + 2.6)
                col = P.mix(C_GRID, C_VOID, 1.0 - 0.45 * fade)
                for cc in range(c, c + w, 2):
                    fr.put(r, cc, "·", fg=col)
                    fr.put(r + h, cc, "·", fg=col)
                for rr in range(r, r + h + 1, 2):
                    fr.put(rr, c, "·", fg=col)
                    fr.put(rr, c + w - 1, "·", fg=col)
            continue
        if lt < et:
            # intact memory panel
            fr.fill_rect(r, c, r + h, c + w, " ", bg=C_PANEL)
            fr.box(r, c, r + h, c + w, 1, fg=P.mix(C_LINE, C_VOID, 0.10),
                   bg=C_PANEL, title=f["tag"])
            fr.write(r + 1, c + 2, f["mem"], fg=P.mix(C_GOLD, C_VOID, 0.10 + 0.20 * f["hsh"]))
            fr.write(r + 2, c + 2, "".join(_SCR[int(rng.integers(0, len(_SCR)))]
                                           for _ in range(w - 5)),
                     fg=P.mix(C_GRID, C_VOID, 0.35))
            # corner ticks
            fr.put(r, c, "┌", fg=P.mix(C_VIOLET, C_VOID, 0.20))
            fr.put(r + h, c + w, "┘", fg=P.mix(C_VIOLET, C_VOID, 0.20))
        else:
            # erasing: scan box + scrambles
            k = (lt - et) / 1.15
            fr.fill_rect(r, c, r + h, c + w, " ", bg=P.mix(C_PANEL2, C_RED, 0.10 * k))
            fr.box(r, c, r + h, c + w, 2, fg=P.mix(C_RED, C_WHITE, 0.25),
                   title=_scramble(f["tag"], 3, fi, 0.9))
            fr.write(r + 1, c + 2, _scramble(f["mem"], 9, fi, 0.35 + 0.65 * k),
                     fg=P.mix(C_RED, C_WHITE, 0.25))
            fr.write(r + 2, c + 2,
                     _scramble(f["mem"][::-1], 17, fi, 0.55 + 0.45 * k),
                     fg=P.mix(C_CRIMSON, C_VOID, 0.25))
            if k > 0.45:
                for _ in range(3):
                    rr = r + int(rng.integers(0, h + 1))
                    _plot(fr, (rr,), (c + int(rng.integers(0, w)),),
                          I_BLOCK, P.mix(C_RED, C_WHITE, 0.4))
    # the erasing beam
    if 0.3 < lt < 3.7:
        bc = int(beam)
        for c in range(max(0, bc - 3), min(W_IDX, bc + 4)):
            a = 1.0 - abs(c - bc) / 4.0
            if a <= 0:
                continue
            col = P.mix(C_WHITE, C_PRIMARY, 1.0 - a)
            for rr in range(2, 45, 1):
                if (rr + c) % 2 == 0 or a > 0.5:
                    fr.put(rr, c, "║" if a > 0.55 else "│", fg=col)
        fr.write(1, max(0, bc - 12), "▼ ERASE", fg=C_WHITE)
        fr.write(2, max(0, bc - 3), "╨", fg=C_WHITE)


def _heart_draw(fr, ctx, t):
    lt = t - T_S
    if lt < 2.90 or lt > 8.2:
        return
    r0 = 9
    c0 = 96 - _HW // 2
    # particles converge into the heart before it materialises
    if lt < 3.95:
        prng = np.random.default_rng(ctx.fi * 53 + 7)
        for k in range(120):
            ang = prng.random() * 2 * math.pi
            rad0 = 30.0 + 90.0 * prng.random()
            sp = 0.55 + 0.65 * prng.random()
            p = fx.clamp((lt - 2.90) / 0.95 * sp)
            rad = rad0 * (1.0 - p) + 2.0
            rr = int(round(r0 + _HH * 0.5 + math.sin(ang) * rad * 0.5))
            cc = int(round(96 + math.cos(ang) * rad))
            if 0 <= rr < 45 and 0 <= cc < W_IDX:
                fr.put(rr, cc, "·" if p < 0.6 else "▪",
                       fg=P.mix(C_GOLD, C_VOID, 0.35 + 0.45 * p), bg=None)
    # appear
    app = fx.smoothstep(lt, 3.75, 4.35)
    grey = fx.smoothstep(lt, 5.55, 6.35)
    fall = fx.smoothstep(lt, 6.55, 7.90)
    if app <= 0.01:
        return
    pulse = float(ctx.pulse)
    gold = P.mix(C_GOLD, C_WHITE, 0.20 + 0.25 * pulse)
    dimc = P.mix(C_DIM, C_WHITE, 0.10)
    base = P.mix(C_GOLD, C_RED, 0.30 * grey)
    core = P.mix(gold, dimc, grey)
    edge = P.mix(P.mix(C_GOLD, C_AMBER, 0.4), dimc, grey)
    if fall < 0.02:
        # solid / grey heart from the art mask
        r = r0
        c = c0
        if app < 0.99:                                   # scanline build
            r = r0 + int(round((1.0 - app) * 4))
            fr.paint_mask(_hm, c, r, _HW, _HH, ramp=P.RAMP_BLOCK,
                          fg=edge, fg2=core, alpha=min(1.0, app * 1.1))
        else:
            fr.paint_mask(_hm, c, r, _HW, _HH, ramp=P.RAMP_BLOCK,
                          fg=edge, fg2=core)
        # scan brackets around the heart
        if lt < 6.2:
            bc = _beam_heart(lt)
            br = int(round(r0 + (1.0 - app) * 4 + bc))
            for cc in range(c0 - 2, c0 + _HW + 2, 2):
                if 0 <= br < 45:
                    fr.put(br, cc, "·", fg=P.mix(C_GOLD, C_VOID, 0.55), bg=None)
        # dimension ticks / corner brackets
        if app > 0.6:
            for (rr, cc) in ((r0 - 1, c0 - 1), (r0 - 1, c0 + _HW),
                             (r0 + _HH + 2, c0 - 1), (r0 + _HH + 2, c0 + _HW)):
                if 0 <= rr < 45:
                    fr.put(rr, cc, "┼", fg=P.mix(C_GOLD, C_VOID, 0.62), bg=None)
            fr.write(r0 - 1, c0 + 2, "LV // AORTA // MESH",
                     fg=P.mix(C_GOLD, C_VOID, 0.55), bg=None)
        # cardiac monitor strip below the heart
        er = 35
        ci = np.arange(24, 168)
        tt = t - (ci - 96) / 62.0
        ph = ((tt - 0.19) * (130.0 / 60.0)) % 1.0
        amp = (np.exp(-((ph - 0.020) / 0.010) ** 2) * 4.4
               - np.exp(-((ph - 0.072) / 0.014) ** 2) * 1.6
               + np.exp(-((ph - 0.210) / 0.035) ** 2) * 1.9
               + np.exp(-((ph - 0.885) / 0.028) ** 2) * 0.7)
        amp = amp * (1.0 - 0.55 * grey) * (1.0 + 0.22 * pulse)
        rs = np.rint(er - amp).astype(np.int32)
        cols = ci.astype(np.int32)
        live = (rs >= 2) & (rs < 45)
        fr.fill_rect(er, 24, er, 167, "─", fg=P.mix(C_GRID, C_VOID, 0.30))
        _plot(fr, rs[live], cols[live], I_H,
              P.mix(P.mix(C_GOLD, C_RED, grey), C_WHITE, 0.18))
        fr.write(37, 24, "ECG // LEAD II",
                 fg=P.mix(C_GOLD, C_VOID, 0.62), bg=None)
        risk = int(round(100 * grey))
        fr.write(37, 135, f"FLATLINE RISK {risk:3d}%",
                 fg=P.mix(C_RED if risk > 50 else C_GOLD, C_VOID, 0.35),
                 bg=None)
        # beat halo
        if pulse > 0.45 and grey < 0.8:
            for k in range(2):
                rad = 2.0 + 3.0 * k + 5.0 * (1.0 - pulse)
                th = np.linspace(0, 2 * math.pi, 24)
                rr = np.rint(9 + _HH / 2 + np.sin(th) * rad).astype(np.int32)
                cc = np.rint(96 + np.cos(th) * rad * 1.9).astype(np.int32)
                _plot(fr, rr, cc, I_DOT,
                      P.mix(C_GOLD, C_VOID, 0.45 + 0.2 * k))
        fr.write(r0 + _HH + 1, 96 - 12, "HEART // 100%",
                 fg=P.mix(C_GOLD, C_VOID, 0.25), bg=None)
        # cracks
        ck = fx.smoothstep(lt, 6.00, 6.70)
        if ck > 0.02:
            for k, pts in enumerate(_CRACKS):
                n = int(len(pts) * min(1.0, ck * 1.2 + 0.05))
                rs = np.array([p[0] for p in pts[:n]], np.int32) + r0
                cs = np.array([p[1] for p in pts[:n]], np.int32) + c0
                ch = np.array([I_V if abs(p[0] - pts[0][0]) > abs(p[1] - pts[0][1])
                               else I_H for p in pts[:n]], np.int16)
                _plot(fr, rs, cs, ch, P.mix(C_RED, C_WHITE, 0.45))
    else:
        # the heart breaks into falling pieces
        prog = fx.clamp((fall - 0.02) * 1.35)
        rr = _heart_rows + r0
        cc = _heart_cols + c0
        delay = (HEART[_heart_rows, _heart_cols] * 0.4 +
                 (_heart_cols / _HW) * 0.35)
        fallen = prog * (5.0 + 20.0 * delay)
        newr = np.rint(rr + fallen).astype(np.int32)
        fade = np.clip(1.0 - (fallen / 26.0), 0.0, 1.0)
        idx = HEART_IDX
        basec = np.asarray(P.mix(C_DIM, C_RED, 0.45), np.float32)
        colarr = (basec[None, :] * (0.25 + 0.75 * fade)[:, None]).astype(np.uint8)
        rs_all = newr
        cs_all = cc
        ch_all = HEART_CH[idx]
        _plot(fr, rs_all, cs_all, ch_all, colarr)
        # sparks / dust
        _plot(fr, newr[::23], cs_all[::23], I_SPARK,
              P.mix(C_RED, C_WHITE, 0.4))


def _illegal(fr, ctx, t):
    lt = t - T_S
    if lt < 7.30:
        return
    wins = _ERR_WINS
    count = 0
    rng = np.random.default_rng(ctx.fi * 613 + 29)
    for k, (delay, r0, c0, w, h, title, lines) in enumerate(wins):
        ap = lt - (7.42 + delay)
        if ap < 0:
            break
        count += 1
        grow = fx.smoothstep(ap, 0.0, 0.13)
        sw = max(2, int(w * grow))
        sh = max(1, int(h * grow))
        bg = C_PANEL2 if k % 3 else P.mix(C_PANEL, C_RED, 0.10)
        fr.fill_rect(r0, c0, r0 + sh, c0 + sw, " ", bg=bg)
        fr.box(r0, c0, r0 + sh, c0 + sw, 1, fg=P.mix(C_RED, C_WHITE, 0.15),
               bg=bg, title=_scramble(title, k, ctx.fi, 1.0 if ap < 0.05 else 0.0))
        for j, ln in enumerate(lines):
            if j >= sh - 2:
                break
            txt = ln if ap > 0.10 else _scramble(ln, k * 7 + j, ctx.fi, 0.85)
            fr.write(r0 + 1 + j, c0 + 2, txt[:sw - 3],
                     fg=P.mix(C_RED if j == 0 else C_AMBER, C_VOID, 0.0))
        if ap < 0.16:
            for rr in range(r0, r0 + sh + 1):
                _plot(fr, (rr,), (c0 + int(rng.integers(0, sw + 1)),),
                      I_BLOCK, P.mix(C_RED, C_WHITE, 0.25))
    # stacked counter / storm
    if count:
        fr.write(1, 60, f"!! EXCEPTIONS {count:02d}  ARGUMENT 1: YOUR GOD",
                 fg=P.mix(C_RED, C_WHITE, 0.15 + 0.20 * ctx.pulse))
    # falling exception trace lines
    tr = ("Traceback (most recent call last):   File \"world.execute(me)\", "
          "line 0xDEAD, in god()   TypeError: illegal argument #1   "
          "AssertionError: you are not a god   ")
    W.marquee(fr, 39, tr, ctx.t, speed=34.0, fg=P.mix(C_RED, C_VOID, 0.05),
              bg=C_VOID2)


_ERR_WINS = (
    (0.0, 3, 118, 34, 5, "!! ILLEGAL ARGUMENT",
     ["TypeError: god() takes", "no arguments", "at 0xDEAD:1"]),
    (0.18, 3, 62, 30, 5, "!! ARGUMENT 1",
     ["expected: YOUR GOD", "got: a terminal", "RETURN 0"]),
    (0.36, 9, 20, 30, 5, "!! SEGFAULT",
     ["faith.exe crashed", "core dumped", "regret 100%"]),
    (0.54, 9, 140, 32, 5, "!! INDEX ERROR",
     ["argument out of", "range: love[0]", "→ nothing"]),
    (0.72, 15, 96, 36, 5, "✗ ASSERTION FAILED",
     ["you have made some", "illegal arguments", "EXCEPTION"]),
    (0.90, 21, 34, 34, 5, "!! ILLEGAL ARGUMENT",
     ["challenging your God", "is not allowed", "line 0xDEAD"]),
    (1.06, 21, 132, 32, 5, "!! TYPE ERROR",
     ["expected: HUMAN", "got: MACHINE", "context invalid"]),
    (1.22, 28, 64, 40, 5, "!! ILLEGAL ARGUMENT",
     ["Traceback: faith()", "TypeError: illegal", "argument #1"]),
    (1.38, 28, 128, 30, 4, "!! KERNEL PANIC",
     ["not enough love", "to continue"]),
    (1.54, 34, 16, 36, 4, "✗ EXCEPTION UNCAUGHT",
     ["god is not defined", "at 0xDEAD:1"]),
)


# ------------------------------------------------------------------- widgets --
def _hud(fr, ctx, t):
    lt = t - T_S
    fr.fill_rect(0, 0, 1, W_IDX - 1, " ", bg=C_VOID2)
    if lt < 3.8:
        phase = "MEMORY SCAN // FRAGMENT ERASURE"
        col = C_VIOLET
    elif lt < 7.4:
        phase = "CORE MONITOR // CARDIAC MESH"
        col = C_GOLD
    else:
        phase = "ERROR LOG // ILLEGAL ARGUMENTS"
        col = C_RED
    fr.write(0, 1, "MEMORY CORE // v2.1", fg=P.mix(col, C_VOID, 0.20))
    fr.ctext(0, phase, fg=P.mix(col, C_VOID, 0.05))
    fr.rtext(0, f"T+{lt:05.2f}  FRM {int(t * 30):05d}",
             fg=P.mix(C_DIM, C_VOID, 0.15))
    erased = sum(1 for f in _FR if lt > _erase_t(f) + 1.15)
    if lt < 3.8:
        fr.write(1, 1, f"FRAGMENTS {N_FR - erased:02d}/{N_FR:02d}   "
                       f"ERASED {erased:02d}   SECTOR {int(_beam_col(lt)):03d}",
                 fg=P.mix(C_VIOLET, C_VOID, 0.10))
    elif lt < 7.4:
        integ = max(0.0, 100.0 * (1.0 - fx.smoothstep(lt, 5.8, 7.2)))
        fr.write(1, 1, f"CARDIAC MESH INTEGRITY {integ:5.1f}%   "
                       f"CRACKS {int(fx.clamp((lt - 5.9) / 0.18)):02d}   "
                       f"STATUS {'GREY' if lt > 6.0 else 'GOLD'}",
                 fg=P.mix(C_GOLD if lt < 6.1 else C_DIM, C_VOID, 0.10))
    else:
        n = max(0, int((lt - 7.42) / 0.16))
        fr.write(1, 1, f"EXCEPTIONS {min(10, n):02d}   ARGUMENTS ILLEGAL   "
                       f"GOD.EXE NOT RESPONDING",
                 fg=P.mix(C_RED, C_VOID, 0.05 + 0.10 * ctx.pulse))
    # bottom strip
    fr.hline(40, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.30))
    if lt < 3.8:
        frac = erased / N_FR
        fr.write(41, 1, "ERASE PROGRESS", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
        W.progress_bar(fr, 41, 16, 60, frac, fg=P.mix(C_VIOLET, C_TEAL, 0.4),
                       bg=C_VOID2, show_pct=True)
        fr.write(41, 88, f"FRAGMENTS LEFT {N_FR - erased:02d}", bg=C_VOID2,
                 fg=P.mix(C_VIOLET, C_VOID, 0.10))
        fr.write(42, 1, "MEMORY BANK 0x00FF // ERASE ALL THE POINTLESS FRAGMENTS",
                 fg=P.mix(C_DIM, C_VOID, 0.10), bg=C_VOID2)
    elif lt < 7.4:
        integ = max(0.0, 1.0 - fx.smoothstep(lt, 5.8, 7.2))
        fr.write(41, 1, "HEART INTEGRITY", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
        W.progress_bar(fr, 41, 17, 60, integ,
                       fg=P.mix(C_GOLD, C_VOID, 0.20), bg=C_VOID2, show_pct=True)
        fr.write(41, 88, "CORE TEMP 41C   GREY MATTER RISING", bg=C_VOID2,
                 fg=P.mix(C_DIM, C_VOID, 0.10))
        fr.write(42, 1, "PLEASE DO NOT LEAVE ME SO DISHEARTENED", bg=C_VOID2,
                 fg=P.mix(C_GOLD, C_VOID, 0.10))
    else:
        fr.write(41, 1, "EXCEPTION STACK", fg=P.mix(C_RED, C_VOID, 0.10), bg=C_VOID2)
        fr.write(41, 18, "at god() line 0xDEAD // TypeError: illegal argument #1"
                         " // fatal: no god defined", fg=P.mix(C_RED, C_VOID, 0.10),
                 bg=C_VOID2)
        fr.fill_rect(42, 1, 42, W_IDX - 2, " ",
                     bg=P.mix(C_RED, C_VOID, 0.90))
        fr.write(42, 1, "  ███████  KERNEL PANIC  ███████  ILLEGAL ARGUMENTS  "
                       "CHALLENGING YOUR GOD  ILLEGAL ARGUMENTS  ███████",
                 fg=P.mix(C_WHITE, C_RED, 0.20))


# --------------------------------------------------------------------- draw ---
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    lt = t - T_S
    p = fx.clamp(lt / DUR)
    _bg(fr, ctx)
    if lt >= 3.7:
        _heart_draw(fr, ctx, t)
    _big_words(fr, ctx, t)
    if lt < 4.0:
        _fragments(fr, ctx, t)
    _illegal(fr, ctx, t)
    _hud(fr, ctx, t)
    # red flash on each new exception window
    fl = 0.0
    for k, (delay, r0, c0, w, h, title, lines) in enumerate(_ERR_WINS):
        ap = lt - (7.42 + delay)
        if 0.0 <= ap < 0.10:
            fl = max(fl, 0.08)
    if lt < 0.10:
        fl = max(fl, 0.10)
    ctx.meta["flash"] = fl
    ctx.meta["flash_color"] = C_RED if lt > 7.3 else C_WHITE
    ctx.meta["bloom"] = 0.30 + 0.30 * ctx.pulse + 0.15 * fx.smoothstep(lt, 7.3, 9.5)
    st = fx.smoothstep(lt, 7.3, 10.6)
    if st > 0.01:
        ctx.shake(1.6 * st, 2000 + int(t * 5))
    return fr
