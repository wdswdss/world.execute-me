"""s03_infinity - verse 1: geometry, the infinity symbol drawn as a program.

29.730 - 33.420  If I'm a set of points, then I will give you my dimension
33.422 - 37.110  If I'm a circle, then I will give you my circumference
37.115 - 40.800  If I'm a sine wave, then you can sit on all my tangents
40.807 - 44.490  If I approach infinity, then you can be my limitations

The first three lines each get their own geometric prop (point cloud, circle,
sine and its tangents) over a perspective floor and nested rotating wireframe
cubes.  The last line draws the lemniscate itself at a *fixed* size, with a
band of light running around the curve, so it reads as an infinite loop that
is already running rather than a shape zooming in from far away.
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

# The lemniscate keeps ONE size for the whole "approach infinity" line: it no
# longer zooms in from far away.  It sits in the middle of the stage and the
# light runs around the curve instead, so the drawing is animated while the
# geometry never moves.
_HERO_FIX = (11, 47, 98, 24)      # r0, c0, w, h


def _hero_geom(p):
    """Box of the hero symbol for phases 1-3 (the lemniscate itself is fixed)."""
    h = 13.0 + 31.0 * (p ** 1.45) + _ip * (0.5 + 1.5 * p)
    h = max(4, int(round(h)))
    w = max(3, int(round(h * 4.09)))
    return (int(round(23.0 - h / 2.0)), int(round(96 - w / 2.0)), w, h)


# ---- baked lemniscate: per-cell ink + position along the figure-eight ------
_INFC = None


def _inf_cells():
    """Bake the lemniscate at the fixed hero size: per-cell ink coverage and,
    for every cell, the position u in [0, 1) of the nearest point of the curve.

    u is what makes the symbol *run*: the light wave in _inf slides along it, so
    the picture animates while the geometry stays exactly where it is.
    """
    global _INFC
    if _INFC is not None:
        return _INFC
    r0, c0, w, h = _HERO_FIX
    m = np.asarray(infm(), np.float32)
    px = F.resize_mask(m, w * 10, h * 18)
    cov = np.clip(px.reshape(h, 18, w, 10).mean(axis=(1, 3)) * 1.45, 0.0, 1.0)
    n = 720
    a = np.arange(n + 1) / n * 2.0 * math.pi
    den = 1.0 + np.sin(a) ** 2
    ax = 420 * 0.5 + (np.cos(a) / den) * 420 * 0.47
    ay = 184 * 0.5 + (np.sin(a) * np.cos(a) / den) * 420 * 0.47
    rr = ((np.arange(h, dtype=np.float32) + 0.5) * (184.0 / h))[:, None, None]
    cc = ((np.arange(w, dtype=np.float32) + 0.5) * (420.0 / w))[None, :, None]
    d = (rr - ay[None, None, :]) ** 2 + (cc - ax[None, None, :]) ** 2
    u = np.argmin(d, axis=2).astype(np.float32) / n
    _INFC = (cov, u)
    return _INFC


def _paint_cells(fr, cov, col, r0, c0, min_v=0.045):
    """paint() for an already cell-quantised mask with a per-cell colour."""
    h, w = cov.shape
    ch = RAMP_IDX[np.clip((cov * 4.0 + 0.5).astype(np.int32), 0, 4)]
    m = cov >= min_v
    r0i, c0i = max(0, int(r0)), max(0, int(c0))
    r1i, c1i = min(ROWS, int(r0) + h), min(COLS, int(c0) + w)
    if r1i <= r0i or c1i <= c0i or not m.any():
        return
    src = (slice(r0i - r0, r1i - r0), slice(c0i - c0, c1i - c0))
    dst = (slice(r0i, r1i), slice(c0i, c1i))
    mm = m[src]
    sub = fr.ch[dst]
    sub[mm] = ch[src][mm]
    subf = fr.fg[dst]
    subf[mm] = col[src][mm]


def _inf(fr, lt, p, phase):
    """The lemniscate: fixed size, animated by a light wave running around it."""
    # the symbol must NOT appear before the "approach infinity" line
    if phase < 4:
        return
    r0, c0, w, h = _HERO_FIX
    pl = fx.clamp((lt - _LINES[3]) / (_LINES[4] - _LINES[3]))
    app = fx.smoothstep(pl, 0.0, 0.07)      # fade in at the fixed size
    if app <= 0.01:
        return
    m = infm()
    paint(fr, m, c0 - 3, r0 + 1, w, h, rc(R_TEAL, 0.30 * app))
    paint(fr, m, c0 + 3, r0 - 1, w, h, rc(R_RED, 0.30 * app))
    cov, u = _inf_cells()
    flow = np.mod(u - lt * 0.55, 1.0)        # position of the light on the curve
    band = (0.5 + 0.5 * np.cos(2.0 * np.pi * flow)) ** 2.0
    head = np.exp(-((np.mod(flow + 0.5, 1.0) - 0.5) / 0.06) ** 2)
    lo = np.asarray(rc(R_GW, 0.30 + 0.45 * p), np.float32)
    hi = np.asarray(WHITE, np.float32)
    v = cov[..., None]
    col = lo[None, None, :] * (1.0 - v) + hi[None, None, :] * v
    f = (0.52 + 0.60 * band + 0.55 * head)[..., None] * app
    _paint_cells(fr, cov, np.clip(col * f, 0.0, 255.0).astype(np.uint8), r0, c0)


# --------------------------------------------------------- phase 1: points ---
def _ph_points(fr, t, pl):
    _field(fr, t, 1.0)
    _box(fr, _G, t)
    _cloud(fr, t, 1.15)
    _axes(fr, t)
    band(fr, 0, 8)
    bigtext(fr, "DIMENSION", 1, 96, 8, rc(R_PRIM, 0.40), WHITE)
    ctext(fr, 9, "SET OF POINTS  ->  DIMENSION (3)   //   x  y  z", TEAL)
    # left panel: tally
    fill(fr, 11, 2, 17, 44, " ", col=DIM, bg=PANEL)
    text(fr, 12, 4, "POINT CLOUD", rc(R_TEAL, 0.7))
    text(fr, 13, 4, f"POINTS {125 + 330:04d}", TEAL)
    text(fr, 14, 4, "LATTICE 3 CUBES", DIM)
    text(fr, 15, 4, "LEMNISCATE 3 X 110", DIM)
    bf = int((pl * 30) % 30)
    text(fr, 16, 4, f"SAMPLE {'▓' * bf}{'░' * (30 - bf)}", rc(R_TEAL, 0.8))
    # right panel: axes
    fill(fr, 11, 146, 18, 190, " ", col=DIM, bg=PANEL)
    text(fr, 12, 148, "DIMENSION VECTOR", PRIMARY)
    for i, axn in enumerate("XYZ"):
        text(fr, 14 + i, 148, f"AXIS {axn}", DIM)
        e = [0.0, 0.0, 0.0]
        e[i] = 1.0
        text(fr, 14 + i, 156, f"[{e[0]:+.3f} {e[1]:+.3f} {e[2]:+.3f}]",
             rc(R_TEAL, 0.6))
    # probe point
    a = t * 1.3
    px = int(96 + 60 * math.cos(a))
    py = int(20 + 11 * math.sin(a * 1.7))
    for d in range(-3, 4):
        put(fr, py + d, px, "│", rc(R_GOLD, 0.75))
        put(fr, py, px + d, "─", rc(R_GOLD, 0.75))
    put(fr, py, px, "◉", WHITE)
    lab = f"P({math.cos(a):+.2f},{math.sin(a * 1.7):+.2f},{math.sin(a):+.2f})"
    fill(fr, py - 1, px + 6, py + 1, px + 7 + len(lab), " ", col=DIM, bg=PANEL)
    text(fr, py, px + 7, lab, GOLD)
    # bottom log
    fill(fr, 39, 2, 40, 60, " ", col=DIM, bg=PANEL)
    k0 = int(t * 6)
    for i in range(2):
        d = 3 - i
        text(fr, 39 + i, 4, f"> dim={d} basis={'xyz'[:d]} rank={(k0 + i) % 9} "
                            f"|{'#' * (d * 5)}|", rc(R_TEAL, 0.75 - 0.15 * i))
    # right side: rank readout
    fill(fr, 30, 152, 38, 190, " ", col=DIM, bg=PANEL)
    text(fr, 31, 154, "RANK NULLITY", PRIMARY)
    text(fr, 33, 154, f"rank = {(k0 % 3) + 1}", GOLD)
    text(fr, 34, 154, f"null = {3 - ((k0 % 3) + 1)}", TEAL)
    text(fr, 36, 154, f"det  = {(k0 % 9) - 4:+.2e}", DIM)


# --------------------------------------------------------- phase 2: circle ---
def _ph_circle(fr, t, pl):
    _field(fr, t, 0.55)
    _cloud(fr, t, 0.30)
    cx, cy = 96.0, 24.0
    R = 12.2 + 1.0 * math.sin(pl * math.pi)
    rx = R * 1.62
    sh = t * 0.5
    for k in range(1, 6):
        a = np.linspace(0, 2 * math.pi, 300) + sh * (0.3 + 0.12 * k)
        rr = R * k / 5.0
        plot(fr, np.round(cy + rr * np.sin(a)).astype(np.int32),
             np.round(cx + rr * 1.8 * np.cos(a)).astype(np.int32),
             "·", rc(R_TEAL, 0.34 + 0.06 * k))
    for n in range(24):
        a = n / 24 * 2 * math.pi + sh
        line(fr, cy, cx, cy + R * math.sin(a), cx + rx * math.cos(a),
             rc(R_TEAL, 0.42), ch="·")
    # body
    a = np.linspace(0, 2 * math.pi, 1400) + sh
    X = np.round(cx + rx * np.cos(a)).astype(np.int32)
    Y = np.round(cy + R * np.sin(a)).astype(np.int32)
    dc = -np.sin(a)
    dr = np.cos(a) / 1.8
    CH = np.where(np.abs(dr) > np.abs(dc) * 1.9, ci("│"),
                  np.where(np.abs(dc) > np.abs(dr) * 1.9, ci("─"),
                           np.where(dr * dc > 0, ci("╲"), ci("╱"))))
    plot(fr, Y, X, CH, rc(R_TW, 0.95))
    # travelling markers
    n = 36
    am = np.arange(n) / n * 2 * math.pi + sh * 2.4
    gold = np.asarray(GOLD, np.uint8)
    tealc = np.asarray(rc(R_TEAL, 0.8), np.uint8)
    plot(fr, np.round(cy + R * np.sin(am)).astype(np.int32),
         np.round(cx + rx * np.cos(am)).astype(np.int32),
         np.where(np.arange(n) % 3 == 0, ci("●"), ci("○")),
         np.where((np.arange(n) % 3 == 0)[:, None], gold, tealc))
    # inscribed square + circumscribed square
    for k in range(4):
        a0 = sh + k * math.pi / 2 + math.pi / 4
        a1 = a0 + math.pi / 2
        line(fr, cy + R * math.sin(a0), cx + rx * math.cos(a0),
             cy + R * math.sin(a1), cx + rx * math.cos(a1), rc(R_VIO, 0.85))
        line(fr, cy + R * 1.414 * math.sin(a0), cx + rx * 1.414 * math.cos(a0),
             cy + R * 1.414 * math.sin(a1), cx + rx * 1.414 * math.cos(a1),
             rc(R_VIO, 0.34))
    put(fr, int(cy), int(cx), "＋", GOLD)
    arad = t * 0.9 + math.pi * 0.25
    ex, ey = cx + rx * math.cos(arad), cy + R * math.sin(arad)
    line(fr, cy, cx, ey, ex, rc(R_GOLD, 0.9))
    put(fr, ey, ex, "◎", WHITE)
    lab = f" r={R:.1f} "
    midr, midc = int((cy + ey) / 2), int((cx + ex) / 2)
    fill(fr, midr - 1, midc - 1, midr + 1, midc + len(lab) + 1, " ", col=DIM, bg=PANEL)
    text(fr, midr, midc, lab, GOLD)
    # title
    band(fr, 0, 7)
    bigtext(fr, "CIRCUMFERENCE", 0, 96, 8, rc(R_TW, 0.30), WHITE)
    text(fr, 8, 66, "2 * PI * r", rc(R_TEAL, 0.6))
    # left formulas
    fill(fr, 11, 2, 20, 44, " ", col=DIM, bg=PANEL)
    circ = 2 * math.pi * R
    text(fr, 12, 4, "C  =  2 * PI * r", rc(R_TEAL, 0.85))
    text(fr, 14, 4, f"C  =  {circ:8.3f}  cells", TEAL)
    text(fr, 15, 4, f"r  =  {R:8.3f}  rows", GOLD)
    text(fr, 16, 4, f"PI =  {math.pi:8.5f}", DIM)
    text(fr, 18, 4, f"C/r = {circ / R:6.4f}", rc(R_VIO, 0.9))
    # right: perimeter walk
    fill(fr, 11, 146, 20, 190, " ", col=DIM, bg=PANEL)
    text(fr, 12, 148, "PERIMETER WALK", PRIMARY)
    text(fr, 14, 148, "SEGMENTS   1400", DIM)
    text(fr, 15, 148, "MARKERS      36", DIM)
    text(fr, 17, 148, f"ANGLE {pl * 360:6.1f} deg", GOLD)
    seg = int(pl * 38)
    text(fr, 18, 148, "▓" * seg + "░" * (38 - seg), rc(R_TEAL, 0.9))
    # unrolled circumference at the bottom
    uy = 39
    L = int(round(circ * 0.5))
    c0 = int(fx.clamp(96 - L / 2, 3, COLS - L - 3))
    for c in range(c0, c0 + L + 1):
        put(fr, uy, c, "─", rc(R_TEAL, 0.7))
    for i in range(0, L + 1, 5):
        c = c0 + i
        put(fr, uy, c, "┴", GOLD if i % 25 == 0 else rc(R_TEAL, 0.9))
        if i % 25 == 0:
            text(fr, uy - 1, c - 1, f"{int(i * 0.5)}", DIM)
    text(fr, uy - 1, c0, "UNROLLED   C = 2*PI*r", rc(R_TEAL, 0.75))
    text(fr, uy - 1, c0 + L - 11, f"{circ:.1f} cells", GOLD)
    # bottom left log
    fill(fr, 41, 2, 41, 58, " ", col=DIM, bg=PANEL)
    text(fr, 41, 4, f"> segments remaining {max(0, 1400 - int(pl * 1400)):05d}",
         rc(R_TEAL, 0.7))


# ----------------------------------------------------------- phase 3: sine ---
def assets_rms(t):
    try:
        from engine.assets import get_assets
        return float(get_assets().rms_at(t))
    except Exception:
        return 0.5


def _ph_sine(fr, t, pl):
    base = 27.0
    amp = 8.6
    ph = t * 2.4
    xs = np.arange(COLS)
    wv = 4 * math.pi / COLS
    yy = base - amp * np.sin(xs * wv + ph)
    fr.ch[10:45:2, 0:COLS:6] = ci("·")
    fr.fg[10:45:2, 0:COLS:6] = rc(R_GRID, 1.0)
    fr.ch[10:45:4, 0:COLS:3] = ci("·")
    fr.fg[10:45:4, 0:COLS:3] = rc(R_LINE, 0.8)
    for dp, tbl in ((1.7, R_PRIM), (-1.4, R_RED), (3.1, R_VIO)):
        yg = base - amp * 0.97 * np.sin(xs * wv + ph + dp)
        plot(fr, np.round(yg).astype(np.int32), xs, "─", rc(tbl, 0.45))
    for r in np.arange(int(base) + 1, ROWS):
        m = yy <= r
        if m.any():
            fr.ch[r, m] = ci("░")
            fr.fg[r, m] = rc(R_TEAL, 0.34)
    fr.ch[int(base), :] = ci("─")
    fr.fg[int(base), :] = rc(R_LINE, 0.95)
    for c in range(0, COLS, 12):
        put(fr, int(base), c, "┼", rc(R_TEAL, 0.9))
    text(fr, int(base) + 1, 2, "0", DIM)
    for i in (-2, -1, 1, 2):
        text(fr, int(base + i * 3), 2, f"{i:+d}", rc(R_DIMC, 0.9))
    Yc = np.round(yy).astype(np.int32)
    plot(fr, Yc, xs, "─", rc(R_TW, 0.9))
    plot(fr, Yc - 1, xs, "·", rc(R_TEAL, 0.7))
    # sliding tangent: a real segment whose length changes with the slope and
    # which is clipped to the wave field so it never crosses the panels/title.
    x0 = 26 + (t * 31.0) % 140
    a0 = x0 * wv + ph
    y0 = base - amp * math.sin(a0)
    slope = -amp * math.cos(a0) * wv
    TOP_R, BOT_R, L_C, R_C = 12.0, 34.0, 7.0, 185.0
    half = 34.0 / math.hypot(1.0, slope)          # shorter on steep slopes
    half *= 0.72 + 0.28 * float(np.clip(assets_rms(t), 0.0, 1.0))
    if abs(slope) > 1e-3:
        room = min((y0 - TOP_R) / abs(slope), (BOT_R - y0) / abs(slope))
        half = min(half, max(2.0, room))
    half = min(half, x0 - L_C, R_C - x0)
    half = max(2.0, half)
    lift = 0.55 * math.sin(t * 3.1)               # landing bob
    n = int(half)
    dcx = np.arange(-n, n + 1)
    ty = y0 + slope * dcx + lift
    _chs = ci("─") if abs(slope) < 0.24 else (ci("╲") if slope > 0 else ci("╱"))
    CH = np.full(len(dcx), _chs, dtype=np.int16)
    cols = np.tile(np.asarray(GOLD, np.uint8), (len(dcx), 1))
    cols[1::2] = np.asarray(AMBER, np.uint8)
    # dashes: skip every 5th cell so the segment does not read as a solid wall
    keep = (np.arange(len(dcx)) % 5) != 0
    tyi0 = np.round(ty).astype(np.int32)
    cxi0 = np.round(x0 + dcx).astype(np.int32)
    lab_top = (tyi0[0] + 5 if tyi0[0] < 16 else tyi0[0] - 3) - 2
    okc = keep.copy()
    for i in range(len(okc)):
        yy, xx = tyi0[i], cxi0[i]
        if yy >= 38:                       # bottom telemetry panels
            okc[i] = False
        if lab_top <= yy <= lab_top + 3 and 24 <= xx <= 48:
            okc[i] = False
    plot(fr, tyi0[okc], cxi0[okc], CH[okc], cols[okc])
    # end caps + contact shadow show the segment landing on the curve
    for sgn in (-1, 1):
        exx = int(round(x0 + sgn * n))
        eyy = int(round(y0 + slope * sgn * n + lift))
        put(fr, eyy, exx, "├" if sgn < 0 else "┤", rc(R_GOLD, 0.75))
        put(fr, eyy + 1, exx, "·", rc(R_GOLD, 0.45))
    tx, tyi = int(round(x0)), int(round(y0))
    for r in range(tyi + 1, min(int(base), tyi + 10)):
        put(fr, r, tx, "┊", rc(R_GOLD, 0.8))
    put(fr, tyi, tx, "◉", WHITE)
    lab = f" dy/dx = {math.cos(a0):+.3f} "
    lr = tyi + 5 if tyi < 16 else tyi - 3
    lc = int(fx.clamp(tx - 8, 2, COLS - len(lab) - 2))
    fill(fr, lr - 1, lc - 1, lr + 1, lc + len(lab) + 1, " ", col=DIM, bg=PANEL)
    text(fr, lr, lc, lab, GOLD)
    band(fr, 0, 8)
    bigtext(fr, "TANGENT", 0, 96, 9, rc(R_PW, 0.25), WHITE)
    text(fr, 9, 74, "sine wave / all tangents", rc(R_TEAL, 0.6))
    fill(fr, 38, 2, 42, 74, " ", col=DIM, bg=PANEL)
    text(fr, 39, 4, "x       sin(x)    cos(x)   ", DIM)
    k0 = int(t * 14)
    for i in range(4):
        xv = (k0 - i) * 0.25
        text(fr, 40 + i, 4, f"{xv:7.3f} {math.sin(xv):+8.4f} {math.cos(xv):+8.4f}",
             WHITE if i == 0 else rc(R_TEAL, 0.9))
    fill(fr, 38, 112, 42, 190, " ", col=DIM, bg=PANEL)
    text(fr, 39, 114, "SLOPE FIELD   dy/dx = cos(x)", PRIMARY)
    phx = np.arange(48)
    sv = np.cos(phx * 0.35 + ph)
    text(fr, 40, 114, "".join("╱" if v > 0 else "╲" for v in sv), rc(R_GOLD, 0.9))
    text(fr, 41, 114, "".join("+" if v > 0.6 else ("-" if v < -0.6 else "·")
                              for v in sv), rc(R_TEAL, 0.8))


# ---------------------------------------------------------- phase 4: limit ---
def _ph_limit(fr, t, pl):
    _cloud(fr, t, 0.26)
    lim_r = 33.0
    xs = np.arange(6, 186)
    f = (xs - 6) / 180.0
    yy = lim_r - 21.0 * np.exp(-f * 3.4)
    plot(fr, np.round(yy).astype(np.int32), xs, "·", rc(R_GOLD, 0.55))
    for k in range(0, len(xs), 2):
        put(fr, int(round(yy[k])) + 1, int(xs[k]), "─",
            rc(R_AMBER, 0.35 + 0.45 * f[k]))
    for c in range(0, COLS, 3):
        put(fr, int(lim_r), c, "┄", rc(R_RED, 0.9))
    text(fr, int(lim_r) - 1, 4, "LIMIT  y = L   (never reached)", RED)
    fill(fr, 11, 2, 19, 60, " ", col=DIM, bg=PANEL)
    text(fr, 12, 4, "APPROACH INFINITY", PRIMARY)
    text(fr, 14, 4, f"n     = 10^{pl * 9:.2f}", GOLD)
    text(fr, 15, 4, f"|f-L| = {10 ** (-pl * 8.0):10.3e}", TEAL)
    text(fr, 16, 4, f"x     = {pl * 100:8.2f}%", DIM)
    text(fr, 18, 4, "lim  f(x) = L", WHITE)
    fill(fr, 11, 128, 19, 190, " ", col=DIM, bg=PANEL)
    text(fr, 12, 130, "MY LIMITATIONS", RED)
    for i in range(5):
        text(fr, 13 + i, 130, f"{'#' * (i + 1)}{'·' * (5 - i)}  BOUND {i + 1}",
             rc(R_RED, 0.45 + 0.11 * i))
    text(fr, 18, 130, "count = 5 / 5  HIT", RED)
    band(fr, 35, 43)
    bigtext(fr, "LIMIT", 34, 96, 9, rc(R_GW, 0.45), WHITE)
    text(fr, 43, 4, f"f(x) = {1 - 1 / max(1.0, 10 ** (pl * 6.0)):.9f}", TEAL)
    text(fr, 43, 34, f"x -> 10^{pl * 6.0:.1f}", DIM)
    text(fr, 43, 120, "CEILING", DIM)
    pct = pl * 0.999 + 0.001
    w = 52
    n = int(pct * w)
    text(fr, 43, 128, "[" + "█" * n + "─" * (w - n) + "]", rc(R_RED, 0.8))
    text(fr, 43, 128 + w + 2, f"{pct * 100:5.1f}%", GOLD)


# -------------------------------------------------------------------- HUD ----
def _hud(fr, t, ctx, p, phase):
    names = {1: "POINTS", 2: "CIRCLE", 3: "SINE WAVE", 4: "INFINITY"}
    _rulers(fr, t)
    put(fr, 0, 2, "┌", rc(R_TEAL, 0.6))
    put(fr, 0, 189, "┐", rc(R_TEAL, 0.6))
    put(fr, 44, 2, "└", rc(R_TEAL, 0.6))
    put(fr, 44, 189, "┘", rc(R_TEAL, 0.6))
    text(fr, 42, 4, f"s03 GEOMETRY // {names.get(phase, '?')}", rc(R_TEAL, 0.75))
    text(fr, 42, 42, f"T+{t:9.2f}", DIM)
    text(fr, 42, 56, f"BEAT {ctx.beat_i:03d}  BAR {ctx.bar_i:03d}", DIM)
    text(fr, 42, 78, "VERSE 1 : GEOMETRY", rc(R_TEAL, 0.55))
    n = int(p * 20)
    text(fr, 43, 4, f"SCALE {'▓' * n}{'░' * (20 - n)}", rc(R_TEAL, 0.9))
    text(fr, 43, 30, f"RMS {ctx.rms * 100:4.1f}", rc(R_GOLD, 0.85))
    text(fr, 43, 44, f"OBJ {phase} / 4", DIM)


# ------------------------------------------------------------------- draw ----
def draw(ctx):
    global _ip
    fr = ctx.frame()
    t = ctx.t
    lt = ctx.local
    p = fx.clamp(lt / ctx.dur)
    _ip = ctx.pulse
    phase, pl = _phase(lt)
    global _G
    _G = _HERO_FIX if phase == 4 else _hero_geom(p)
    _bg(fr, t)
    if phase == 1:
        _floor(fr, t, 22, R_TEAL, 0.9)
    elif phase == 2:
        _floor(fr, t, 24, R_TEAL, 0.7)
    elif phase == 3:
        _floor(fr, t, 12, R_TEAL, 0.5)
    else:
        _floor(fr, t, 24, R_RED, 0.55)
    _inf(fr, lt, p, phase)
    if phase == 1:
        _ph_points(fr, t, pl)
    elif phase == 2:
        _ph_circle(fr, t, pl)
    elif phase == 3:
        _ph_sine(fr, t, pl)
    else:
        _ph_limit(fr, t, pl)
    _hud(fr, t, ctx, p, phase)
    ctx.meta["bloom"] = 0.42 + 0.30 * p
    ctx.set_glitch(0.03 + 0.16 * fx.smoothstep(lt, 11.2, ctx.dur) + 0.05 * ctx.pulse)
    if phase == 4:
        ctx.meta["flash"] = 0.08 * ctx.pulse
        ctx.meta["flash_color"] = GOLD
    return fr


def _phase(lt):
    for i in range(4):
        if lt < _LINES[i + 1]:
            return i + 1, fx.clamp((lt - _LINES[i]) / (_LINES[i + 1] - _LINES[i]))
    return 4, 1.0
