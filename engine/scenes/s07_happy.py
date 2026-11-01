"""s07_happy - happy execution.  A runtime monitor where every readout has
been rewritten to the same answer: eight threads, a completion bar that only
ever fills, an execution log that keeps printing the same happy line.

66.654 - 70.347
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .. import font as F
from .. import fx
from .. import palette as P

ROWS, COLS = 45, 192
V = P.C["void"]
VOID2 = P.C["void2"]
PANEL = P.C["panel"]
PRIMARY = P.C["primary"]
TEAL = P.C["teal"]
GOLD = P.C["gold"]
RED = P.C["red"]
VIO = P.C["violet"]
WHITE = P.C["white"]
DIM = P.C["dim"]
AMBER = P.C["amber"]

_LINES = (0.0, 3.692, 7.385, 11.077, 14.770)


# ------------------------------------------------------- fast cell raster ----
_ATL = None
_IDX = {}


def _ai():
    global _ATL
    if _ATL is None:
        _ATL = F.get_atlas()[1]
    return _ATL


def ci(ch):
    v = _IDX.get(ch)
    if v is None:
        v = _IDX[ch] = _ai().get(ch, 0)
    return v


def ramp(a, b, n=17):
    A = np.asarray(a, np.float32)
    B = np.asarray(b, np.float32)
    f = np.linspace(0.0, 1.0, n)[:, None]
    return (A[None, :] * (1 - f) + B[None, :] * f).astype(np.uint8)


def rc(tbl, f):
    return tbl[int(np.clip(f, 0.0, 0.9999) * (len(tbl) - 1))]


R_GRID = ramp(V, P.C["grid"])
R_LINE = ramp(V, P.C["line"])
R_DIMC = ramp(V, DIM)
R_TEAL = ramp(V, TEAL)
R_PRIM = ramp(V, PRIMARY)
R_GOLD = ramp(V, GOLD)
R_RED = ramp(V, RED)
R_VIO = ramp(V, VIO)
R_AMBER = ramp(V, AMBER)
R_TW = ramp(TEAL, WHITE)
R_PW = ramp(PRIMARY, WHITE)
R_GW = ramp(GOLD, WHITE)
R_RW = ramp(RED, WHITE)
RAMP_IDX = np.asarray([ci(" "), ci("░"), ci("▒"), ci("▓"), ci("█")], np.int16)


def put(fr, r, c, ch, col):
    r = int(r)
    c = int(c)
    if 0 <= r < ROWS and 0 <= c < COLS:
        fr.ch[r, c] = ci(ch)
        fr.fg[r, c] = col


def text(fr, r, c, s, col):
    r = int(r)
    c = int(c)
    if not (0 <= r < ROWS) or c >= COLS:
        return
    if c < 0:
        s = s[-c:]
        c = 0
    n = min(len(s), COLS - c)
    fr.ch[r, c:c + n] = [ci(x) for x in s[:n]]
    fr.fg[r, c:c + n] = col


def ctext(fr, r, s, col):
    text(fr, r, (COLS - len(s)) // 2, s, col)


def plot(fr, Y, X, CH, COL):
    Y = np.asarray(Y, np.int32)
    X = np.asarray(X, np.int32)
    m = (Y >= 0) & (Y < ROWS) & (X >= 0) & (X < COLS)
    if not m.any():
        return
    Y = Y[m]
    X = X[m]
    if isinstance(CH, str):
        fr.ch[Y, X] = ci(CH)
    else:
        CH = np.asarray(CH, np.int16)
        if CH.ndim:
            CH = CH[m]
        fr.ch[Y, X] = CH
    C = np.asarray(COL)
    fr.fg[Y, X] = C[m] if C.ndim == 2 else C


def line(fr, r0, c0, r1, c1, col, ch="·"):
    n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
    f = np.linspace(0.0, 1.0, n)
    plot(fr, np.round(r0 + (r1 - r0) * f), np.round(c0 + (c1 - c0) * f), ch, col)


def fill(fr, r0, c0, r1, c1, ch=" ", col=None, bg=None):
    r0 = max(0, int(r0))
    c0 = max(0, int(c0))
    r1 = min(ROWS - 1, int(r1))
    c1 = min(COLS - 1, int(c1))
    if r1 < r0 or c1 < c0:
        return
    sl = (slice(r0, r1 + 1), slice(c0, c1 + 1))
    fr.ch[sl] = ci(ch)
    if col is not None:
        fr.fg[sl] = col
    if bg is not None:
        fr.bg[sl] = bg


def paint(fr, mask, c0, r0, w, h, c_lo, c_hi=None, gain=1.8, min_v=0.045):
    """Coverage-mask painter: same result as Frame.paint_mask, ~20x faster."""
    mask = np.asarray(mask, np.float32)
    if mask.shape != (h * 18, w * 10):
        mask = F.resize_mask(mask, w * 10, h * 18)
    cells = np.clip(mask.reshape(h, 18, w, 10).mean(axis=(1, 3)) * gain, 0.0, 1.0)
    CH = RAMP_IDX[np.clip((cells * 4 + 0.5).astype(np.int32), 0, 4)]
    if c_hi is None:
        FG = np.broadcast_to(np.asarray(c_lo, np.uint8), (h, w, 3)).copy()
    else:
        v = cells[..., None]
        FG = (np.asarray(c_lo, np.float32) * (1 - v) +
              np.asarray(c_hi, np.float32) * v).astype(np.uint8)
    r0i = max(0, int(r0))
    c0i = max(0, int(c0))
    r1i = min(ROWS, int(r0) + h)
    c1i = min(COLS, int(c0) + w)
    if r1i <= r0i or c1i <= c0i:
        return
    src = (slice(r0i - r0, r1i - r0), slice(c0i - c0, c1i - c0))
    m = cells[src] >= min_v
    if not m.any():
        return
    dst = (slice(r0i, r1i), slice(c0i, c1i))
    sub = fr.ch[dst]
    sub[m] = CH[src][m]
    subf = fr.fg[dst]
    subf[m] = FG[src][m]


def bigtext(fr, s, r0, c0, h, c_lo, c_hi, align="center", gain=1.0):
    tm = F.text_mask(s, int(h * 18), bold=True)
    w = max(1, int(round(tm.shape[1] / 10.0)))
    if align == "center":
        c0 = int(round(c0 - w / 2.0))
    elif align == "right":
        c0 = int(round(c0 - w))
    paint(fr, tm, c0, r0, w, max(1, int(round(tm.shape[0] / 18.0))), c_lo, c_hi,
          gain=gain)
    return w


def band(fr, r0, r1, bg=None):
    fill(fr, r0, 0, r1, COLS - 1, " ", col=DIM, bg=bg if bg is not None else VOID2)
    for r in range(r0, r1 + 1, 2):
        fr.ch[r, 0:COLS:3] = ci("·")
        fr.fg[r, 0:COLS:3] = rc(R_LINE, 0.5)


def _h01(x):
    v = np.sin(np.asarray(x, np.float64) * 12.9898) * 43758.5453
    return v - np.floor(v)


# ----------------------------------------------------------- infinity art ----
_INF = None


def infm():
    global _INF
    if _INF is None:
        W, H = 420, 184
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        pts = []
        n = 1080
        for i in range(n + 1):
            a = i / n * 2 * math.pi
            den = 1.0 + math.sin(a) ** 2
            x = math.cos(a) / den
            y = math.sin(a) * math.cos(a) / den
            pts.append((W * 0.5 + x * W * 0.47, H * 0.5 + y * W * 0.47))
        d.line(pts, fill=255, width=11, joint="curve")
        im = im.filter(ImageFilter.GaussianBlur(3.6))
        _INF = np.asarray(im, np.float32) / 255.0
    return _INF


# ------------------------------------------------------------- 3d helpers ----
def _rot(pts, ay, ax):
    cY, sY = math.cos(ay), math.sin(ay)
    cX, sX = math.cos(ax), math.sin(ax)
    x = pts[:, 0] * cY + pts[:, 2] * sY
    z1 = -pts[:, 0] * sY + pts[:, 2] * cY
    y = pts[:, 1] * cX - z1 * sX
    z = pts[:, 1] * sX + z1 * cX
    return np.stack([x, y, z], axis=1)


def _lemn(n=110):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    den = 1.0 + np.sin(a) ** 2
    return np.cos(a) / den, np.sin(a) * np.cos(a) / den


# --------------------------------------------------------------- background --
def _bg(fr, t):
    fr.ch[0:ROWS:3, 0:COLS:4] = ci("·")
    fr.fg[0:ROWS:3, 0:COLS:4] = rc(R_DIMC, 0.32)
    for k in range(3):
        r = int((t * 4.0 + k * 15.0) % 52) - 4
        if 0 <= r < ROWS:
            fr.ch[r, 0:COLS:3] = ci("─")
            fr.fg[r, 0:COLS:3] = rc(R_LINE, 0.42)
    k = np.arange(64, dtype=np.float64)
    X = (_h01(k + 1) * COLS + t * (4 + (k % 5) * 2)) % COLS
    Y = (_h01(k * 3.7 + 2) * ROWS + np.sin(t * 0.9 + k * 1.7) * 2.2) % ROWS
    CH = np.where(k % 4 == 0, ci("+"), ci("·"))
    plot(fr, Y.astype(np.int32), X.astype(np.int32), CH, rc(R_PRIM, 0.45))


def _rulers(fr, t):
    ph = int(t * 20) % 16
    arr = (np.arange(43) * 3 + ph) % 16
    hx = np.asarray([ci("%X" % i) for i in range(16)], np.int16)
    fr.ch[1:44, 0] = hx[arr]
    fr.fg[1:44, 0] = rc(R_TEAL, 0.5)
    fr.ch[1:44, 191] = hx[arr[::-1]]
    fr.fg[1:44, 191] = rc(R_TEAL, 0.36)
    for r in range(2, 45, 5):
        put(fr, r, 1, "▪", rc(R_LINE, 0.9))
        put(fr, r, 190, "▪", rc(R_LINE, 0.7))


def _floor(fr, t, horizon=22, tbl=None, alpha=1.0, nr=9, spread=11.0):
    tbl = tbl if tbl is not None else R_TEAL
    hh = ROWS - horizon
    r_vals = np.arange(horizon + 2, ROWS)
    f = (r_vals - horizon) / hh
    rays = np.arange(-nr, nr + 1)
    Y = np.repeat(r_vals, len(rays))
    FF = np.tile(f, len(rays))
    K = np.repeat(rays, len(r_vals))
    X = np.round(96.0 + K * spread * FF ** 1.35 * 2.0).astype(np.int32)
    b = (0.30 + 0.62 * FF) * alpha
    plot(fr, Y.astype(np.int32), X, "·",
         tbl[np.clip((b * 16).astype(np.int32), 0, 16)])
    for k in range(1, 8):
        depth = k + (t * 1.6) % 1.0
        r = int(horizon + depth ** 1.55 * 1.02)
        if horizon < r < ROWS:
            fr.ch[r, 0:COLS:4] = ci("─")
            fr.fg[r, 0:COLS:4] = tbl[min(16, int((0.18 + 0.6 * depth / 9) * 16))]
    fr.ch[horizon, :] = ci("═")
    fr.fg[horizon, :] = tbl[7]


# ---------------------------------------------------------- geometric props --
def _eline(fr, r0, c0, r1, c1, col):
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    if dc > dr * 2.2:
        ch = "─"
    elif dr > dc * 2.2:
        ch = "│"
    elif (r1 - r0) * (c1 - c0) > 0:
        ch = "╲"
    else:
        ch = "╱"
    line(fr, r0, c0, r1, c1, col, ch=ch)


def _box(fr, geom, t):
    """Bounding dimensional box around the hero symbol, dotted wireframe."""
    r0, c0, w, h = geom
    x0, x1 = c0 - 3, c0 + w + 2
    y0, y1 = r0 - 2, r0 + h + 1
    for (r, cc0, cc1, ch) in ((y0, x0, x1, "─"), (y1, x0, x1, "─")):
        if 0 <= r < ROWS:
            fr.ch[r, max(0, cc0):cc1 + 1:2] = ci("─")
            fr.fg[r, max(0, cc0):cc1 + 1:2] = rc(R_TEAL, 0.80)
    for cn in (x0, x1):
        col = np.arange(max(0, y0), min(ROWS, y1 + 1))
        col = col[(col % 2) == 0]
        if 0 <= cn < COLS and len(col):
            fr.ch[col, cn] = ci("│")
            fr.fg[col, cn] = rc(R_TEAL, 0.80)
    for (r, cn, ch) in ((y0, x0, "┌"), (y0, x1, "┐"), (y1, x0, "└"), (y1, x1, "┘")):
        put(fr, r, cn, ch, rc(R_TEAL, 0.9))
        put(fr, r, cn + (1 if cn == x0 else -1), "◆", GOLD)
    # coordinate ticks + labels along the box
    for i in range(0, w + 1, 20):
        cc = c0 + i
        if 0 <= cc < COLS:
            put(fr, y0, cc, "┬", rc(R_TEAL, 0.6))
            text(fr, y0 + 1, cc + 1, f"{i:02d}", rc(R_TEAL, 0.5))
    for j in range(0, h + 1, 5):
        rr = r0 + j
        if 0 <= rr < ROWS:
            put(fr, rr, x0, "┤", rc(R_TEAL, 0.6))


def _cloud(fr, t, bright=1.0):
    """The point cloud sampling the lemniscate: points BECOME the symbol."""
    r0, c0, w, h = _G
    n = int(max(30, min(130, 22 + h * 2.6)))
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    den = 1.0 + np.sin(a) ** 2
    x = np.cos(a) / den
    y = np.sin(a) * np.cos(a) / den
    Xs, Ys, Bs = [], [], []
    for k, z in enumerate((-1.0, 0.0, 1.0)):
        wob = 0.018 + 0.030 * (k + 0.2)
        ph = t * 2.1 + k * 1.9
        xx = x * (1 + wob * np.sin(ph + a * 3.0))
        yy = y * (1 + wob * np.cos(ph + a * 3.0))
        Xs.append(c0 + (xx * 0.47 + 0.5) * w)
        Ys.append(r0 + (yy * 1.0728 + 0.5) * h)
        Bs.append(np.clip((0.55 + 0.45 * np.sin(t * 3.0 + a * 2.7 + k)) *
                          (0.75 + 0.25 * z) * bright, 0, 1))
    X = np.round(np.concatenate(Xs)).astype(np.int32)
    Y = np.round(np.concatenate(Ys)).astype(np.int32)
    B = np.clip(np.concatenate(Bs), 0, 1)
    COLS = (np.asarray(V, np.float32)[None, :] * (1 - B[:, None]) +
            np.asarray(PRIMARY, np.float32)[None, :] * B[:, None]).astype(np.uint8)
    plot(fr, Y, X, np.where(B > 0.42, ci("•"), ci("·")), COLS)


def _field(fr, t, bright=1.0):
    g = np.stack(np.meshgrid(np.linspace(-1, 1, 11), np.linspace(-1, 1, 5),
                             np.linspace(-1, 1, 11)), -1).reshape(-1, 3)
    P3 = _rot(g, t * 0.32, 0.30 + 0.16 * math.sin(t * 0.27))
    persp = 1.0 / (1.15 + 0.32 * P3[:, 2])
    X = np.round(96 + P3[:, 0] * 82 * persp).astype(np.int32)
    Y = np.round(22 + P3[:, 1] * 16.5 * persp).astype(np.int32)
    b = np.clip(0.62 - 0.34 * P3[:, 2], 0.10, 1.0) * 0.85 * bright
    COLS = (np.asarray(V, np.float32)[None, :] * (1 - b[:, None]) +
            np.asarray(TEAL, np.float32)[None, :] * b[:, None]).astype(np.uint8)
    plot(fr, Y, X, np.where(b > 0.62, ci("+"), ci("·")), COLS)


def _axes(fr, t):
    ay = t * 0.50 + 0.6
    cY, sY = math.cos(ay), math.sin(ay)
    for name, vec in (("X", (1.0, 0.0, 0.0)), ("Y", (0.0, 1.0, 0.0)),
                      ("Z", (0.0, 0.0, 1.0))):
        x, y, z = vec
        x1 = x * cY + z * sY
        ex = 96 + x1 * 58
        ey = 21 + y * 11.8
        line(fr, 21, 96, ey, ex, rc(R_GOLD, 0.55))
        put(fr, ey, ex, "◎", rc(R_GOLD, 0.95))
        text(fr, int(ey) - 1, int(ex) + 1, name, GOLD)


# ------------------------------------------------------------ hero symbol ----
_ip = 0.0
_G = (0, 0, 4, 1)


def _hero_geom(p):
    h = 13.0 + 31.0 * (p ** 1.45) + _ip * (0.5 + 1.5 * p)
    h = max(4, int(round(h)))
    w = max(3, int(round(h * 4.09)))
    return (int(round(23.0 - h / 2.0)), int(round(96 - w / 2.0)), w, h)


def _inf(fr, p, phase):
    r0, c0, w, h = _G
    if h < 12 and phase < 4:
        return
    m = infm()
    if phase == 1:
        lo, hi, gain = rc(R_TEAL, 0.42), None, 0.80
    elif phase == 2:
        lo, hi, gain = rc(R_TEAL, 0.55), None, 0.90
    elif phase == 3:
        lo, hi, gain = rc(R_PRIM, 0.60), rc(R_PW, 0.30), 1.05
    else:
        lo = rc(R_GW, 0.30 + 0.45 * p)
        hi = WHITE
        gain = 1.20 + 0.38 * p
        paint(fr, m, c0 - 3, r0 + 1, w, h, rc(R_TEAL, 0.30))
        paint(fr, m, c0 + 3, r0 - 1, w, h, rc(R_RED, 0.30))
    paint(fr, m, c0, r0, w, h, lo, hi, gain=gain)


def rl(tbl, fa):
    return tbl[np.clip((np.asarray(fa) * 16).astype(np.int32), 0, 16)]


def _plate(fr, r0, c0, r1, c1, title, tf, body_lines, bf=DIM, bg=None):
    fill(fr, r0, c0, r1, c1, " ", col=DIM, bg=PANEL if bg is None else bg)
    put(fr, r0, c0, "┤", tf)
    text(fr, r0, c0 + 2, title, tf)
    put(fr, r0, c1, "├", tf)
    rr = r0 + 2
    for s in body_lines:
        if rr > r1 - 1:
            break
        if isinstance(s, tuple):
            text(fr, rr, c0 + 2, s[0], s[1])
        else:
            text(fr, rr, c0 + 2, s, bf)
        rr += 1


def _rail(fr, r, tbl, a, step=3, c0=2, c1=190):
    if 0 <= r < ROWS:
        fr.ch[r, c0:c1:step] = ci("─")
        fr.fg[r, c0:c1:step] = rc(tbl, a)


def _vbar(fr, r_base, c0, vals, gap, tbl, lo_c=0.45):
    for i, v in enumerate(vals):
        h = int(round(float(v) * 8.5))
        if h <= 0:
            continue
        c = c0 + i * gap
        ys = np.arange(r_base - h, r_base)
        col = rc(tbl, min(1.0, lo_c + 0.055 * h))
        plot(fr, ys, np.full(ys.shape, c, np.int32), "█", col)
        put(fr, r_base - h - 1, c, "▔", rc(R_TW, 0.8))


# =========================================================== s07 HAPPY ======
def _sunburst(fr, cx, cy, t, p, n=36):
    for k in range(n):
        a = k * 2 * math.pi / n + t * (0.35 + 0.45 * p)
        wob = 0.5 + 0.5 * math.sin(t * 2.7 + k * 1.7)
        L = 6.0 + 20.0 * wob
        col = rc(R_GW, 0.42 + 0.48 * wob)
        line(fr, cy + L * 0.34 * math.sin(a), cx + L * 1.8 * math.cos(a) * 0.42,
             cy + L * 1.02 * math.sin(a), cx + L * 1.8 * math.cos(a), col,
             ch="·" if wob < 0.72 else "─")


def _smiley(fr, cx, cy, R, t, p):
    th = np.linspace(0, 2 * math.pi, 620)
    plot(fr, np.round(cy + R * np.sin(th)).astype(np.int32),
         np.round(cx + R * 1.8 * np.cos(th)).astype(np.int32), "█", rc(R_GW, 0.95))
    th2 = np.linspace(0, 2 * math.pi, 240)
    plot(fr, np.round(cy + (R - 1.4) * np.sin(th2)).astype(np.int32),
         np.round(cx + (R - 1.4) * 1.8 * np.cos(th2)).astype(np.int32), "▒", rc(R_GW, 0.75))
    for s in (-1, 1):
        ex = int(cx + s * R * 0.58)
        ey = int(cy - R * 0.30)
        for dr in (-2, -1, 0):
            put(fr, ey + dr, ex - 1, "█", WHITE)
            put(fr, ey + dr, ex, "█", WHITE)
            put(fr, ey + dr, ex + 1, "█", WHITE)
        put(fr, ey + 1, ex, "▄", rc(R_RW, 0.9))
    am = np.linspace(math.pi * 0.20, math.pi * 0.80, 44)
    plot(fr, np.round(cy + R * 0.06 + R * 0.52 * np.sin(am)).astype(np.int32),
         np.round(cx + R * 1.30 * np.cos(am)).astype(np.int32), "█", WHITE)
    plot(fr, np.round(cy + R * 0.02 + R * 0.52 * np.sin(am)).astype(np.int32),
         np.round(cx + R * 1.30 * np.cos(am)).astype(np.int32), "▀", rc(R_RW, 0.85))
    put(fr, int(cy + R * 0.30), int(cx - R * 1.10), "♥", rc(R_RED, 0.95))
    put(fr, int(cy + R * 0.30), int(cx + R * 1.10), "♥", rc(R_RED, 0.95))
    for k in range(16):
        a = t * 1.5 + k * math.pi / 8
        rr = R + 1.8
        put(fr, int(cy + rr * math.sin(a)), int(cx + rr * 1.8 * math.cos(a)),
            "✦" if k % 2 else "✧", rc(R_GW, 0.65 + 0.35 * math.sin(t * 4 + k)))


def _hearts(fr, t, p, n=22):
    for i in range(n):
        x = (_h01(i * 2.3) * 118 + 36 + math.sin(t * (0.7 + 0.3 * _h01(i * 3.1)) + i) * 5)
        y = ((_h01(i * 5.7) * 60) - t * (6 + 10 * p)) % 40 + 5
        col = rc(R_GW, 0.45 + 0.5 * _h01(i * 7.3))
        put(fr, y, x, "♥" if i % 3 else "♡", col)


def _scroll_col(fr, c0, w, t, p, side):
    spd = 2.4 + 3.0 * p
    base = t * spd
    for r in range(1, 43):
        ph = base + r * 0.13 + side * 3.3
        kk = int(ph)
        v = _h01(kk * 3.71 + r * 2.1 + side)
        ch = "0123456789ABCDEF"[int(v * 16)]
        hot = _h01((kk + r) * 4.3 + side)
        col = rc(R_TEAL, 0.30 + 0.45 * hot)
        if v > 0.90:
            ch, col = "#", rc(R_GW, 0.85)
        cc = c0 + int(_h01(kk * 2.7 + r * 1.3 + side) * (w - 1))
        put(fr, r, cc, ch, col)
        if r % 2 == 0:
            put(fr, r, c0 + int(_h01(kk * 5.1 + r + side) * (w - 1)), "·",
                rc(R_TEAL, 0.35))
        if int(ph) % 9 == 0:
            put(fr, r, c0 + w // 2, "│", rc(R_AMBER, 0.55))
    # vertical ruler
    for r in range(2, 43, 3):
        put(fr, r, c0 - 1 if side == 0 else c0 + w, "┤", rc(R_TEAL, 0.5))


def _bubbles(fr, t, p, n=30):
    k = np.arange(n, dtype=np.float64)
    X = np.clip((_h01(k * 1.7) * 116 + 38 + np.sin(t * 2 + k) * 4).astype(np.int32), 2, 189)
    Y = np.clip(((45 - (_h01(k * 3.1) * 40 + 3 - t * (5 + 9 * p))) % 44).astype(np.int32), 1, 42)
    plot(fr, Y, X, np.where((k % 4 == 0), ci("○"), ci("·")), rc(R_TW, 0.55))


# ------------------------------------------------------------------ draw -----
def _hud(fr, t, ctx, p):
    _rulers(fr, t)
    fill(fr, 42, 2, 43, 189, " ", col=DIM, bg=PANEL)
    put(fr, 0, 2, "┌", rc(R_GW, 0.7))
    put(fr, 0, 189, "┐", rc(R_GW, 0.7))
    put(fr, 44, 2, "└", rc(R_GW, 0.7))
    put(fr, 44, 189, "┘", rc(R_GW, 0.7))
    text(fr, 42, 4, "s07 HAPPY_EXEC // RUNTIME", rc(R_GW, 0.95))
    text(fr, 42, 40, f"T+{t:9.2f}", DIM)
    text(fr, 42, 54, f"BEAT {ctx.beat_i:03d}  BAR {ctx.bar_i:03d}", DIM)
    text(fr, 42, 82, "CHORUS 1 : HAPPY EXECUTION", rc(R_TEAL, 0.6))
    n = int(p * 30)
    text(fr, 43, 4, f"EXEC {'▓' * n}{'░' * (30 - n)}", rc(R_GW, 0.95))
    text(fr, 43, 38, f"RMS {ctx.rms * 100:4.1f}", rc(R_GOLD, 0.9))
    text(fr, 43, 116, f"PASS {int(p * 100):3d}%", rc(R_GW, 0.9))
    text(fr, 43, 152, "THREADS   8", rc(R_TEAL, 0.85))



# ---------------------------------------------------- full-screen motion ----
_WING = np.array([ci(ch) for ch in ("✦", "♥", "♪", "✧", "○", "◆", "■", "●",
                                    "▲", "▼", "★", "☆", "+", "×", "·")], np.int16)


def _wings(fr, t, p):
    """Radial burst of glyphs sweeping the whole stage out of the smiley."""
    n = 230
    k = np.arange(n)
    ang = _h01(k * 12.9898) * 2.0 * math.pi
    spd = 6.0 + 10.0 * _h01(k * 78.233)
    R = (spd * (t * 1.15) + _h01(k * 3.71) * 34.0) % 34.0 + 1.0
    x = 96.0 + np.cos(ang) * R * 2.15
    y = 19.0 + np.sin(ang) * R * 0.72
    ok = (x >= 1.0) & (x <= 190.0) & (y >= 1.0) & (y <= 43.0)
    if not ok.any():
        return
    ys = y[ok].astype(np.int32)
    xs = x[ok].astype(np.int32)
    g = _WING[k[ok].astype(np.int64) % len(_WING)]
    fade = np.clip(1.0 - R[ok] / 36.0, 0.12, 1.0) * (0.35 + 0.65 * p)
    lo = np.array(TEAL, np.float32)
    hi = np.array(GOLD, np.float32)
    cols = lo[None, :] * (1.0 - fade[:, None]) + hi[None, :] * fade[:, None]
    fr.ch[ys, xs] = g
    fr.fg[ys, xs] = cols.astype(np.uint8)


def _rings(fr, cx, cy, t, p, pulse):
    base = (t * 0.62) % 1.0
    for k in range(3):
        a = (base + k / 3.0) % 1.0
        R = 3.0 + a * 26.0
        f = 0.62 * (1.0 - a) * (0.55 + 0.75 * pulse) * (0.5 + 0.5 * p)
        if f < 0.05:
            continue
        col = rc(R_GW, f)
        for d in range(0, 96, 2):
            ang = d / 96.0 * 2.0 * math.pi
            x = int(round(cx + math.cos(ang) * R * 2.1))
            y = int(round(cy + math.sin(ang) * R * 0.68))
            if 1 <= x <= 190 and 1 <= y <= 43:
                put(fr, y, x, "·" if a > 0.45 else "○", col)


def _data_roll(fr, t, p):
    for cix, c in enumerate((64, 70, 76, 118, 124, 130)):
        sp = 0.45 + 0.28 * cix
        for r in range(6, 29):
            v = _h01((r * 31 + cix * 17) * 0.013 + t * sp)
            if v > 0.70:
                ch = "0123456789ABCDEF"[int(v * 16.0) % 16]
                put(fr, r, c, ch, rc(R_TEAL, 0.18 + 0.55 * v * (0.4 + 0.6 * p)))


def _marquee(fr, r, t, p, txt, col, speed):
    if not txt:
        return
    off = int((t * speed) % len(txt))
    row = (txt + txt)[off:off + fr.cols]
    for c, ch in enumerate(row):
        if ch != " ":
            put(fr, r, c, ch, col)


def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    lt = ctx.local
    p = fx.clamp(lt / ctx.dur)
    pulse = ctx.pulse
    _bg(fr, t)
    _wings(fr, t, p)
    _sunburst(fr, 96, 20, t, p)
    _data_roll(fr, t, p)
    _scroll_col(fr, 1, 13, t, p, 0)
    _scroll_col(fr, 177, 13, t, p, 1)
    _marquee(fr, 7, t, p,
             " HAPPY:// RUN HAPPINESS 100.0  EXECUTION STREAM OK  SMILE() -> OK  "
             "LOVE  JOY  LAUGH  ONLY YOU  ", rc(R_GW, 0.34), 9.0)
    _marquee(fr, 27, t, p,
             " > run existence --only-you ... rc=0    > smile() -> SMILE    "
             "> output LAUGH JOY LOVE    ", rc(R_TEAL, 0.28), -7.0)
    _hearts(fr, t, p)
    _bubbles(fr, t, p)
    _rings(fr, 96, 20, t, p, pulse)
    _smiley(fr, 96, 20 + 0.5 * math.sin(t * 5.2), 8.1 + 1.0 * pulse, t, p)
    # title
    band(fr, 0, 2)
    bigtext(fr, "EXECUTION", 0, 96, 8, rc(R_GW, 0.35), WHITE)
    fill(fr, 6, 40, 6, 152, " ", col=DIM, bg=PANEL)
    text(fr, 6, 42, "if I can make you happy, I will run the execution", rc(R_GW, 0.95))
    # left panels
    _plate(fr, 8, 17, 16, 62, "HAPPINESS", rc(R_GW, 0.95),
           [(f"  level  {min(9.99, p * 10.4):4.2f}", GOLD),
            ("  unit   HEART", DIM),
            ("  bound  NONE", DIM),
            (f"  hearts {int(p * 32):2d}/32", rc(R_RW, 0.9))])
    _plate(fr, 18, 17, 28, 62, "MOOD CORE", rc(R_GW, 0.95), [])
    for i, (lab, v) in enumerate((("joy", 1.0), ("love", 0.92), ("calm", 0.62),
                                  ("smile", p))):
        r = 20 + i * 2
        text(fr, r, 19, lab, rc(R_GW, 0.85))
        n = int(v * 24)
        fill(fr, r, 30, r, 54, "░", rc(R_LINE, 0.9), bg=VOID2)
        fill(fr, r, 30, r, 30 + n, "█", rc(R_GW, 0.75), bg=PANEL)
        text(fr, r + 1, 30, f"{int(v * 100):3d}%", rc(R_GOLD, 0.8))
    # right panels
    _plate(fr, 8, 132, 16, 175, "OUTPUT", rc(R_GW, 0.95),
           [(f"  happiness {min(100.0, p * 108):6.2f}", GOLD),
            (f"  smiles    {int(640 * p):5d}/s", DIM),
            ("  tears     0", rc(R_TEAL, 0.8)),
            ("  status    HAPPY", rc(R_GW, 0.9))])
    _plate(fr, 18, 132, 26, 175, "PROCESS", rc(R_GW, 0.95),
           [("  pid   0x5A17", rc(R_TEAL, 0.85)),
            (f"  cpu   {int(30 + 67 * p):3d} %", DIM),
            (f"  mem   {int(p * 4096):4d} MB", DIM),
            ("  rc    0", rc(R_GW, 0.85))])
    # execution log
    _plate(fr, 29, 17, 39, 175, "EXECUTION LOG", rc(R_GW, 0.95), [])
    lines = [("> exec happiness(target=you)", 0.05),
             ("  load memories ......... OK", 0.16),
             ("  raise reward .......... +1.0", 0.30),
             ("  suppress pain ......... 100%", 0.45),
             ("  execute() ............. RUNNING", 0.58),
             ("  output: SMILE", 0.72),
             ("  output: LAUGH  output: JOY", 0.84),
             ("> EXECUTION COMPLETE  rc=0", 0.94)]
    for i, (s, th) in enumerate(lines):
        if p >= th and i < 8:
            col = rc(R_GW, 0.95) if s.startswith(">") else rc(R_TEAL, 0.85)
            if "COMPLETE" in s:
                col = rc(R_RW, 0.95)
            text(fr, 30 + i, 19, s, col)
    # progress bar under the log
    w = 150
    n = int(p * w)
    fill(fr, 40, 20, 40, 20 + w, "░", rc(R_LINE, 0.85), bg=VOID2)
    if n:
        fill(fr, 40, 20, 40, 20 + n, "█", rc(R_GW, 0.95), bg=PANEL)
        put(fr, 40, 20 + n, "▌", WHITE)
    text(fr, 41, 20, f"execution {int(p * 100):3d}%   threads 8/8   rc=0   SMILE", rc(R_GW, 0.9))
    # sparkle frame
    k = np.arange(70, dtype=np.float64)
    X = np.clip((_h01(k * 1.9) * 150 + 20).astype(np.int32), 2, 189)
    Y = np.clip((_h01(k * 4.3) * 26 + 3).astype(np.int32), 2, 41)
    plot(fr, Y, X, "✦", rl(R_GW, 0.35 + 0.6 * _h01(k * 8.1 + t * 0.4)))
    _hud(fr, t, ctx, p)
    ctx.meta["bloom"] = 0.55 + 0.35 * p
    ctx.meta["flash"] = (0.03 + 0.06 * p) * pulse
    ctx.meta["flash_color"] = (255, 240, 200)
    ctx.set_glitch(0.02 + 0.02 * p)
    return fr
