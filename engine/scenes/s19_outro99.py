"""s19_outro99 - the completion routine that never completes.

192.190 - 203.720 (outro, 25 beats)

The giant progress bar is the subject of the frame: it crawls to 99.9%,
then the "Execution" push fails and the counter snaps back to 99.0%.
Three pushes (192.190 / 195.882 / 199.575), three retries, then one last
overdrive push that runs straight into the final EXECUTION.
"""
from __future__ import annotations

import math

import numpy as np

from .. import font as F
from .. import fx
from .. import palette as P
from .. import timeline as TL

ROWS, COLS = 45, 192

PANEL = P.C["panel"]
PANEL2 = P.C["panel2"]
VOID = P.C["void"]
LINE = P.C["line"]
DIM = P.C["dim"]
MID = P.C["mid"]
FG = P.C["fg"]
WHITE = P.C["white"]
PRIMARY = P.C["primary"]
TEAL = P.C["teal"]
GOLD = P.C["gold"]
AMBER = P.C["amber"]
RED = P.C["red"]
CRIMSON = P.C["crimson"]
BLOOD = P.C["blood"]

PUSH_T = (192.190, 195.882, 199.575)   # "Execution, execution" lyric pushes
LAST_PUSH = 203.267                    # last "Execution" line
CUT = 203.720                          # s20 takes over
CYCLE = 3.6923
FAIL_U = 3.28                          # failure inside each push cycle
BASE = 0.9900
SPAN = 0.0095

_BLK = F.char_index("█")
_DIMC = F.char_index("░")
_PART = [F.char_index(ch) for ch in " ▏▎▍▌▋▊▉█"]
_H = F.char_index("─")
_TICK = F.char_index("┴")
_BARW = 188


# ------------------------------------------------------------------ state --
def _state(t):
    """Return (frac, fail_env, retries, final, current_push)."""
    if t < LAST_PUSH:
        p = PUSH_T[0]
        for pt in PUSH_T:
            if pt <= t:
                p = pt
        u = t - p
        creep = fx.ease_inout(min(u, FAIL_U) / FAIL_U)
        if u < FAIL_U:
            frac = BASE + SPAN * creep
        else:
            rev = fx.smoothstep(u, FAIL_U, FAIL_U + 0.20)
            frac = BASE + SPAN * (1.0 - rev)
        fail = 0.0
        for pt in PUSH_T:
            dt = t - (pt + FAIL_U)
            if dt >= 0.0:
                fail = max(fail, math.exp(-dt * 6.2))
        retries = sum(1 for pt in PUSH_T if t >= pt + FAIL_U)
        frac += (0.00022 * math.sin(t * 11.3) + 0.00010 * math.sin(t * 27.7)) * (1.0 - fail)
        return frac, fail, retries, False, p

    v = fx.clamp((t - LAST_PUSH) / (CUT - LAST_PUSH))
    frac = BASE + SPAN * fx.ease_in(v)
    frac += 0.00030 * max(0.0, math.sin(t * 21.0) - 0.82) + 0.00022 * max(0.0, math.sin(t * 37.0) - 0.9)
    frac = min(frac, 0.99996)
    return frac, 0.0, 3, True, LAST_PUSH


def _eta(frac, fail, final, t):
    if final:
        return "00:00" if math.sin(t * 17.0) > -0.1 else "--:--"
    if fail > 0.30:
        return "--:--"
    if frac > 0.9986:
        return "00:00"
    if frac > 0.9962:
        return "00:01"
    return "--:--"


# --------------------------------------------------------------- helpers ---
def _panel(fr, r0, c0, r1, c1, title, fg, bg=PANEL, style=1):
    fr.fill_rect(r0, c0, r1, c1, " ", fg=fg, bg=bg)
    fr.box(r0, c0, r1, c1, style=style, fg=fg, bg=bg)
    if title:
        fr.write(r0, c0 + 3, f" {title} ", fg=fg, bg=bg)


def _mini_bar(fr, r, c, w, frac, fg, bg=PANEL, empty=None):
    empty = empty if empty is not None else P.mix(bg, LINE, 0.75)
    n = max(0, min(w, int(round(fx.clamp(frac) * w))))
    fr.put(r, c - 1, "▕", fg=empty, bg=bg)
    fr.put(r, c + w, "▏", fg=empty, bg=bg)
    if n:
        fr.ch[r, c:c + n] = _BLK
        fr.fg[r, c:c + n] = np.asarray(fg, np.uint8)
    if n < w:
        fr.ch[r, c + n:c + w] = _DIMC
        fr.fg[r, c + n:c + w] = np.asarray(empty, np.uint8)
    fr.bg[r, c - 1:c + w + 1] = np.asarray(bg, np.uint8)


def _bar_cells(fr, r0, r1, c0, c1, frac, *, base, hot, t, pulse,
               fail, fail_pos=0.0, bg=None, separators=0):
    """Numpy-painted solid progress bar (columns carry the pattern)."""
    h = r1 - r0 + 1
    w = c1 - c0 + 1
    xx = np.arange(w, dtype=np.float32)
    filled = fx.clamp(frac) * w
    n = int(filled)
    part = filled - n
    chars = np.full(w, _DIMC, np.int16)
    if n > 0:
        chars[:n] = _BLK
    if part >= 0.04 and n < w:
        chars[n] = _PART[min(8, int(round(part * 8.0)))]

    u = xx / float(max(1, w - 1))
    scanpos = (t * 0.52) % 1.0
    scan = np.exp(-((u - scanpos) ** 2) / 0.013)
    flick = 0.94 + 0.06 * np.sin(xx * 0.51 - t * 8.4)
    heat = np.clip((0.72 + 0.55 * scan) * flick, 0.0, 1.35)
    if n < w:
        heat = heat + 1.2 * np.exp(-((xx - filled) ** 2) / 2.4)

    base = np.asarray(base, np.float32).reshape(3)
    base_l = base * 0.70 + np.asarray(VOID, np.float32) * 0.30
    base_r = base * 0.78 + np.asarray(WHITE, np.float32) * 0.22
    grad = np.clip(u, 0.0, 1.0)[:, None]
    basecol = np.asarray(base_l, np.float32)[None, :] * (1.0 - grad) \
        + base_r[None, :] * grad                                          # (w,3)

    yy = np.arange(h, dtype=np.float32)
    rowmul = (0.86 + 0.18 * np.sin(np.pi * (yy + 0.5) / h))[:, None]     # (h,1)
    rgb = basecol[None, :, :] * (heat[None, :, None] * rowmul[:, :, None])

    hot = np.asarray(hot, np.float32)
    hot_amt = np.clip(scan[None, :] * rowmul * 0.30, 0.0, 0.34)[:, :, None]
    rgb = rgb * (1.0 - hot_amt) + hot[None, None, :] * hot_amt

    if separators:
        groove = (np.mod(xx, w / separators) < 0.55)[None, :, None]
        rgb = np.where(groove, rgb * 0.55, rgb)

    if n < w:
        g = 0.55 + 0.45 * pulse
        rgb[:, n:, :] = np.asarray(P.mix(BLOOD, RED, 0.55), np.float32)[None, None, :] * g

    if fail > 0.02:
        wv = np.exp(-((u - fail_pos) ** 2) / 0.0035) * fail
        red = np.asarray(CRIMSON, np.float32)
        rgb = rgb * (1.0 - 0.70 * wv[None, :, None]) + red[None, None, :] * (1.05 * wv[None, :, None])

    fr.ch[r0:r1 + 1, c0:c1 + 1] = chars[None, :]
    fr.fg[r0:r1 + 1, c0:c1 + 1] = np.clip(rgb, 0, 255).astype(np.uint8)
    if bg is not None:
        fr.bg[r0:r1 + 1, c0:c1 + 1] = np.asarray(bg, np.uint8)


# ------------------------------------------------------------------ draw ---
def draw(ctx):
    t = ctx.t
    fr = ctx.frame()
    frac, fail, retries, final, cur_push = _state(t)

    _background(fr, ctx)
    _top_strip(fr, ctx, frac, fail, retries, final)
    _big_percent(fr, ctx, frac, fail, final)
    _attempt_panel(fr, ctx, frac, fail, retries, t)
    _heart_panel(fr, ctx, fail, final)
    _sub_labels(fr, ctx, frac, fail, final)
    _giant_bar(fr, ctx, frac, fail, retries, cur_push)
    _bar_scale(fr, ctx, frac, fail)
    _zoom_bar(fr, ctx, frac, fail, cur_push)
    _workers(fr, ctx, frac, fail)
    _stack_panel(fr, ctx, fail)
    _system_log(fr, ctx, frac, fail, retries, final)
    _task_queue(fr, ctx, frac, fail)
    _counters(fr, ctx, frac, fail, retries, final)
    _bottom(fr, ctx, frac, fail, final)
    _effects(ctx, t, frac, fail, final)
    return fr


# ------------------------------------------------------------- background --
def _background(fr, ctx):
    t = ctx.t
    dimline = P.mix(VOID, LINE, 0.55)
    for r, dash_phase in ((1, 0), (28, 3), (42, 7)):
        fr.ch[r, :] = _H
        col = np.tile(np.asarray(dimline, np.float32), (COLS, 1))
        sel = (np.arange(COLS) + dash_phase) % 6 < 4
        col[~sel] *= 0.22
        fr.fg[r, :] = np.clip(col, 0, 255).astype(np.uint8)

    sy = int((t * 12.0) % (ROWS + 10)) - 5
    if 0 <= sy < ROWS:
        fr.fg[sy] = np.clip(fr.fg[sy].astype(np.float32) * 1.16 + 5.0, 0, 255).astype(np.uint8)

    br = P.mix(VOID, LINE, 0.9)
    for (r, c, ch, dr, dc) in ((0, 0, "┌", 1, 1), (0, COLS - 1, "┐", 1, -1),
                               (ROWS - 1, 0, "└", -1, 1), (ROWS - 1, COLS - 1, "┘", -1, -1)):
        fr.put(r, c, ch, fg=br)
        for k in range(1, 5):
            fr.put(r + dr * k, c, "│", fg=br)
            fr.put(r, c + dc * k, "─", fg=br)


# -------------------------------------------------------------- top strip --
def _top_strip(fr, ctx, frac, fail, retries, final):
    t = ctx.t
    fr.fill_rect(0, 0, 0, COLS - 1, " ", fg=FG, bg=PANEL)
    fr.write(0, 2, "■ COMPLETION MONITOR", fg=PRIMARY)
    fr.write(0, 24, "PID 0x00E99", fg=DIM)
    fr.write(0, 38, "PARENT: WORLD.SIMULATE(1)", fg=DIM)
    state = "WAITING_FOR_PROCESS_EXIT"
    sc = PRIMARY
    if final:
        state = "EXECUTION_ACCEPTED" if math.sin(t * 9.0) > 0 else "TERMINATING_PROCESS"
        sc = CRIMSON if math.sin(t * 9.0) > 0 else GOLD
    elif fail > 0.12:
        state = "EXECUTION_REVERTED"
        sc = RED
    fr.write(0, 68, f"STATE: {state}", fg=sc)
    if math.sin(t * 4.6) > -0.2:
        fr.write(0, 110, "◉ SYS", fg=TEAL)
    ecol = RED if fail > 0.3 else (AMBER if frac > 0.996 else MID)
    fr.write(0, 121, f"RETRY 0x{retries:02X}", fg=(RED if fail > 0.3 else GOLD))
    eta = _eta(frac, fail, final, t)
    fr.write(0, 134, f"ETA {eta}", fg=ecol)
    fr.write(0, 145, "TGT 100.000000", fg=DIM)
    fr.rtext(0, f"PUSH {min(retries + 1, 4):02d}/04", fg=WHITE)


# ------------------------------------------------------------ big percent --
def _big_percent(fr, ctx, frac, fail, final):
    t = ctx.t
    pct = min(99.9999, frac * 100.0)
    txt = f"{pct:5.2f}%"                       # 6 cells
    if fail > 0.28:
        fh = int(t * 30)
        glyphs = "#*&%$@=+"
        chars = list(txt)
        for i in range(1 + int(fx.hash01(fh, 3) * 2)):
            j = int(fx.hash01(fh, i * 7 + 1) * (len(chars) - 1))
            chars[j] = glyphs[int(fx.hash01(fh, i * 13 + 5) * len(glyphs))]
        txt = "".join(chars)
    fg, fg2 = GOLD, WHITE
    if fail > 0.12:
        fg, fg2 = RED, GOLD
    elif frac > 0.9987:
        fg, fg2 = AMBER, WHITE
    if final:
        v = fx.clamp((t - LAST_PUSH) / (CUT - LAST_PUSH))
        sh = 0.5 + 0.5 * math.sin(t * 40.0)
        fg = P.mix(WHITE, CRIMSON, 0.30 + 0.55 * sh * v)
        fg2 = WHITE
    # engraved readout: RAMP_HI (10 levels) keeps big strokes clean, not speckled
    fr.paint_text(txt, 2, 96, 8, fg=fg, fg2=fg2, align="center", ramp=P.RAMP_HI)


# --------------------------------------------------------- attempt panel --
def _attempt_panel(fr, ctx, frac, fail, retries, t):
    r0, c0, r1, c1 = 2, 1, 9, 55
    fg = RED if fail > 0.25 else PRIMARY
    _panel(fr, r0, c0, r1, c1, "ATTEMPT LOG", fg)
    fr.write(r0 + 1, c0 + 2, "seq target            result", fg=P.mix(PANEL, MID, 0.55))
    vals = ("99.912844", "99.961002", "99.995310")
    ev = []
    for i, p in enumerate(PUSH_T):
        ev.append((p, f"{i + 1:02d}  100.000000  → {vals[i]}", FG))
        ev.append((p + FAIL_U, f"{i + 1:02d}  ERR 0x5F TERMINATION_UNREACHABLE", RED))
    ev = [e for e in ev if e[0] <= t]
    if len(ev) > 5:
        ev = ev[-5:]
    for i, (et, txt, col) in enumerate(ev):
        fr.write(r0 + 2 + i, c0 + 2, txt[:50], fg=col)
    r = r0 + 2 + len(ev)
    if r <= r1 - 1 and math.sin(t * 8.0) > 0:
        fr.write(r, c0 + 2, f"{retries + 1:02d}  retry queued", fg=GOLD)
        fr.put(r, c0 + 20, "█", fg=WHITE)


# ----------------------------------------------------------- heart panel ---
def _heart_panel(fr, ctx, fail, final):
    t = ctx.t
    r0, c0, r1, c1 = 2, 136, 9, 190
    _panel(fr, r0, c0, r1, c1, "HEARTBEAT // SYNTH", P.mix(PRIMARY, RED, 0.45 * fail))
    fr.write(r0 + 1, c0 + 2, "SIGNAL", fg=DIM)
    fr.write(r0 + 1, c0 + 32, "CH 0x0E", fg=DIM)
    dim = P.mix(PANEL, MID, 0.55)
    mid = r0 + 4
    for c in range(c0 + 2, c1 - 1):
        fr.put(mid, c, "·", fg=dim)
    period = 1.55
    for k in range(2):
        ph = ((t / period) + k * 0.5) % 1.0
        bc = (c0 + 2) + int((1.0 - ph) * (c1 - c0 - 6))
        if bc <= c0 + 1 or bc >= c1 - 2:
            continue
        col = P.mix(PRIMARY, TEAL, 0.35)
        amp = 1 if ph > 0.74 else 2
        if amp == 2:
            fr.put(mid - 2, bc, "▲", fg=col)
            fr.put(mid - 1, bc, "│", fg=col)
            fr.put(mid, bc, "╱", fg=col)
            fr.put(mid, bc + 1, "╲", fg=col)
            fr.put(mid - 1, bc + 1, "│", fg=col)
        else:
            fr.put(mid - 1, bc, "╱", fg=col)
            fr.put(mid, bc, "·", fg=col)
    bpm = "--" if not final else f"{90 + int(40 * abs(math.sin(t * 3.0)))}"
    fr.write(r0 + 5, c0 + 2, f"BPM {bpm:>3}   RATE 0.00   WDT 0x0000", fg=P.mix(DIM, RED, fail))
    stall = "STALLED" if (fail > 0.05 or not final) else "RECOVERING"
    if math.sin(t * 6.0) > -0.3 or fail > 0.2:
        fr.write(r0 + 6, c0 + 2, f"STATE {stall}", fg=RED if fail > 0.05 else DIM)
        fr.write(r0 + 6, c0 + 24, "FLATLINE", fg=P.mix(PANEL, RED, 0.7))


# ------------------------------------------------------------ sub labels ---
def _sub_labels(fr, ctx, frac, fail, final):
    delta = -(1.0 - frac) * 100.0
    txt = f"TARGET 100.000000   DELTA {delta:+.6f}   PENDING 1 = THE.LOOP"
    col = P.mix(MID, RED, fail)
    if final:
        col = P.mix(GOLD, CRIMSON, 0.5 + 0.5 * math.sin(ctx.t * 30.0))
    fr.ctext(10, txt, fg=col)


# -------------------------------------------------------------- giant bar --
def _giant_bar(fr, ctx, frac, fail, retries, cur_push):
    t = ctx.t
    golden = fx.smoothstep(frac, 0.988, 0.9995)
    edge = P.mix(LINE, GOLD, 0.25 + 0.60 * golden)
    if fail > 0.18:
        edge = P.mix(edge, RED, 0.7)
    bg = VOID
    fr.box(11, 1, 21, 190, 2, fg=edge, bg=PANEL)
    fr.fill_rect(12, 2, 20, 189, " ", fg=DIM, bg=bg)
    fr.write(11, 4, " COMPLETION ", fg=P.mix(GOLD, WHITE, 0.30 * golden), bg=PANEL)
    if fail > 0.15:
        msg = f" ▸ REVERTED · COUNTER {frac * 100:8.4f}% · ATTEMPT {min(retries + 1, 4):02d} "
        fr.write(11, 70, msg[:70], fg=P.mix(RED, WHITE, 0.25), bg=PANEL)
    else:
        fr.write(11, 70, f" ▸ EXECUTING THE.LOOP · {frac * 100:8.4f}% ", fg=AMBER, bg=PANEL)
    fr.write(11, 172, " TGT 100.0 ", fg=DIM, bg=PANEL)
    fr.write(21, 4, " ── ", fg=DIM, bg=PANEL)
    fr.write(21, 178, " ── ", fg=DIM, bg=PANEL)

    warm = fx.clamp((frac - BASE) / SPAN)          # 0 at 99.0, 1 at 99.95
    base = P.mix(P.mix(VOID, PRIMARY, 0.90), P.mix(GOLD, AMBER, 0.35), warm)
    if fail > 0.05:
        base = P.mix(base, CRIMSON, 0.55 * min(1.0, fail * 1.4))
    fpos = 1.0
    if cur_push is not None and t >= cur_push + FAIL_U:
        fpos = 1.0 - 1.7 * fx.smoothstep(t, cur_push + FAIL_U, cur_push + FAIL_U + 0.45)
    _bar_cells(fr, 12, 20, 2, 189, frac, base=base, hot=WHITE,
               t=t, pulse=max(ctx.pulse, 0.30), fail=fail, fail_pos=fpos,
               bg=bg, separators=10)

    fc = 2 + int(frac * _BARW)
    blink = 0.5 + 0.5 * math.sin(t * 14.0)
    mcol = P.mix(WHITE, CRIMSON, 0.45 + 0.55 * math.sin(t * 14.0))
    fr.put(11, min(190, fc), "▼", fg=mcol, bg=PANEL)
    fr.put(21, min(190, fc), "▲", fg=mcol, bg=PANEL)

    if fail > 0.15:
        rng = ctx.rng(int(t * 40))
        for k in range(3):
            r = 12 + rng.randint(0, 9)
            c = 186 + rng.randint(0, 3)
            fr.put(r, min(189, c), "⚡", fg=P.mix(GOLD, WHITE, rng.random()))


def _bar_scale(fr, ctx, frac, fail):
    c0, c1 = 2, 189
    w = c1 - c0 + 1
    dim = P.mix(VOID, LINE, 0.95)
    ch = [_TICK if (k % 19) == 0 else _H for k in range(w)]
    fr.ch[22, c0:c1 + 1] = np.asarray(ch, np.int16)
    fr.fg[22, c0:c1 + 1] = np.asarray(dim, np.uint8)
    fr.write(22, 2, "0.000", fg=DIM)
    fc = c0 + int(frac * w)
    for k in range(1, 5):
        c = c0 + int(round(k * w / 5.0))
        lab = f"{k * 20}"
        if abs(c - fc) > 5:
            fr.write(22, c - 1, lab, fg=P.mix(PANEL, MID, 0.35))
    fr.rtext(22, "100.000 ", fg=RED if fail > 0.3 else MID)


# --------------------------------------------------------------- zoom bar --
def _zoom_bar(fr, ctx, frac, fail, cur_push):
    t = ctx.t
    zoom = fx.clamp((frac - 0.99) / 0.010)
    hot_edge = P.mix(LINE, GOLD, 0.55)
    if fail > 0.18:
        hot_edge = P.mix(hot_edge, RED, 0.6)
    fr.box(23, 1, 27, 190, 1, fg=hot_edge, bg=PANEL)
    fr.write(23, 4, " ZOOM ×100 · FINAL SEGMENT · 99.000000% → 100.000000% ",
             fg=P.mix(GOLD, AMBER, 0.25), bg=PANEL)
    fr.write(23, 150, f" GAP {100.0 - frac * 100.0:.6f}% ", fg=RED, bg=PANEL)
    bg = VOID
    fr.fill_rect(24, 2, 26, 189, " ", fg=DIM, bg=bg)
    base_l = P.mix(VOID, RED, 0.60)
    base_r = P.mix(GOLD, AMBER, 0.20 + 0.50 * zoom)
    base = P.mix(base_l, base_r, 0.35 + 0.65 * zoom)
    fpos = 1.0
    if cur_push is not None and t >= cur_push + FAIL_U:
        fpos = 1.0 - 1.7 * fx.smoothstep(t, cur_push + FAIL_U, cur_push + FAIL_U + 0.40)
    _bar_cells(fr, 24, 26, 2, 189, zoom, base=base, hot=WHITE,
               t=t, pulse=ctx.pulse, fail=fail, fail_pos=fpos, bg=bg, separators=5)
    for k in range(11):
        c = 2 + int(round(k * 187 / 10.0))
        fr.put(27, c, "┴", fg=P.mix(DIM, GOLD, 0.3), bg=PANEL)
    fr.write(27, 2, " 99.000", fg=DIM, bg=PANEL)
    fr.rtext(27, " 100.000 ", fg=GOLD, bg=PANEL)


# ---------------------------------------------------------------- workers --
def _workers(fr, ctx, frac, fail):
    t = ctx.t
    r0, c0, r1, c1 = 29, 1, 34, 94
    _panel(fr, r0, c0, r1, c1, "EXECUTION WORKERS", P.mix(PRIMARY, RED, 0.4 * fail))
    vals = (0.9982, 0.99961, 0.9990, 0.9900)
    for i in range(4):
        r = r0 + 1 + i
        if i < 3:
            v = min(0.99999, vals[i] + 0.00006 * math.sin(t * (1.7 + i * 0.6)))
        else:
            v = 0.99000                        # the worker that never lands
        stalled = i == 3
        fr.write(r, c0 + 2, f"WKR 0{i + 1}", fg=P.mix(DIM, PRIMARY, 0.5))
        bc = c0 + 10
        bw = 60
        fg = RED if (stalled and fail > 0.1) else (GOLD if v > 0.999 else PRIMARY)
        _mini_bar(fr, r, bc, bw, v, fg)
        fr.write(r, bc + bw + 2, f"{v * 100:8.4f}%", fg=(RED if stalled else AMBER))
        if stalled and math.sin(t * 5.0) > 0:
            fr.write(r, c0 + 82, "STALL", fg=RED)


# ------------------------------------------------------------ stack panel --
def _stack_panel(fr, ctx, fail):
    r0, c0, r1, c1 = 29, 97, 34, 190
    _panel(fr, r0, c0, r1, c1, "STACK TRACE · 0x00E99", P.mix(PRIMARY, RED, 0.4 * fail))
    lines = (
        ("at loop.execute(me):0x00E99", FG),
        ("at world.simulate(cycle=1):0x1A4", MID),
        ("at __main__.terminate():0x55F", RED if fail > 0.2 else MID),
        ("› no exit condition found — control returned to loop", DIM),
    )
    for i, (txt, col) in enumerate(lines):
        fr.write(r0 + 1 + i, c0 + 2, txt[:90], fg=col)


# ------------------------------------------------------------- system log --
def _system_log(fr, ctx, frac, fail, retries, final):
    t = ctx.t
    r0, c0, r1, c1 = 35, 1, 41, 96
    _panel(fr, r0, c0, r1, c1, "SYSTEM LOG", P.mix(PRIMARY, RED, 0.35 * fail))
    ev = [
        (192.190, "push 01 · object=THE.LOOP · request=TERMINATE"),
        (195.470, "ERR 0x5F · termination signal swallowed by loop"),
        (195.882, "push 02 · object=THE.LOOP · request=TERMINATE"),
        (199.162, "ERR 0x5F · termination signal swallowed by loop"),
        (199.575, "push 03 · object=THE.LOOP · request=TERMINATE"),
        (202.855, "ERR 0x5F · counter reverted to 99.000000"),
        (203.267, "push 04 · FINAL · no retry queued"),
    ]
    rows = [e for e in ev if e[0] <= t]
    if len(rows) > 5:
        rows = rows[-5:]
    for i, (et, txt) in enumerate(rows):
        col = RED if "ERR" in txt else FG
        fr.write(r0 + 1 + i, c0 + 2, f"[{et:08.3f}]", fg=P.mix(DIM, col, 0.6))
        fr.write(r0 + 1 + i, c0 + 14, txt, fg=col)
    r = r0 + 1 + len(rows)
    if r <= r1 - 1:
        cur = "█" if math.sin(t * 9.0) > 0 else " "
        fr.write(r, c0 + 2, f"[{t:08.3f}]", fg=DIM)
        fr.write(r, c0 + 14, ">", fg=PRIMARY)
        fr.put(r, c0 + 16, cur, fg=WHITE)


# -------------------------------------------------------------- task queue --
def _task_queue(fr, ctx, frac, fail):
    t = ctx.t
    r0, c0, r1, c1 = 35, 99, 41, 148
    _panel(fr, r0, c0, r1, c1, "TASK QUEUE", P.mix(PRIMARY, RED, 0.35 * fail))
    tasks = (
        ("THE.LOOP", frac, "WAIT"),
        ("SERIALIZE.SELF", 1.0, "DONE"),
        ("CLOSE.SESSION", 1.0, "DONE"),
        ("WORLD.SIM(1)", 1.0, "DONE"),
    )
    for i, (name, v, st) in enumerate(tasks):
        r = r0 + 1 + i
        fr.write(r, c0 + 2, f"{i}", fg=DIM)
        fr.write(r, c0 + 4, name, fg=WHITE if i == 0 else MID)
        col = GOLD if i == 0 else P.mix(DIM, TEAL, 0.7)
        _mini_bar(fr, r, c0 + 19, 16, v, col)
        fr.write(r, c0 + 37, st, fg=RED if i == 0 else TEAL)
        if i == 0 and math.sin(t * 4.0) > 0:
            fr.write(r, c0 + 42, "◂", fg=GOLD)
    fr.write(r1 - 1, c0 + 2, "QUEUE 1 PENDING · 3 DONE · BLOCKED=YES",
             fg=P.mix(DIM, RED, 0.4 + 0.6 * fail))


# ---------------------------------------------------------------- counters --
def _counters(fr, ctx, frac, fail, retries, final):
    t = ctx.t
    r0, c0, r1, c1 = 35, 151, 41, 190
    _panel(fr, r0, c0, r1, c1, "COUNTERS", P.mix(PRIMARY, RED, 0.35 * fail))
    eta = _eta(frac, fail, final, t)
    rows = (
        ("RETRY", f"0x{retries:02X}", RED if fail > 0.3 else GOLD),
        ("ATTEMPT", f"0x{min(retries + 1, 4):02X}/04", FG),
        ("FAILED", f"0x{retries:02X}", RED),
        ("ELAPSED", "00:11.530", MID),
        ("ETA", eta, RED if fail > 0.3 else AMBER),
    )
    for i, (k, v, col) in enumerate(rows):
        r = r0 + 1 + i
        fr.write(r, c0 + 2, k, fg=DIM)
        fr.write(r, c0 + 10, v, fg=col)
    sp = int(3 + 5 * abs(math.sin(t * 1.3)))
    fr.write(r0 + 1, c0 + 26, "▕" + "█" * sp + "▏", fg=PRIMARY)
    if fail > 0.3 and math.sin(t * 12.0) > 0:
        fr.write(r0 + 1, c0 + 26, "◀◀◀", fg=RED)


# ----------------------------------------------------------------- bottom --
def _bottom(fr, ctx, frac, fail, final):
    t = ctx.t
    fr.fill_rect(43, 1, 43, 190, " ", fg=FG, bg=PANEL)
    lead = "◇" if math.sin(t * 3.0) > 0 else "◆"
    state = "MONITORING · NO EXIT CONDITION"
    if fail > 0.2:
        state = "THREAD 0x00E99 UNRESPONSIVE"
    if final:
        state = "FINAL PUSH IN FLIGHT"
    fr.write(43, 2, f"{lead} {state}", fg=(RED if fail > 0.2 else PRIMARY), bg=PANEL)
    fr.write(43, 48, f"QUEUE 4/4  RETRY 0x{sum(1 for p in PUSH_T if t >= p + FAIL_U):02X}",
             fg=DIM, bg=PANEL)
    fr.write(43, 90, "PID 0x00E99 · THREADS 4 · LOCKS 0", fg=DIM, bg=PANEL)
    if math.sin(t * 2.2) > -0.4:
        fr.write(43, 138, "PRESS CTRL+C TO FORCE EXIT", fg=P.mix(PANEL, RED, 0.55), bg=PANEL)
    fr.write(44, 1, ">", fg=PRIMARY)
    seg = "EXECUTE.THE.LOOP.·.OBJECTIVE=THE.LOOP.·.TARGET=100.000000.·."
    off = int(t * 22) % len(seg)
    line = (seg * 4)[off:off + 178]
    fr.write(44, 3, line, fg=P.mix(VOID, LINE, 1.0))
    if math.sin(t * 7.0) > 0:
        fr.write(44, 183, "█", fg=WHITE)


# --------------------------------------------------------------- effects ---
def _effects(ctx, t, frac, fail, final):
    g = 0.10 * ctx.pulse
    if fail > 0.02:
        g = max(g, 0.55 * fail)
        ctx.shake(2.6 * fail)
        ctx.meta["flash"] = max(ctx.meta.get("flash", 0.0), 0.18 * fail)
        ctx.meta["flash_color"] = RED
    if final:
        v = fx.clamp((t - LAST_PUSH) / (CUT - LAST_PUSH))
        g = max(g, 0.18 + 1.05 * v * v)
        ctx.shake(1.0 + 4.5 * v)
        ctx.meta["tint"] = (CRIMSON, 0.05 + 0.18 * v)
        if v > 0.55:
            flick = 0.5 + 0.5 * math.sin(t * 51.0)
            ctx.meta["flash"] = max(ctx.meta.get("flash", 0.0), 0.28 * v * flick)
            ctx.meta["flash_color"] = RED
    ctx.set_glitch(g)
