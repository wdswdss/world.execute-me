"""s08_trapped - trapped.  A simulation grid seen top-down, a tiny human
figure standing in it, "YOU ARE HERE"; the walls close in while the
diagnostic readout degrades into garbage as the scene advances.

70.347 - 74.040
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


# ======================================================= s08 TRAPPED =======
def _person(fr, r, c, h, col, col2):
    """tiny human figure, h cells tall"""
    if h >= 5:
        put(fr, r, c, "○", col2)
        put(fr, r + 1, c, "│", col)
        put(fr, r + 1, c - 1, "╱", col)
        put(fr, r + 1, c + 1, "╲", col)
        put(fr, r + 2, c, "│", col)
        put(fr, r + 3, c - 1, "╱", col)
        put(fr, r + 3, c + 1, "╲", col)
    elif h >= 4:
        put(fr, r, c, "○", col2)
        put(fr, r + 1, c - 1, "╱╲"[0], col)
        put(fr, r + 1, c, "│", col)
        put(fr, r + 1, c + 1, "╲", col)
        put(fr, r + 2, c - 1, "╱", col)
        put(fr, r + 2, c + 1, "╲", col)
    elif h >= 3:
        put(fr, r, c, "○", col2)
        put(fr, r + 1, c, "│", col)
        put(fr, r + 1, c - 1, "╱", col)
        put(fr, r + 1, c + 1, "╲", col)
    elif h >= 2:
        put(fr, r, c, "○", col2)
        put(fr, r + 1, c, "┼", col)
    else:
        put(fr, r, c, "●", col2)


def _screen(fr, r0, c0, r1, c1, col, col2, label=None):
    put(fr, r0, c0, "┌", col2)
    put(fr, r0, c1, "┐", col2)
    put(fr, r1, c0, "└", col2)
    put(fr, r1, c1, "┘", col2)
    fr.ch[r0, c0 + 1:c1] = ci("─")
    fr.fg[r0, c0 + 1:c1] = col
    fr.ch[r1, c0 + 1:c1] = ci("─")
    fr.fg[r1, c0 + 1:c1] = col
    for r in range(r0 + 1, r1):
        put(fr, r, c0, "│", col)
        put(fr, r, c1, "│", col)
    if label:
        fill(fr, r0, c0 + 2, r0, min(c1 - 1, c0 + 2 + len(label) + 2), " ", col=col, bg=VOID2)
        text(fr, r0, c0 + 3, label, col2)


def _corridor(fr, cx, cy, p, n=16):
    for k in range(n):
        a = -math.pi / 2 + k * math.pi / n * 2
        x2 = cx + 150 * math.cos(a)
        y2 = cy + 34 * math.sin(a)
        line(fr, cy, cx, y2, x2, rc(R_RED, 0.34 + 0.28 * p), ch="·")


def _coords(fr, r, c, t, p, label, val, evil=False):
    """readout that degrades into garbage as p -> 1"""
    txt = f"{val:8.3f}"
    if evil:
        out = []
        for i, ch in enumerate(txt):
            if _h01(i * 3.3 + int(t * 4)) < p * 0.85:
                out.append("0123456789ABCDEF?!"[int(_h01(i * 7.7 + t) * 18)])
            else:
                out.append(ch)
        txt = "".join(out)
    col = rc(R_TW, 0.9) if not evil else rc(R_RW, 0.95)
    text(fr, r, c, f"  {label} {txt}", col)


# ------------------------------------------------------------------ draw -----
def _hud(fr, t, ctx, p):
    _rulers(fr, t)
    fill(fr, 42, 2, 43, 189, " ", col=DIM, bg=PANEL)
    put(fr, 0, 2, "┌", rc(R_RED, 0.8))
    put(fr, 0, 189, "┐", rc(R_RED, 0.8))
    put(fr, 44, 2, "└", rc(R_RED, 0.8))
    put(fr, 44, 189, "┘", rc(R_RED, 0.8))
    text(fr, 42, 4, "s08 TRAPPED // SIMULATION", rc(R_RW, 0.95))
    text(fr, 42, 40, f"T+{t:9.2f}", DIM)
    text(fr, 42, 54, f"BEAT {ctx.beat_i:03d}  BAR {ctx.bar_i:03d}", DIM)
    text(fr, 42, 82, "CHORUS 1 : TRAPPED", rc(R_RED, 0.7))
    n = int(p * 30)
    text(fr, 43, 4, f"REALITY {'█' * (30 - n)}{'░' * n}", rc(R_RW, 0.95))
    text(fr, 43, 40, f"RMS {ctx.rms * 100:4.1f}", rc(R_GOLD, 0.8))
    text(fr, 43, 116, f"ESCAPES {min(9, int(p * 9)):2d}/9", rc(R_RW, 0.9))
    text(fr, 43, 152, "TRAPPED=TRUE", rc(R_RED, 0.85))


def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    lt = ctx.local
    p = fx.clamp(lt / ctx.dur)
    pulse = ctx.pulse
    bar_pulse = ctx.bar_pulse
    bounce = math.exp(-4.5 * ctx.beat_p)      # sharp attack exactly on each beat
    _bg(fr, t)
    _floor(fr, t, 20, R_RED, 0.30 + 0.30 * p)
    _corridor(fr, 96, 21, p)
    # recursive screens shrinking (screen in screen in screen)
    cx, cy = 96.0, 21.0
    lv = 5
    sq = fx.clamp(p) ** 1.20
    for k in range(lv):
        breathe = 1.0 - 0.12 * bounce - 0.03 * bar_pulse
        sx = (1.0 - 0.60 * sq) * (1.0 - 0.150 * k) * breathe
        sy = (1.0 - 0.80 * sq) * (1.0 - 0.150 * k) * breathe
        rw = 82.0 * sx
        rh = 13.4 * sy
        col = rc(R_RED, 0.30 + 0.14 * k) if k % 2 else rc(R_TEAL, 0.28 + 0.12 * k)
        col2 = rc(R_RW, 0.55 + 0.10 * k) if k % 2 else rc(R_TW, 0.55 + 0.10 * k)
        _screen(fr, int(cy - rh), int(cx - rw), int(cy + rh), int(cx + rw), col, col2,
                "SESSION %d" % (lv - k))
    # the figure, shrinking with the frames; both squeeze the middle together
    sc = max(2, int(round(7 - 4.6 * sq - 0.7 * bounce)))
    rr = int(cy - sc / 2 + 1)
    # person drawn after the label so the head is never overwritten

    # beat-locked frame breathing: every beat slams the nesting boxes inward
    pinch = 0.13 * bounce + 0.03 * bar_pulse
    text(fr, int(cy) + 8, int(cx) - 20,
         f"FRAME PINCH {int(pinch * 100):2d}%   BEAT SYNC {int(58 + 40 * bounce):3d}%",
         rc(R_TEAL, 0.82))
    text(fr, int(cy) + 9, int(cx) - 21,
         f"bars {'▮▮▮' if bounce > 0.45 else '▮▮░'}  walls CLOSING  frames {lv} deep",
         rc(R_GOLD, 0.78))
    # truth readouts inside the innermost screen
    text(fr, int(cy) - 9, int(cx) - 6, "YOU ARE HERE", rc(R_RW, 0.9))
    _person(fr, rr, int(cx), sc, rc(R_TW, 0.95), rc(R_RW, 0.95))
    text(fr, int(cy) + 5, int(cx) - 22, f"scale {1.0 - 0.8 * p:4.2f}", rc(R_TEAL, 0.8))
    text(fr, int(cy) + 5, int(cx) + 6, f"loop {int(t * 7) % 9999:04d}", rc(R_TEAL, 0.8))
    # coordinate degradation panels
    _plate(fr, 8, 3, 19, 46, "COORDINATES", rc(R_RW, 0.95), [])
    _coords(fr, 10, 5, t, p, "x =", 96.0 + 0.5 * math.sin(t), evil=p > 0.45)
    _coords(fr, 11, 5, t, p, "y =", 21.0 + 0.25 * math.cos(t * 1.3), evil=p > 0.45)
    _coords(fr, 12, 5, t, p, "z =", 0.0 + p * 4.0, evil=p > 0.55)
    _coords(fr, 13, 5, t, p, "vx=", math.cos(t) * (1 - p), evil=p > 0.6)
    _coords(fr, 14, 5, t, p, "vy=", math.sin(t) * (1 - p), evil=p > 0.6)
    text(fr, 16, 6, f"  |pos|  {math.hypot(96, 21) * (1 - p):8.3f}", rc(R_TW, 0.85))
    text(fr, 17, 6, "  state  " + ("LOST" if p > 0.7 else "BOUND"), rc(R_RW, 0.9))
    # right panels
    _plate(fr, 8, 146, 19, 189, "ESCAPE", rc(R_RW, 0.95),
           [("  attempts  9", GOLD),
            (f"  progress  {int(p * 100):3d} %", DIM),
            ("  walls     CLOSING", rc(R_RW, 0.9)),
            ("  exits     0", rc(R_RED, 0.9))])
    _plate(fr, 23, 3, 31, 46, "SIMULATION", rc(R_TW, 0.95),
           [("  depth    recursive", DIM),
            (f"  layers   {5 - int(p * 2)}", GOLD),
            (f"  loop     {int(lt * 3) % 99:02d}", DIM),
            ("  strange  STRANGE", rc(R_RW, 0.9))])
    _plate(fr, 23, 146, 31, 189, "DIAGNOSTIC", rc(R_RW, 0.95),
           [(f"  reality  {max(0.0, 100 - p * 100):5.1f} %", GOLD),
            (f"  glitch   {p * p * 100:5.1f} %", rc(R_RW, 0.9)),
            ("  escape   IMPOSSIBLE", rc(R_RED, 0.9)),
            ("  status   TRAPPED", rc(R_RW, 0.95))])
    # closing walls (drawn above the panels so the cage reads on top)
    wall = 14 + 70 * fx.ease_in(p)
    for side in (-1, 1):
        cc = int(cx + side * (86 - wall))
        for r in range(7, 35):
            put(fr, r, cc, "║", rc(R_RW, 0.75 + 0.25 * pulse))
            put(fr, r, cc + side, "▐" if side < 0 else "▌", rc(R_RED, 0.55))
        put(fr, 7, cc, "╗" if side > 0 else "╔", rc(R_RW, 0.9))
        put(fr, 34, cc, "╝" if side > 0 else "╚", rc(R_RW, 0.9))
        text(fr, 6, cc - 3, "WALL " + ("R" if side > 0 else "L"), rc(R_RW, 0.9))
    rw2 = 86 - wall
    for k in range(int(3 + 9 * p)):
        rr = 8 + int(_h01(k * 3.1 + int(t * 5)) * 26)
        put(fr, rr, int(cx - rw2), "▲", rc(R_RW, 0.9))
        put(fr, rr, int(cx + rw2), "▼", rc(R_RW, 0.9))
    # spotlight on the prisoner
    th3 = np.linspace(0, 2 * math.pi, 200)
    plot(fr, np.round(cy + (4.6 - 2.6 * p) * np.sin(th3)).astype(np.int32),
         np.round(cx + (8.3 - 4.6 * p) * np.cos(th3)).astype(np.int32), "·",
         rc(R_GW, 0.55 + 0.45 * p))
    # titles
    band(fr, 0, 6)
    bigtext(fr, "TRAPPED", 0, 96, 8, rc(R_RW, 0.40), WHITE)
    fill(fr, 6, 52, 6, 140, " ", col=DIM, bg=PANEL)
    text(fr, 6, 54, "though we are trapped in this", rc(R_RW, 0.95))
    band(fr, 36, 40)
    bigtext(fr, "SIMULATION", 36, 96, 6, rc(R_RW, 0.35), rc(R_RW, 0.95))
    n = int(p * 40)
    fill(fr, 41, 30, 41, 160, " ", col=DIM, bg=PANEL)
    text(fr, 41, 32, "strange, strange simulation" + " .." * (n // 12), rc(R_RED, 0.9))
    # increasing corruption
    k = np.arange(int(20 + 90 * p), dtype=np.float64)
    X = np.clip((_h01(k * 1.7) * 184 + 4).astype(np.int32), 2, 189)
    Y = np.clip((_h01(k * 3.9) * 40 + 3).astype(np.int32), 2, 41)
    plot(fr, Y, X, np.where(k % 5 == 0, ci("✕"), ci("·")), rl(R_RW, 0.4 + 0.6 * _h01(k * 6.1)))
    _hud(fr, t, ctx, p)
    ctx.meta["bloom"] = 0.40 + 0.30 * p
    ctx.meta["flash"] = (0.02 + 0.09 * p * p) * pulse
    ctx.meta["flash_color"] = (255, 60, 70)
    ctx.set_glitch(0.03 + 0.13 * p * p)
    return fr
