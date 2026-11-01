"""s11_heartbeat — "feel your vibrations" / "then I can finally be completion".

The ECG is the whole screen: a bold monitor trace across the full width, pulse
rings firing on the QRS, vibration waves collapsing onto it, live telemetry,
and from 107.272 a gold completion lock (COMPLETE, 100 %, full heart).

Cells are written in numpy batches where the shape is repetitive (trace,
waves, rings); this keeps the scene draw well under the frame budget.
"""
from __future__ import annotations

import math

import numpy as np

from .. import palette as P
from .. import fx
from .. import font as F
from .. import widgets as W
from ..assets import BEAT, T0 as BEAT0

T_START = 103.580
T_COMPLETE = 107.272
T_END = 110.964

W_IDX = 192
TRACE_R0 = 11
TRACE_H = 18                     # rows 11..28
MID_R = TRACE_R0 + TRACE_H // 2  # row 20
TRACE_SPAN = BEAT * 2.55         # ~1.18 s of history, ~75 cols per beat
STEP = TRACE_H / 2 - 0.9         # cells per unit of amplitude

C_VOID = P.C["void"]
C_PANEL = P.C["panel"]
C_GRID = P.C["grid"]
C_LINE = P.C["line"]
C_DIM = P.C["dim"]
C_MID = P.C["mid"]
C_PRIMARY = P.C["primary"]
C_TEAL = P.C["teal"]
C_GOLD = P.C["gold"]
C_WHITE = P.C["white"]

# pre-mixed static colours (palette.mix is comparatively slow, keep it out of loops)
BG_DOT = P.mix(C_GRID, C_VOID, 0.20)
BG_DOT2 = P.mix(C_GRID, C_VOID, 0.10)
GRID_DOT = P.mix(C_GRID, C_VOID, 0.42)
GRID_LINE = P.mix(C_LINE, C_VOID, 0.34)
RAIN_HEAD = P.mix(C_TEAL, C_VOID, 0.80)
RAIN_MID = P.mix(C_TEAL, C_VOID, 0.88)
RAIN_TAIL = P.mix(C_PRIMARY, C_VOID, 0.93)
DRIFT = P.mix(C_VOID, C_PANEL, 0.40)
BAND_LO = P.mix(P.C["blue"], C_VOID, 0.45)
EDGE_COL = P.mix(C_WHITE, C_VOID, 0.58)
MARKER = P.mix(C_WHITE, C_GOLD, 0.35)
SOFT = P.mix(C_LINE, C_VOID, 0.25)

WAVE_ROWS = (-12, -6, 6, 12)
WAVE_COLS = (C_PRIMARY, C_TEAL, C_PRIMARY, C_TEAL)

# glyph indices
I_DOT = F.char_index("·")
I_BLOCK = F.char_index("█")
I_HALF = F.char_index("▄")
I_RING = F.char_index("○")
I_BLANK = 0
I_RAIN = (F.char_index("░"), F.char_index("·"), F.char_index("."))


# ------------------------------------------------------------------ helpers --
def _panel(fr, r0, c0, r1, c1, title=None, fg=C_LINE, style=1):
    fr.fill_rect(r0, c0, r1, c1, " ", bg=C_PANEL)
    fr.box(r0, c0, r1, c1, style=style, fg=fg, bg=C_PANEL, title=title)


def _ghost_text(fr, text, r0, c0, h, fg, fg2=None, ghost=2, align="center",
                step=1, bg=None):
    for k in range(ghost, 0, -1):
        gc = P.mix(fg, C_VOID, 0.52 + 0.15 * k)
        fr.paint_text(text, r0 + k * step, c0 + k, h, fg=gc, align=align, bg=bg)
    return fr.paint_text(text, r0, c0, h, fg=fg, fg2=fg2, align=align, bg=bg)


def _plot(fr, rs, cs, ch_idx, fg, mask=None):
    """Batched cell write (frame-internal arrays, strict in-bounds)."""
    rs = np.asarray(rs, np.int32)
    cs = np.asarray(cs, np.int32)
    ok = (rs >= 0) & (rs < fr.rows) & (cs >= 0) & (cs < fr.cols)
    if mask is not None:
        ok &= mask
    if not ok.any():
        return
    rs = rs[ok]
    cs = cs[ok]
    if np.ndim(ch_idx) == 0:
        fr.ch[rs, cs] = int(ch_idx)
    else:
        fr.ch[rs, cs] = np.asarray(ch_idx, np.int16)[ok]
    fg = np.asarray(fg, np.uint8)
    if fg.ndim == 3:
        fr.fg[rs, cs] = fg[ok]
    else:
        fr.fg[rs, cs] = fg


def _ecg(ph):
    """P-QRS-T with R exactly on the audio beat (phase 0)."""
    v = 0.0
    v += 0.26 * math.exp(-((ph - 0.885) / 0.026) ** 2)      # P
    v -= 0.20 * math.exp(-((ph - 0.958) / 0.014) ** 2)      # Q
    v += 1.00 * math.exp(-((ph - 0.020) / 0.018) ** 2)      # R
    v -= 0.36 * math.exp(-((ph - 0.072) / 0.021) ** 2)      # S
    v += 0.46 * math.exp(-((ph - 0.215) / 0.048) ** 2)      # T
    v += 0.09 * math.exp(-((ph - 0.405) / 0.044) ** 2)      # U
    return v


def _phase(tt):
    return ((tt - BEAT0) / BEAT) % 1.0


def _at(tt):
    return _ecg(_phase(tt))


# --------------------------------------------------------------------- bg ----
def _bg(ctx, fr, p2):
    t = ctx.t
    # dotted graph paper
    for r in range(2, 45, 3):
        rr = np.full(48, r, np.int32)
        cc = np.arange(0, W_IDX, 4, dtype=np.int32)
        ok = ((rr + cc) % 12) == 0
        _plot(fr, rr, cc, I_DOT, BG_DOT, ok)
    # rain in the outer margins
    for c in list(range(0, 20)) + list(range(176, 192)):
        h = fx.hash01(11, c, 1)
        head = (t * (10 + h * 9) + fx.hash01(11, c, 2) * 80) % 62 - 8
        for k in range(8):
            r = int(head) - k
            if 0 <= r < 45:
                f = 1.0 - k / 8.0
                ch = I_RAIN[0] if f > 0.6 else I_RAIN[1]
                col = RAIN_HEAD if f > 0.6 else (RAIN_MID if f > 0.3 else RAIN_TAIL)
                _plot(fr, (r,), (c,), ch, col)
    # slow phosphor drift bands
    for k in range(3):
        rr = int((t * 11 + k * 15) % 45)
        fr.fill_rect(rr, 0, rr, W_IDX - 1, " ", bg=DRIFT)
    if p2 > 0.02:
        for k in range(1 + int(p2 * 3)):
            fr.hline(1 + k, 0, W_IDX - 1, "═", fg=P.mix(C_GOLD, C_VOID, 0.45))
    gl = 0.010 + 0.020 * float(ctx.rms) + 0.030 * float(ctx.pulse) ** 2
    if t >= T_COMPLETE:
        gl = 0.015 + 0.40 * (1.0 - fx.smoothstep(t, T_COMPLETE, T_COMPLETE + 0.22))
    ctx.set_glitch(gl)


# ------------------------------------------------------------------- scope ----
def _grid(fr, t, panel_style):
    for r in range(TRACE_R0, TRACE_R0 + TRACE_H + 1, 3):
        fr.fill_rect(r, 0, r, W_IDX - 1, "·", fg=GRID_DOT)
    for c in range(0, W_IDX, 8):
        rs = np.arange(TRACE_R0, TRACE_R0 + TRACE_H + 1, 3, dtype=np.int32)
        _plot(fr, rs, np.full(len(rs), c, np.int32), I_DOT, BG_DOT)
    k0 = int(math.floor((t - TRACE_SPAN - BEAT0) / BEAT)) - 1
    for k in range(k0, k0 + 8):
        bt = BEAT0 + k * BEAT
        if not (t - TRACE_SPAN <= bt <= t):
            continue
        c = int(round(W_IDX - 1 - (t - bt) / TRACE_SPAN * W_IDX))
        if 0 <= c < W_IDX:
            fr.vline(c, TRACE_R0, TRACE_R0 + TRACE_H, "│", fg=GRID_LINE)


def _waves(fr, ctx, p2):
    """Vibration sines closing in on the trace, then settling onto it."""
    lt = ctx.local
    t = ctx.t
    if p2 > 0.8:
        return
    low = ctx.assets.low_at(t)
    for k in range(4):
        conv = fx.smoothstep(lt, 0.08 + 0.38 * k, 1.95 + 0.48 * k)
        off = WAVE_ROWS[k] * (1.0 - 0.92 * conv)
        col = P.mix(WAVE_COLS[k], C_VOID, 0.26 + 0.44 * conv)
        if p2 > 0.05:
            col = P.mix(col, C_VOID, min(1.0, p2 * 1.60))
        freq = 0.046 + 0.018 * k + 0.026 * conv
        spd = 4.4 + 1.6 * k + 3.5 * ctx.pulse
        amp = (1.25 - 0.50 * conv) * (0.50 + 0.60 * low)
        ph = np.arange(W_IDX * 2, dtype=np.float32) * (freq * 0.5) + t * spd + k * 1.7
        vals = 0.5 + np.sin(ph) * amp
        W.braille_plot(fr, int(round(MID_R + off)) - 1, 0, W_IDX, 3, vals, fg=col)


def _pleth(fr, ctx, p2):
    """SpO2 pulse-wave, dim, under the ECG baseline."""
    t = ctx.t
    cols = np.arange(W_IDX, dtype=np.int32)
    rs = np.empty(W_IDX, np.int32)
    for i in range(W_IDX):
        tt = t - (W_IDX - 1 - i) / W_IDX * TRACE_SPAN
        p = _phase(tt)
        v = math.exp(-3.2 * p) + 0.30 * math.exp(-((p - 0.46) / 0.10) ** 2)
        rs[i] = 27 - int(round(v * 3.4 * (1.0 - 0.35 * p2)))
    fg = P.mix(P.C["blue"], C_VOID, 0.45) if p2 < 0.5 else P.mix(C_GOLD, C_VOID, 0.55)
    _plot(fr, rs, cols, I_DOT, fg)
    _plot(fr, rs + 1, cols, I_DOT, P.mix(fg, C_VOID, 0.55))


def _trace(fr, t, amp, fg, peak, p2):
    cols = np.arange(W_IDX, dtype=np.int32)
    vals = np.empty(W_IDX, np.float32)
    phs = np.empty(W_IDX, np.float32)
    for i in range(W_IDX):
        tt = t - (W_IDX - 1 - i) / W_IDX * TRACE_SPAN
        p = _phase(tt)
        phs[i] = p
        vals[i] = _ecg(p) * amp
    rows = np.round(vals * STEP).astype(np.int32)
    # CRT after-image: one time-lagged ghost a row below
    glag, gdy, gmix = 0.026, 2, 0.66
    grow = np.empty(W_IDX, np.int32)
    for i in range(W_IDX):
        tt = t - (W_IDX - 1 - i) / W_IDX * TRACE_SPAN - glag
        grow[i] = MID_R - int(round(_at(tt) * amp * STEP)) + gdy
    gcl = np.clip(grow, 0, fr.rows - 1)
    gmask = (grow == gcl) & (fr.ch[gcl, cols] == I_BLANK)
    _plot(fr, grow, cols, I_DOT, P.mix(fg, C_VOID, gmix), mask=gmask)
    # dim body fill between the baseline and the line
    rs = []
    cs = []
    for i in range(W_IDX):
        rr = int(rows[i])
        if abs(rr) < 2:
            continue
        step = 1 if rr > 0 else -1
        for k in range(1, abs(rr)):
            rs.append(MID_R - step * k)
            cs.append(i)
    if rs:
        rs = np.asarray(rs, np.int32)
        cs = np.asarray(cs, np.int32)
        ok = (fr.ch[rs, cs] == I_BLANK) | (fr.ch[rs, cs] == I_DOT)
        _plot(fr, rs, cs, I_DOT, P.mix(fg, C_VOID, 0.70), ok)
    # bright stroke + steep-slope connectors so the QRS reads as one line
    r_st = np.clip(MID_R - rows, TRACE_R0, TRACE_R0 + TRACE_H)
    av = np.abs(vals)
    ctab = np.stack([P.mix(fg, C_VOID, 0.52), fg, peak])          # (3,3)
    sel = (av > 0.18).astype(np.int8) + (av > 0.62).astype(np.int8)
    crs = []
    ccs = []
    for i in range(1, W_IDX):
        r0 = int(r_st[i - 1])
        r1 = int(r_st[i])
        if abs(r1 - r0) > 1:
            lo, hi = (r0, r1) if r0 < r1 else (r1, r0)
            for rr in range(lo + 1, hi):
                crs.append(rr)
                ccs.append(i)
    if crs:
        _plot(fr, np.asarray(crs, np.int32), np.asarray(ccs, np.int32),
              I_BLOCK, ctab[sel[np.asarray(ccs, np.int32)]])
    _plot(fr, r_st, cols, I_BLOCK, ctab[sel])
    lower = r_st + 1
    _plot(fr, lower, cols, I_HALF, (ctab[sel] * 0.50).astype(np.uint8),
          mask=lower <= TRACE_R0 + TRACE_H)
    # leading edge + now marker
    for r in range(TRACE_R0, TRACE_R0 + TRACE_H + 1):
        if fr.ch[r, W_IDX - 1] == I_BLANK:
            _plot(fr, (r,), (W_IDX - 1,), I_DOT, EDGE_COL)
    r_now = int(np.clip(MID_R - int(rows[-1]), TRACE_R0, TRACE_R0 + TRACE_H))
    _plot(fr, (r_now,), (W_IDX - 1,), F.char_index("◉"), peak)
    return vals, rows


def _rings(fr, ctx, color):
    """Pulse rings radiated from the middle of the trace on every QRS."""
    t = ctx.t
    for lag, maxpx in ((0.0, 430.0), (0.33, 300.0), (0.66, 190.0)):
        p = ((t - BEAT0) / BEAT) % 1.0 - lag
        if p < 0.0 or p >= 1.0:
            continue
        e = fx.ease_out(min(1.0, p * 1.15))
        rpx = 26 + e * maxpx
        a = (1.0 - p) ** 1.6
        col = P.mix(C_VOID, color, 0.18 + 0.62 * a)
        rx = rpx / 10.0
        ry = rpx / 18.0
        n = max(44, int(rx * 2.4))
        th = np.arange(n, dtype=np.float32) * (2 * math.pi / n)
        cs = np.round(96 + rx * np.cos(th)).astype(np.int32)
        rs = np.round(MID_R + ry * np.sin(th)).astype(np.int32)
        idx = np.full(n, I_DOT, np.int16)
        idx[::12] = I_RING
        ok = (rs >= 0) & (rs < fr.rows) & (cs >= 0) & (cs < fr.cols)
        rcl = np.clip(rs, 0, fr.rows - 1)
        ccl = np.clip(cs, 0, fr.cols - 1)
        ok &= (fr.ch[rcl, ccl] == I_BLANK) | (fr.ch[rcl, ccl] == I_DOT)
        _plot(fr, rs, cs, idx, col, ok)


def _qrs_marker(fr, t):
    """Bright cursor riding just behind the freshest QRS."""
    bt = BEAT0 + math.floor((t - BEAT0) / BEAT) * BEAT
    age = t - bt
    if age > 0.17:
        return
    c = int(round(W_IDX - 1 - age / TRACE_SPAN * W_IDX))
    if not (0 <= c < W_IDX):
        return
    for r in range(TRACE_R0, TRACE_R0 + TRACE_H + 1):
        if fr.ch[r, c] in (I_BLANK, I_DOT):
            _plot(fr, (r,), (c,), F.char_index("║"),
                  P.mix(C_WHITE, C_GOLD, 0.35))
    _plot(fr, (TRACE_R0 - 1,), (c,), F.char_index("◆"), C_GOLD)


# --------------------------------------------------------------------- HUD ----
def _rate_block(fr, ctx, p2):
    c0 = 2
    if p2 < 0.6:
        fr.write(1, c0, "HEART-RATE // SINUS", fg=C_DIM)
        bpm = 128 + int(round(4 * math.sin(ctx.t * 1.7) + 2 * ctx.pulse))
        _ghost_text(fr, str(bpm), 2, c0 + 1, 6, C_GOLD, C_WHITE, ghost=2,
                    align="left", step=1)
        fr.write(8, c0, "BPM // A-V DELAY 120MS", fg=C_MID)
        fr.write(9, c0, "R-R 461MS  QRS 092MS  SPO2 98.6%", fg=C_DIM)
    else:
        fr.write(1, c0, "SYNC // COMPLETION LOCK", fg=P.mix(C_GOLD, C_DIM, 0.5))
        rows = [("SYNC", "LOCKED", C_TEAL), ("PULSE", "STEADY", C_TEAL),
                ("BEATS", f"{ctx.beat_i:04d}", C_MID), ("FILL", "100.0 %", C_GOLD)]
        for i, (k, v, col) in enumerate(rows):
            fr.write(2 + i * 2, c0, k.ljust(6, ".") + " ", fg=C_DIM)
            fr.write(2 + i * 2, c0 + 8, v, fg=col)


def _stats_block(fr, ctx, p2):
    c0 = 146
    fr.write(1, c0, "TELEMETRY // LEAD-II ARRAY", fg=C_DIM)
    entries = [
        (2, "SPO2", "98.6 %", C_TEAL),
        (3, "RESP", "13 /MIN", C_PRIMARY),
        (4, "VOICE", "ACQUIRED", C_GOLD),
        (5, "MODE", "COMPLETE" if p2 > 0.5 else "VIBRATION",
         C_WHITE if p2 > 0.5 else C_GOLD),
        (6, "GAIN", "10 MM/MV", C_MID),
        (8, "BEAT", f"{ctx.beat_i:04d}", C_MID),
        (9, "BAR", f"{ctx.bar_i:03d}", C_DIM),
    ]
    for r, k, v, col in entries:
        fr.write(r, c0, k.ljust(6, ".") + " ", fg=C_DIM)
        fr.write(r, c0 + 8, v, fg=col)
    # signal-strength marks in the right margin
    lvl = int(fx.clamp(ctx.rms * 9, 0, 8))
    for i in range(6):
        on = i < max(1, lvl // 2)
        _plot(fr, (3 + i,), (c0 + 44,), F.char_index("▏"),
              C_TEAL if on else P.mix(C_LINE, C_VOID, 0.35))


def _big_word(fr, ctx, p2):
    if p2 < 0.7:
        fade = 1.0 - p2 / 0.7
        col = P.mix(C_VOID, P.mix(C_TEAL, C_VOID, 0.58), fade)
        _ghost_text(fr, "HEARTBEAT", 1, 96, 8, col, None, ghost=1,
                    align="center", step=1)
    if p2 > 0.22:
        q = fx.smoothstep(p2, 0.22, 1.0)
        h = int(round(4 + 5 * q))
        col = P.mix(C_GOLD, C_WHITE, 0.10 + 0.28 * ctx.pulse)
        _ghost_text(fr, "COMPLETE", 10 - h, 96, h, col, C_WHITE,
                    ghost=3 if h < 7 else 2, align="center", step=1)


def _completion(fr, ctx, p2):
    if p2 <= 0.0:
        return
    if p2 > 0.22:
        pct = fx.clamp(p2 * 1.8)
        W.progress_bar(fr, 10, 24, 132, pct, fg=C_GOLD, bg=C_VOID,
                       label=None, show_pct=False)
        fr.write(10, 158, f"{pct * 100:5.1f}%  HEART FULL", fg=C_WHITE, bg=C_VOID)
        fr.write(10, 2, "COMPLETION", fg=P.mix(C_GOLD, C_DIM, 0.3), bg=C_VOID)
    fr.write(29, 156, "LOCKED" if p2 > 0.7 else "SYNCING",
             fg=P.mix(C_GOLD, C_DIM, 0.4), bg=C_PANEL)


# --------------------------------------------------------- bottom readouts ----
def _band_feed(fr, ctx, r0, h, p2):
    b = np.clip(np.asarray(ctx.bands, np.float32), 0, 1) ** 1.65
    peak = np.maximum(b, np.asarray(
        ctx.assets.bands_at(max(0.0, ctx.t - 0.30)), np.float32) ** 1.65 * 0.85)
    hi = C_TEAL if p2 < 0.5 else C_GOLD
    ramp = [P.mix(BAND_LO, hi, (k + 1) / h) for k in range(h)]
    for bi in range(64):
        c0 = bi * 3
        total = float(b[bi]) * h
        full = int(total)
        frac = total - full
        for k in range(full):
            r = r0 + h - 1 - k
            fr.fill_rect(r, c0, r, c0 + 1, "█", fg=ramp[k])
        if frac > 0.18 and full < h:
            r = r0 + h - 1 - full
            ch = P.RAMP_VERT[min(7, max(1, int(frac * 8)))]
            fr.fill_rect(r, c0, r, c0 + 1, ch, fg=ramp[min(h - 1, full)])
        pr = r0 + h - 1 - int(round(float(peak[bi]) * h))
        if r0 <= pr < r0 + h:
            fr.put(pr, c0, "▔", fg=P.mix(hi, C_WHITE, 0.30))


def _rhythm_history(fr, ctx, p2):
    r0, c0 = 36, 1
    _panel(fr, r0, c0, 42, 62, "VIBRATION HISTORY // 2.6S", fg=C_LINE)
    ts = np.linspace(ctx.t - 2.6, ctx.t, 112)
    vals = np.array([ctx.assets.rms_at(x) for x in ts], np.float32)
    fg = C_TEAL if p2 < 0.5 else C_GOLD
    W.braille_plot(fr, r0 + 1, c0 + 2, 56, 3, vals, fg=fg)
    cur = float(vals[-1])
    fr.write(r0 + 5, c0 + 2, "PEAK", fg=C_DIM)
    fr.write(r0 + 5, c0 + 8, f"{cur*100:5.1f}", fg=C_WHITE)
    fr.write(r0 + 5, c0 + 20, "MEAN", fg=C_DIM)
    fr.write(r0 + 5, c0 + 26, f"{float(vals.mean())*100:5.1f}", fg=C_MID)
    fr.write(r0 + 5, c0 + 38, "RMS", fg=C_DIM)
    fr.write(r0 + 5, c0 + 43, f"{ctx.rms*100:5.1f}", fg=fg)


def _pacing(fr, ctx, p2):
    r0, c0 = 36, 66
    _panel(fr, r0, c0, 42, 126, "PACING // PHASE LOCK", fg=C_LINE)
    fg = C_TEAL if p2 < 0.5 else C_GOLD
    cur_col = P.mix(C_WHITE, C_VOID, 0.10)
    for k in range(18):
        bi = ctx.beat_i - 9 + k
        if bi < 0:
            continue
        cur = (k == 9)
        on = cur or (bi % 2 == 0)
        _plot(fr, (r0 + 2,), (c0 + 2 + k * 3,), F.char_index("●" if on else "○"),
              cur_col if cur else (fg if on else C_LINE))
        _plot(fr, (r0 + 3,), (c0 + 2 + k * 3,), F.char_index("│" if on else "▏"),
              P.mix(fg, C_VOID, 0.45))
    fr.write(r0 + 1, c0 + 2, "EXPECTED BEATS", fg=C_DIM)
    W.progress_bar(fr, r0 + 4, c0 + 2, 40, 0.5 + 0.44 * math.sin(ctx.t * 5.2),
                   fg=fg, bg=C_VOID, show_pct=False)
    fr.write(r0 + 4, c0 + 45, "PHASE", fg=C_DIM)
    fr.write(r0 + 5, c0 + 2, "SYNC LOCKED // A-V DELAY 120MS // ±42MS", fg=C_MID)


def _profile(fr, ctx, p2):
    r0, c0 = 36, 129
    _panel(fr, r0, c0, 42, 190, "CARDIAC PROFILE", fg=C_LINE)
    rows = [
        ("HRV", f"{42 + 6*math.sin(ctx.t*0.9):4.0f} MS", C_TEAL),
        ("AMP", f"{1.24 + 0.10*ctx.pulse:4.2f} MV", C_PRIMARY),
        ("PERF", f"{97 + 2*math.sin(ctx.t*1.3):5.1f} %", C_TEAL),
        ("FILL", f"{min(100.0, p2*100):5.1f} %", C_GOLD if p2 > 0.5 else C_MID),
    ]
    for i, (k, v, col) in enumerate(rows):
        r = r0 + 2 + (i // 2) * 2
        c = c0 + 2 + (i % 2) * 31
        fr.write(r, c, k + " ", fg=C_DIM)
        fr.write(r, c + len(k) + 1, v, fg=col)
    hp = 0.5 + 0.5 * ctx.pulse
    fr.write(r0 + 5, c0 + 2, "♥" if ctx.beat_p < 0.4 else "♡",
             fg=P.mix(P.C["red"], C_WHITE, hp))
    fr.write(r0 + 5, c0 + 4, "BEAT SYNC", fg=C_DIM)
    fr.write(r0 + 5, c0 + 18, "STATE", fg=C_DIM)
    fr.write(r0 + 5, c0 + 24, "COMPLETE" if p2 > 0.5 else "MEASURING",
             fg=C_GOLD if p2 > 0.5 else C_MID)


def _pulse_strip(fr, ctx, p2):
    """Beat-synced level meter right at the bottom edge."""
    t = ctx.t
    cols = np.arange(W_IDX, dtype=np.int32)
    v = 0.5 + 0.5 * np.sin(cols * 0.11 + t * 6.0)
    v = v * (0.35 + 0.65 * float(ctx.pulse))
    if p2 > 0.5:
        v = v * (0.4 + 0.6 * float(ctx.pulse))
    k = np.clip((v * 7.9).astype(int), 0, 7)
    ramp = [F.char_index(P.RAMP_VERT[i]) for i in range(8)]
    base = np.array(C_DIM, np.float32)
    tip = np.array(C_TEAL if p2 < 0.5 else C_GOLD, np.float32)
    cols_rgb = (base + (tip - base) * np.clip(v, 0, 1)[:, None]).astype(np.uint8)
    _plot(fr, np.full(W_IDX, 44, np.int32), cols, np.array(ramp, np.int16)[k],
          cols_rgb)


# ------------------------------------------------------------------- draw ----
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    p2 = fx.smoothstep(t, T_COMPLETE, T_COMPLETE + 0.55)
    ctx.meta["bloom"] = 0.24
    ctx.meta["flash"] = 0.0
    if t >= T_COMPLETE:
        ctx.meta["flash"] = 0.30 * (1.0 - fx.smoothstep(
            t, T_COMPLETE, T_COMPLETE + 0.20))
        ctx.meta["flash_color"] = C_GOLD
    if ctx.pulse > 0.55:
        ctx.shake(1.2 + 0.9 * ctx.pulse)

    _bg(ctx, fr, p2)

    # stage row 0: live monitor strip
    fr.write(0, 0, " ◉ LIVE // HEART MONITOR ", fg=C_DIM, bg=C_VOID)
    fr.write(0, 54, "SAMPLE 250HZ  12BIT  //  CHANNEL 01  //  LEAD-II",
             fg=P.mix(C_LINE, C_VOID, 0.20))
    fr.write(0, 150, f"T+{t:07.2f}  FRM {ctx.fi:05d}", fg=C_DIM)
    if ctx.beat_p < 0.10:
        fr.write(0, 120, "◉ BEAT", fg=C_GOLD)

    # scope panel
    fr.fill_rect(TRACE_R0, 0, TRACE_R0 + TRACE_H, W_IDX - 1, " ", bg=C_PANEL)
    # sweeping refresh line inside the scope
    sweep = TRACE_R0 + int((t * 3.0) % TRACE_H)
    fr.fill_rect(sweep, 0, sweep, W_IDX - 1, " ", bg=P.mix(C_PANEL, P.C["grid"], 0.35))
    _big_word(fr, ctx, p2)
    _grid(fr, t, p2)
    _pleth(fr, ctx, p2)
    _waves(fr, ctx, p2)
    trace_fg = P.mix(C_TEAL, C_GOLD, p2)
    trace_peak = P.mix(C_WHITE, C_GOLD, 0.55 * p2)
    amp = 1.0 - 0.40 * p2
    _trace(fr, t, amp, trace_fg, trace_peak, p2)
    _rings(fr, ctx, trace_peak)
    _qrs_marker(fr, t)

    # scope header / footer
    if p2 < 0.25:
        fr.write(10, 0, " ECG // LEAD II ", fg=C_MID, bg=C_VOID)
        fr.write(10, 160, " 25MM/S 10MM/MV ", fg=C_MID, bg=C_VOID)
        if ctx.beat_p < 0.30:
            fr.write(10, 84, " ◉ QRS DETECTED ", fg=C_GOLD, bg=C_VOID)
        else:
            fr.write(10, 84, " · SEEKING SIGNAL ", fg=C_DIM, bg=C_VOID)
    fr.write(29, 0, " FILTER 0.5-40HZ // ECG-E ", fg=C_DIM, bg=C_PANEL)
    if p2 > 0.7:
        fr.write(29, 84, " ✓ SIGNAL COMPLETE ✓ ", fg=C_GOLD, bg=C_PANEL)
    else:
        fr.write(29, 84, " ◉ VIBRATION LOCK ", fg=C_MID, bg=C_PANEL)
    fr.write(29, 168, f"GAIN {1.0 + 0.1*ctx.rms:4.2f}", fg=C_DIM, bg=C_PANEL)

    _rate_block(fr, ctx, p2)
    _stats_block(fr, ctx, p2)
    _completion(fr, ctx, p2)

    # vibration feed
    fr.write(30, 0, " VIBRATION FEED // " +
             ("COMPLETION" if p2 > 0.5 else "FEEL YOUR VIBRATIONS"),
             fg=C_MID, bg=C_VOID)
    _band_feed(fr, ctx, 31, 4, p2)
    fr.write(35, 0, " 20Hz", fg=C_DIM)
    fr.fill_rect(35, 6, 35, 148, "─", fg=SOFT)
    for k in range(7):
        _plot(fr, (35,), (6 + k * 24,), F.char_index("┴"),
              P.mix(C_LINE, C_VOID, 0.25))
    fr.write(35, 152, "16kHz ", fg=C_DIM)
    _rhythm_history(fr, ctx, p2)
    _pacing(fr, ctx, p2)
    _profile(fr, ctx, p2)

    if p2 > 0.72:
        blink = "✓" if int(ctx.t * 3) % 2 == 0 else "●"
        fr.ctext(43, f"{blink} HEART FULL   {blink} FEELING COMPLETE   "
                 f"{blink} SYNCHRONISED   {blink} 100%",
                 fg=P.mix(C_GOLD, C_WHITE, 0.3))
    else:
        W.marquee(fr, 43, "▸ FEEL YOUR VIBRATIONS ▸ SIGNAL ACQUIRED ▸ COMPLETION "
                  "PENDING ▸ STAY ▸ ", t, speed=22,
                  fg=P.mix(C_TEAL, C_VOID, 0.32), gap=6)
    _pulse_strip(fr, ctx, p2)
    return fr
