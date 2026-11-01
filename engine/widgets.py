"""Reusable widgets: progress bars, ECG, spectrum columns, node graphs, rain,
sparklines, attention/token grids, log streams, braille plotters.
"""
from __future__ import annotations

import math

import numpy as np

from . import font as F
from . import fx
from . import palette as P

_HEX = "0123456789ABCDEF"


# ---------------------------------------------------------------- plotting --
def plot_columns(fr, c0, r0, values, h, lo=-1.0, hi=1.0, ramp=None, fg=None,
                 baseline=None, bg=None, dot=False):
    """Plot a value series as a filled column chart (values array -> h rows)."""
    ramp = ramp or P.RAMP_VERT
    v = np.asarray(values, np.float32)
    if baselen := 0:
        pass
    for i, val in enumerate(v):
        c = c0 + i
        if c < 0 or c >= fr.cols:
            continue
        x = (val - lo) / max(1e-6, hi - lo)
        x = fx.clamp(x)
        for k in range(h):
            if k / max(1, h) < x:
                fr.put(r0 + h - 1 - k, c, ramp[4] if dot else "█", fg=fg, bg=bg)
        if baseline is not None:
            fr.put(r0 + h - 1 - baseline, c, "─", fg=P.C["line"], bg=bg)
    return r0


def sparkline(fr, r0, c0, values, h, ramp=None, fg=None, bg=None):
    """Draw a single-line trace like a mini oscilloscope."""
    ramp = ramp or P.RAMP_HI
    v = np.asarray(values, np.float32)
    n = len(v)
    if n == 0:
        return
    prev_row = None
    for i in range(n):
        c = c0 + i
        if c < 0 or c >= fr.cols:
            continue
        y = int(round((1.0 - fx.clamp(v[i])) * (h - 1)))
        r = r0 + y
        if prev_row is not None and prev_row != y:
            steps = abs(prev_row - y)
            for s in range(1, steps):
                rr = prev_row + (1 if y > prev_row else -1) * s
                fr.put(rr, c, "│" if s == steps // 2 else "·", fg=fg, bg=bg)
        ch = "●" if i == n - 1 else "─"
        fr.put(r, c, ch, fg=fg, bg=bg)
        prev_row = y


def ecg_trace(fr, r0, c0, w, h, t, fg=None, fg_peak=None, grid=True, bpm=130.0,
              phase_shift=0.0, amp=1.0, label=True, bg=None):
    """Electrocardiogram waveform scrolling leftwards; returns current level."""
    fg = fg or P.C["teal"]
    fg_peak = fg_peak or P.C["white"]
    period = 60.0 / bpm
    if grid:
        for c in range(0, w, 4):
            for r in range(0, h, 2):
                if fr.get(r0 + r, c0 + c) == " ":
                    fr.put(r0 + r, c0 + c, "·", fg=P.C["grid"], bg=bg)
    mid = r0 + h // 2
    vals = []
    for i in range(w):
        tt = t - (w - 1 - i) / w * (period * 2.6)
        ph = ((tt / period) + phase_shift) % 1.0
        v = _ecg_shape(ph) * amp
        vals.append(v)
        # compress positive/negative amplitude into h/2 rows
        rows = int(round(v * (h / 2 - 0.6)))
        r = mid - rows
        ch = "▌"
        col = fg
        if abs(v) > 0.62:
            col = fg_peak
            ch = "█"
        elif abs(v) > 0.2:
            ch = "▐"
        fr.put(r, c0 + i, ch, fg=col, bg=bg)
        if rows != 0 and abs(rows) < h // 2:
            # connect to baseline
            step = 1 if rows > 0 else -1
            for k in range(0, abs(rows)):
                rr = mid - step * k
                if rr != r and fr.get(rr, c0 + i) == " ":
                    fr.put(rr, c0 + i, "·", fg=P.mix(fg, P.C["void"], 0.45), bg=bg)
    # baseline
    for i in range(w):
        if fr.get(mid, c0 + i) == " ":
            fr.put(mid, c0 + i, "─", fg=P.mix(fg, P.C["void"], 0.6), bg=bg)
    if label:
        fr.write(r0, c0, "ECG//LEAD-II", fg=P.C["dim"], bg=bg)
        fr.rtext(r0, f"{int(round(60.0 / period))} BPM", fg=P.C["gold"], bg=bg, pad=0)
    return vals[-1] if vals else 0.0


def _ecg_shape(ph):
    """A recognisable P-QRS-T shape over one beat phase."""
    v = 0.0
    # P wave
    v += 0.14 * math.exp(-((ph - 0.13) / 0.030) ** 2)
    # Q
    v -= 0.16 * math.exp(-((ph - 0.205) / 0.014) ** 2)
    # R
    v += 1.0 * math.exp(-((ph - 0.235) / 0.013) ** 2)
    # S
    v -= 0.30 * math.exp(-((ph - 0.268) / 0.018) ** 2)
    # T
    v += 0.26 * math.exp(-((ph - 0.40) / 0.055) ** 2)
    # U
    v += 0.05 * math.exp(-((ph - 0.55) / 0.05) ** 2)
    return v


# ------------------------------------------------------------- bar widgets --
def progress_bar(fr, r, c, w, frac, fg=None, bg=None, label=None, style=1,
                 show_pct=True, color_by=None):
    """[██████▌───] style progress bar; returns (r, end_col)."""
    fg = fg or P.C["primary"]
    frac = fx.clamp(frac)
    inner = w - 2
    fill = frac * inner
    full = int(fill)
    part = fill - full
    if style == 2:
        left, right = "╡", "╞"
        fr.put(r, c, left, fg=fg, bg=bg)
        fr.put(r, c + w - 1, right, fg=fg, bg=bg)
    else:
        fr.write(r, c, "[", fg=fg, bg=bg)
        fr.write(r, c + w - 1, "]", fg=fg, bg=bg)
    for i in range(inner):
        x = c + 1 + i
        if i < full:
            col = fg if color_by is None else color_by((i + 1) / inner)
            fr.put(r, x, "█", fg=col, bg=bg)
        elif i == full and part > 0.08:
            col = fg if color_by is None else color_by((i + 1) / inner)
            ch = "▏▎▍▌▋▊▉█"[min(7, int(part * 8))]
            fr.put(r, x, ch, fg=col, bg=bg)
        else:
            fr.put(r, x, "─", fg=P.mix(fg, P.C["void"], 0.72), bg=bg)
    end = c + w
    if show_pct:
        fr.write(r, end + 1, f"{frac * 100:5.1f}%", fg=fg, bg=bg)
        end += 7
    if label:
        fr.write(r, end + 1, label, fg=P.C["dim"], bg=bg)
        end += 1 + len(label)
    return r, end


def segmented_bar(fr, r, c, w, frac, cells=8, fg=None, bg=None):
    """Discrete block meter (8 segments)."""
    fg = fg or P.C["gold"]
    on = frac * cells
    fr.write(r, c, "[", fg=P.C["line"], bg=bg)
    for i in range(cells):
        x = c + 1 + i
        if i < int(on):
            fr.put(r, x, "■", fg=fg, bg=bg)
        elif i < on:
            fr.put(r, x, "▌", fg=fg, bg=bg)
        else:
            fr.put(r, x, "·", fg=P.C["grid"], bg=bg)
    fr.write(r, c + 1 + cells, "]", fg=P.C["line"], bg=bg)
    return c + cells + 2


def hex_dump(fr, r0, c0, rows, cols, t, seed=0, fg=None, step=0.35):
    """Scrolling hex dump where each line holds for `step` seconds."""
    fg = fg or P.C["mid"]
    line_no = int(t / step)
    for i in range(rows):
        addr = (line_no - i) & 0xFFFF
        r = r0 + i
        s = f"{(addr * 16):06X}  "
        for j in range((cols - 8) // 3):
            v = int(fx.hash01(addr, j, seed) * 256)
            s += f"{v:02X} "
        fr.write(r, c0, s, fg=fg)
    return rows


def data_column(fr, r0, c0, h, t, seed=0, speed=6.0, fg=None):
    """A single scrolling data column of hex tokens."""
    fg = fg or P.C["mid"]
    off = t * speed
    for i in range(h):
        y = (i + int(off)) % h
        v = int(fx.hash01(seed, y, int(off)) * 256)
        ch = _HEX[v >> 4]
        a = fx.hash01(seed, y, int(off), 3)
        fr.put(r0 + i, c0, ch, fg=P.mix(fg, P.C["void"], 0.25 + 0.55 * a))


def side_data(fr, t, seed=0, left_w=14, right_w=14, fg=None):
    """Two vertical data scrolls down the left/right edges of the stage."""
    for c in range(left_w):
        data_column(fr, 0, c, fr.rows, t, seed=seed + c, speed=5.0 + (c % 3) * 2.5,
                    fg=fg or P.C["cyan2"] if "cyan2" in P.C else None)
    for c in range(fr.cols - right_w, fr.cols):
        data_column(fr, 0, c, fr.rows, t, seed=seed + 91 + c, speed=4.0 + (c % 4),
                    fg=fg)


# ------------------------------------------------------------ matrix rain --
def matrix_rain(fr, t, seed=0, density=0.55, speed=9.0, fg=None, fg_head=None,
                region=None, chars=None):
    r0, c0, r1, c1 = region or (0, 0, fr.rows - 1, fr.cols - 1)
    pool = chars or "01ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
    # never emit a glyph the atlas does not have
    pool = "".join(ch for ch in pool if F.char_index(ch) > 0) or "01#%&"
    fg = fg or P.C["green"]
    for c in range(c0, c1 + 1, 1):
        h = fx.hash01(seed, c, 1)
        if h > density:
            continue
        sp = speed * (0.5 + fx.hash01(seed, c, 2) * 1.3)
        head = (t * sp + fx.hash01(seed, c, 3) * 60) % (fr.rows + 24) - 12
        trail = int(4 + fx.hash01(seed, c, 4) * 10)
        for k in range(trail):
            r = int(head) - k
            if r < r0 or r > r1:
                continue
            a = 1.0 - k / trail
            ch = pool[int(fx.hash01(seed, c, r, int(t * 6)) * len(pool)) % len(pool)]
            if k == 0:
                fr.put(r, c, ch, fg=fg_head or P.C["white"])
            elif a > 0.55:
                fr.put(r, c, ch, fg=fg)
            else:
                fr.put(r, c, ch, fg=P.mix(fg, P.C["void"], 0.35 + 0.5 * (1 - a)))


# ----------------------------------------------------------- node graphs ----
def line_cells(fr, r0, c0, r1, c1, fg, ch=None, odd="·"):
    """Bresenham line in cell space using box-drawing chars."""
    dr = r1 - r0
    dc = c1 - c0
    n = max(abs(dr), abs(dc), 1)
    for k in range(n + 1):
        r = r0 + int(round(dr * k / n))
        c = c0 + int(round(dc * k / n))
        if not fr.inb(r, c):
            continue
        if ch:
            fr.put(r, c, ch, fg=fg)
        else:
            if abs(dc) >= abs(dr):
                fr.put(r, c, "─" if dr == 0 else ("\\" if dr * dc > 0 else "/"), fg=fg)
            else:
                fr.put(r, c, "│", fg=fg)


def node(fr, r, c, state="on", fg=None, label=None, halo=0):
    fg = fg or P.C["primary"]
    ch = {"on": "◉", "off": "○", "dead": "×", "warn": "◍"}.get(state, "◉")
    if halo:
        for k in range(1, halo + 1):
            for d in ((k, 0), (-k, 0), (0, k), (0, -k)):
                rr, cc = r + d[0], c + d[1]
                if fr.inb(rr, cc) and fr.get(rr, cc) == " ":
                    fr.put(rr, cc, "·", fg=P.mix(fg, P.C["void"], 0.6))
    fr.put(r, c, ch, fg=fg)
    if label:
        fr.write(r, c + 2, label, fg=P.mix(fg, P.C["white"], 0.2))


# ---------------------------------------------------------- attention grid --
def token_grid(fr, r0, c0, rows, cols, tokens, weights, fg=None, bg=None,
               highlight=-1):
    """Token matrix for the ML/LLM scene; weights 0..1 per cell."""
    fg = fg or P.C["teal"]
    ramp = " .:-=+*#%@"
    for i in range(rows):
        for j in range(cols):
            r, c = r0 + i, c0 + j
            if not fr.inb(r, c):
                continue
            w = weights[i][j] if hasattr(weights, "__getitem__") else 0
            ch = tokens[(i * cols + j) % len(tokens)]
            if ch == " ":
                continue
            v = fx.clamp(w)
            col = P.mix(P.C["line"], fg, v)
            if i == highlight:
                col = P.C["gold"]
            fr.put(r, c, ch, fg=col, bg=bg)


def attention_matrix(fr, r0, c0, n, t, seed=0, fg=None, bg=None):
    """Softmax-like attention heatmap (mostly diagonal, collapsing)."""
    fg = fg or P.C["primary"]
    ramp = " ░▒▓█"
    for i in range(n):
        for j in range(n):
            d = abs(i - j)
            base = math.exp(-d * 0.45)
            wob = fx.noise2d(i * 0.3, j * 0.3 + t, seed) * 0.3
            v = fx.clamp(base * 0.85 + wob + 0.1 * fx.hash01(i, j, seed))
            ch = ramp[min(4, int(v * 5))]
            fr.put(r0 + i, c0 + j, ch, fg=P.mix(P.C["line"], fg, v), bg=bg)


# ------------------------------------------------------------------ misc ----
def marquee(fr, r, text, t, speed=12.0, fg=None, bg=None, gap=8):
    fg = fg or P.C["mid"]
    s = text + " " * gap
    off = int(t * speed) % len(s)
    doubled = s * 3
    fr.write(r, 0, doubled[off:off + fr.cols], fg=fg, bg=bg)


def typing(fr, r, c, text, t, start=0.0, cps=28.0, fg=None, cursor=True):
    fg = fg or P.C["fg"]
    n = int(fx.clamp((t - start) * cps, 0, len(text)))
    fr.write(r, c, text[:n], fg=fg)
    if cursor and int((t - start) * 4) % 2 == 0 and n < len(text):
        fr.put(r, c + n, "█", fg=fg)
    return c + n


def crosshair(fr, r, c, size=5, fg=None, label=None):
    fg = fg or P.C["gold"]
    fr.hline(r, c - size, c - 2, "─", fg=fg)
    fr.hline(r, c + 2, c + size, "─", fg=fg)
    fr.vline(c, r - size, r - 2, "│", fg=fg)
    fr.vline(c, r + 2, r + size, "│", fg=fg)
    fr.put(r, c, "＋", fg=fg)
    if label:
        fr.write(r + 1, c + 2, label, fg=fg)


def spinner(fr, r, c, t, fg=None, frames="|/-\\"):
    fr.put(r, c, frames[int(t * 12) % len(frames)], fg=fg or P.C["primary"])


def dots_progress(fr, r, c, n, k, fg=None):
    fg = fg or P.C["primary"]
    for i in range(n):
        fr.put(r, c + i * 2, "●" if i < k else "○",
               fg=fg if i < k else P.C["grid"])


def braille_plot(fr, r0, c0, w, h, values, fg=None):
    """Plot a series at 2x4 sub-cell resolution using braille glyphs."""
    fg = fg or P.C["primary"]
    grid = np.zeros((h * 4, w * 2), bool)
    v = np.asarray(values, np.float32)
    n = min(len(v), w * 2)
    for i in range(n):
        y = int(round((1 - fx.clamp(v[i])) * (h * 4 - 1)))
        grid[y, i] = True
    for cy in range(h):
        for cx in range(w):
            code = 0
            sub = grid[cy * 4:(cy + 1) * 4, cx * 2:(cx + 1) * 2]
            if sub[0, 0]: code |= 1
            if sub[1, 0]: code |= 2
            if sub[2, 0]: code |= 4
            if sub[3, 0]: code |= 8
            if sub[0, 1]: code |= 16
            if sub[1, 1]: code |= 32
            if sub[2, 1]: code |= 64
            if sub[3, 1]: code |= 128
            if code:
                fr.put(r0 + cy, c0 + cx, chr(0x2800 + code), fg=fg)
