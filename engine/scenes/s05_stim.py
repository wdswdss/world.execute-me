"""s05_stim - stimulation.  A rotating wire globe wrapped in an electrode
array; two independent spike trains (A and B) fire on the beat and a
stimulus pulse runs down the electrodes into the globe.

59.270 - 62.962
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


# ============================================================ s05 STIMULI ===
# Pseudo-3D neural globe: depth-shaded wireframe sphere, spike trains wrapped
# round the latitudes, electrodes converging on the surface, bolts striking it,
# scanner rings and an orbiting particle swarm.  Panels stay peripheral.
_CX, _CY = 96.0, 22.0
_TAU = 2.0 * math.pi


def _orient_idx(dr, dc):
    """Glyph index for a single cell step, given row/col deltas."""
    a = np.abs(np.asarray(dr, np.float64))
    b = np.abs(np.asarray(dc, np.float64))
    return np.where(b > a * 1.9, ci("─"),
                    np.where(a > b * 1.9, ci("│"),
                             np.where(np.asarray(dr) * np.asarray(dc) > 0,
                                      ci("╲"), ci("╱"))))


def _deltas(X, Y):
    dX = np.empty_like(X)
    dY = np.empty_like(Y)
    dX[:-1] = X[1:] - X[:-1]
    dY[:-1] = Y[1:] - Y[:-1]
    dX[-1] = dX[-2] if len(dX) > 1 else 0.0
    dY[-1] = dY[-2] if len(dY) > 1 else 0.0
    return dX, dY


def _proj(P3, cx, cy, rx, ry, persp=0.15):
    k = 1.0 / (1.0 + persp * P3[:, 2])
    return cx + P3[:, 0] * rx * k, cy + P3[:, 1] * ry * k, P3[:, 2]


def _wire(fr, pts, cx, cy, rx, ry, ay, ax, tbl=R_TW, gain=1.0, step=1,
          light=True):
    """One 3-D curve: Lambert-lit on the near half, dim on the far half."""
    if step > 1:
        pts = pts[::step]
    P3 = _rot(pts, ay, ax)
    X, Y, Z = _proj(P3, cx, cy, rx, ry)
    dX, dY = _deltas(X, Y)
    CH = _orient_idx(dY, dX)
    near = Z < 0
    if light:
        lam = np.clip(-0.42 * P3[:, 0] - 0.52 * P3[:, 1] - 0.74 * P3[:, 2],
                      0.0, 1.0)
    else:
        lam = np.ones(len(P3))
    b = (0.10 + 0.90 * np.clip(-Z, 0.0, 1.0) ** 0.6) * (0.20 + 0.80 * lam)
    b = np.where(near, b * gain, 0.11 * gain)
    plot(fr, np.round(Y), np.round(X), CH,
         np.where(near[:, None], rl(tbl, b), rl(R_TEAL, b)))


_RAMP_SHADE = np.asarray(RAMP_IDX, np.int16)
_SYN = np.asarray([[0.34, -0.40], [-0.28, -0.52], [-0.55, 0.10], [0.10, 0.18],
                   [0.52, 0.22], [-0.18, 0.58], [0.30, -0.10], [-0.62, -0.18]])


def _sphere(fr, t, p, cx, cy, rx, ry, ay, ax):
    """Neural globe: continuous wireframe sphere (7 latitudes / 5 meridians,
    depth-dimmed on the back half), light-sided silhouette rim, synapse nodes."""
    for r in range(int(cy - ry) - 1, int(cy + ry) + 2):
        if r < 0 or r >= ROWS:
            continue
        dy = (r - cy) / ry
        span = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        a0 = max(0, int(round(cx - span)))
        b0 = min(COLS - 1, int(round(cx + span)))
        if b0 >= a0:
            fr.ch[r, a0:b0 + 1] = ci(" ")
            fr.bg[r, a0:b0 + 1] = VOID2
    a = np.linspace(0, _TAU, 210)
    for i in range(7):
        lat = math.radians(-62.0 + 124.0 * i / 6.0)
        cl, sl = math.cos(lat), math.sin(lat)
        _wire(fr, np.stack([np.cos(a) * cl, np.full_like(a, sl),
                            np.sin(a) * cl], 1),
              cx, cy, rx, ry, ay, ax, R_GW, 1.55, step=1)
    for j in range(5):
        lon = math.pi * j / 5.0 + t * 0.12
        _wire(fr, np.stack([np.cos(a) * math.cos(lon), np.sin(a),
                            np.cos(a) * math.sin(lon)], 1),
              cx, cy, rx, ry, ay, ax, R_PRIM, 1.20, step=1)
    # silhouette rim, brighter on the light side (upper-left)
    aa = np.linspace(0, _TAU, 150)
    riml = np.clip(-0.42 * np.cos(aa) - 0.55 * np.sin(aa), 0.0, 1.0)
    plot(fr, np.round(cy + ry * np.sin(aa)),
         np.round(cx + rx * np.cos(aa)),
         np.where(np.arange(150) % 2 == 0, ci("•"), ci("·")),
         rl(R_TW, 0.34 + 0.60 * riml))
    # synapse nodes on the front cap
    for (nx, ny) in _SYN:
        kk = math.sqrt(max(0.04, 1.0 - nx * nx - ny * ny))
        px, py, pz = _proj(_rot(np.asarray([[nx, ny, -kk]]), ay, ax),
                           cx, cy, rx, ry)
        if pz[0] < 0:
            put(fr, py[0], px[0], "◎", rc(R_GW, 0.95))


def _lat_spikes(fr, t, p, cx, cy, rx, ry, ay, ax):
    """Spike trains wrapped onto the globe: short bright latitude arcs."""
    for k in range(3):
        lat = math.radians(-52.0 + 52.0 * k + 9.0 * math.sin(t * 0.9 + k))
        cl, sl = math.cos(lat), math.sin(lat)
        a0 = t * (1.1 + 0.5 * k) + k * 2.1
        a = np.linspace(a0 - 0.72, a0 + 0.72, 40)
        base = np.stack([np.cos(a) * cl, np.full_like(a, sl),
                         np.sin(a) * cl], 1)
        V = _rot(base, ay, ax)
        X, Y, Z = _proj(V, cx, cy, rx, ry)
        m = Z < -0.05
        if not m.any():
            continue
        wave = np.clip(np.sin(a * 7.0 - t * (7.0 + 2.0 * k) + k * 2.2), 0, 1) ** 3
        dX, dY = _deltas(X, Y)
        plot(fr, np.round(Y[m]), np.round(X[m]), _orient_idx(dY[m], dX[m]),
             rl(R_GW, (0.35 + 0.60 * wave)[m]))
        sel = m & (wave > 0.55)
        if sel.any():
            X2, Y2, _ = _proj(_rot(base[sel] * 1.10, ay, ax), cx, cy, rx, ry)
            plot(fr, np.round(Y2), np.round(X2), "✦", rl(R_GW, 0.95))


def _orbiters(fr, t, p, cx, cy, rx, ry, ay):
    n = 30
    k = np.arange(n, dtype=np.float64)
    th = k * 2.399 + t * (0.9 + 0.7 * _h01(k * 1.7))
    ph = (k * 0.618 + t * 0.23) * math.pi
    r = 1.10 + 0.36 * _h01(k * 3.3)
    pts = np.stack([np.cos(th) * np.sin(ph) * r, np.cos(ph) * r,
                    np.sin(th) * np.sin(ph) * r], 1)
    P3 = _rot(pts, ay, 0.5 + 0.2 * math.sin(t * 0.5))
    X, Y, Z = _proj(P3, cx, cy, rx, ry, persp=0.22)
    b = np.clip(0.90 - 0.62 * Z, 0.12, 1.0)
    uu = (X - cx) / rx
    vv = (Y - cy) / ry
    m = (Z < 0.05) & (uu * uu + vv * vv > 1.10)
    plot(fr, np.round(Y[m]), np.round(X[m]),
         np.where(b[m] > 0.62, ci("•"), ci("·")), rl(R_GW, b[m]))


def _scan_ring(fr, t, p, cx, cy, rx, ry, seed, part):
    """Rotating scanner ring; called twice (far half, then near half)."""
    a = np.linspace(0, _TAU, 210)
    scale = 1.22 + 0.09 * math.sin(t * 1.6 + seed)
    pts = np.stack([np.cos(a) * scale, np.zeros_like(a), np.sin(a) * scale], 1)
    ay = t * 1.25 + seed
    ax = 0.72 + 0.34 * math.sin(t * 0.85 + seed)
    P3 = _rot(pts, ay, ax)
    X, Y, Z = _proj(P3, cx, cy, rx, ry, persp=0.10)
    lead = (a / _TAU - t * 0.50 + seed * 0.3) % 1.0
    b = 0.20 + 0.80 * np.exp(-lead * 4.0)
    far = Z >= 0
    m = far if part == "far" else ~far
    if not m.any():
        return
    dX, dY = _deltas(X, Y)
    tbl = R_VIO if part == "far" else R_GW
    vals = (b * 0.50) if part == "far" else (0.35 + 0.65 * b)
    plot(fr, np.round(Y[m]), np.round(X[m]), _orient_idx(dY[m], dX[m]),
         rl(tbl, vals[m]))
    if part == "near":
        j = int(np.argmax(b))
        if m[j]:
            put(fr, Y[j], X[j], "◉", rc(R_GW, 0.95))
            put(fr, Y[j] - 1, X[j], "▔", rc(R_GW, 0.60))


_PROBES = (
    # src_r, src_c, tip (x, y, z) on the unit sphere, label
    (13, 47, (-0.80, -0.52, -0.28), "E1"),
    (19, 47, (-0.90, 0.34, -0.18), "E2"),
    (27, 47, (-0.55, 0.76, -0.34), "E3"),
    (32, 47, (-0.72, -0.30, 0.56), "E4"),
    (13, 145, (0.80, -0.52, -0.28), "E5"),
    (19, 145, (0.90, 0.34, -0.18), "E6"),
    (27, 145, (0.55, 0.76, -0.34), "E7"),
    (32, 145, (0.74, -0.34, 0.56), "E8"),
)


def _needle(fr, r0, c0, r1, c1, tbl, a, step=2):
    n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
    f = np.linspace(0.0, 1.0, n)
    rr = np.round(r0 + (r1 - r0) * f)
    cc = np.round(c0 + (c1 - c0) * f)
    m = (np.arange(n) % step) == 0
    dr, dc = _deltas(cc, rr)
    plot(fr, rr[m], cc[m], _orient_idx(dr[m], dc[m]), rl(tbl, a))


def _bolt_to(fr, r0, c0, r1, c1, tbl, a, seed, t, head="⚡"):
    n = 10
    f = np.linspace(0.0, 1.0, n)
    rr = r0 + (r1 - r0) * f
    cc = c0 + (c1 - c0) * f
    amp = 2.2 * np.sin(f * math.pi)
    rr = rr + (_h01(np.arange(n) * 2.3 + seed + int(t * 14)) - 0.5) * amp
    cc = cc + (_h01(np.arange(n) * 3.1 + seed + 5 + int(t * 14)) - 0.5) * amp * 1.6
    dY, dX = _deltas(cc, rr)
    plot(fr, np.round(rr), np.round(cc), _orient_idx(dY, dX), rl(tbl, a))
    put(fr, rr[-1], cc[-1], head, rc(R_GW, 0.95))


def _impact(fr, t, tr, tc, seed):
    q = (t * 1.7 + seed * 0.13) % 1.0
    rad = 2.0 + q * 4.5
    th = np.linspace(0, _TAU, 48)
    plot(fr, np.round(tr + rad * np.sin(th)).astype(np.int32),
         np.round(tc + rad * 1.8 * np.cos(th)).astype(np.int32), "✧",
         rc(R_GW, 0.90 * (1 - q)))


def _electrodes(fr, t, p, cx, cy, rx, ry, ay, ax, pulse):
    for i, (sr, sc, tip, lab) in enumerate(_PROBES):
        tip3 = np.asarray(tip, np.float64)
        P3 = _rot(np.stack([tip3]), ay, ax)
        tx, ty, _ = _proj(P3, cx, cy, rx, ry)
        tr, tc = float(ty[0]), float(tx[0])
        # needle body: from the panel edge to just short of the surface
        back = 1.09 - 0.03 * pulse + 0.02 * math.sin(t * 2.1 + i)
        bx, by, _ = _proj(_rot(np.stack([tip3 * back]), ay, ax),
                          cx, cy, rx, ry)
        _needle(fr, sr, sc, by[0], bx[0], R_GW, 0.45 + 0.40 * p, step=2)
        put(fr, by[0], bx[0], "◉", rc(R_GW, 0.95))
        if i % 2 == 0:
            _bolt_to(fr, by[0], bx[0], tr, tc, R_RW, 0.55 + 0.30 * p, i * 3 + 1, t)
        if i % 3 == 0:
            _impact(fr, t, tr, tc, i + 1)
        mv = f"{40 + 60 * p * (1 + 0.4 * math.sin(t * 3 + i)):4.1f}mV"
        if sc < 96:
            text(fr, sr, sc + 2, lab, rc(R_GW, 0.9))
            text(fr, sr + 1, sc + 2, mv, rc(R_TEAL, 0.7))
        else:
            text(fr, sr, sc - 8, lab, rc(R_GW, 0.9))
            text(fr, sr + 1, sc - 8, mv, rc(R_TEAL, 0.7))


def _incoming(fr, t, p, cx, cy, rx, ry, ay, ax):
    """Bolts from outside the stage striking random points of the globe."""
    for i in range(3):
        s = int(t * 2.4) * 7 + i * 13
        sr = 3.0 if i % 2 == 0 else 43.0
        sc = 40.0 + _h01(s * 2.9) * 112.0
        th = _h01(s * 4.3) * _TAU
        ph = math.acos(1.0 - 1.25 * _h01(s * 5.1))
        tip = np.asarray([math.sin(ph) * math.cos(th), math.cos(ph),
                          math.sin(ph) * math.sin(th)], np.float64)
        P3 = _rot(np.stack([tip]), ay, ax)
        tx, ty, _ = _proj(P3, cx, cy, rx, ry)
        _bolt_to(fr, sr, sc, ty[0], tx[0], R_GW, 0.45 + 0.35 * p, i * 5 + 2, t)
        _impact(fr, t, ty[0], tx[0], i + 9)


def _lane(fr, r0, c0, w, t, seed, p, tbl, label):
    k = np.arange(w)
    v = np.zeros(w)
    dens = 0.05 + 0.20 * p
    hit = _h01((k + seed * 13) * 1.7) < dens
    v[hit] = 0.4 + 0.6 * _h01((k[hit] + seed) * 7.3)
    v = np.roll(v, int(t * (20 + 60 * p)) % w)
    for i in range(w):
        h = int(round(v[i] * 2))
        if h:
            ys = np.arange(r0 - h, r0)
            plot(fr, ys, np.full(ys.shape, c0 + i, np.int32), "│",
                 rc(tbl, 0.45 + 0.12 * h))
    fr.ch[r0, c0:c0 + w] = ci("─")
    fr.fg[r0, c0:c0 + w] = rc(R_LINE, 1.0)
    text(fr, r0 + 1, c0, label, rc(tbl, 0.8))

def _clear_disc(fr, cx, cy, rxc, ryc, lift=0.0):
    """Wipe a soft dark disc so the globe sits in a clean field."""
    r0 = max(0, int(cy - ryc) - 1)
    r1 = min(ROWS - 1, int(cy + ryc) + 1)
    c0 = max(0, int(cx - rxc) - 1)
    c1 = min(COLS - 1, int(cx + rxc) + 1)
    for r in range(r0, r1 + 1):
        dy = (r - cy) / ryc
        span = rxc * math.sqrt(max(0.0, 1.0 - dy * dy))
        a = max(0, int(round(cx - span)))
        b = min(COLS - 1, int(round(cx + span)))
        if b < a:
            continue
        fr.ch[r, a:b + 1] = ci(" ")
        if lift > 0:
            fr.bg[r, a:b + 1] = VOID2


def hline(fr, r, c0, c1, ch, col):
    fr.ch[r, c0:c1 + 1] = ci(ch)
    fr.fg[r, c0:c1 + 1] = np.asarray(col, np.uint8)


# --------------------------------------------------------------- chrome ------
def _hud(fr, t, ctx, p):
    _rulers(fr, t)
    fill(fr, 42, 2, 43, 189, " ", col=DIM, bg=PANEL)
    put(fr, 0, 2, "┌", rc(R_RED, 0.7))
    put(fr, 0, 189, "┐", rc(R_RED, 0.7))
    put(fr, 44, 2, "└", rc(R_RED, 0.7))
    put(fr, 44, 189, "┘", rc(R_RED, 0.7))
    text(fr, 42, 4, "s05 STIMULUS // NEURAL GLOBE", rc(R_RED, 0.95))
    text(fr, 42, 38, f"T+{t:9.2f}", DIM)
    text(fr, 42, 52, f"BEAT {ctx.beat_i:03d}  BAR {ctx.bar_i:03d}", DIM)
    text(fr, 42, 76, "CHORUS 1 : STIMULATIONS", rc(R_TEAL, 0.6))
    n = int(p * 30)
    text(fr, 43, 4, f"DRIVE {'▓' * n}{'░' * (30 - n)}", rc(R_GW, 0.95))
    text(fr, 43, 40, f"RMS {ctx.rms * 100:4.1f}", rc(R_GOLD, 0.9))
    text(fr, 43, 100, f"{int(30 + 970 * p):4d} mA", rc(R_RW, 0.9))
    text(fr, 43, 122, f"{int(12 + 380 * p):4d} Hz", rc(R_RW, 0.9))
    text(fr, 43, 150, f"DOSE {int(p * 100):3d}%", rc(R_GOLD, 0.9))


def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    lt = ctx.local
    p = fx.clamp(lt / ctx.dur)
    pulse = ctx.pulse
    cx = _CX
    cy = _CY + 0.8 * math.sin(t * 1.25)
    rx = (21.0 + 4.0 * p) * (1.0 + 0.035 * math.sin(t * 2.3))
    ry = rx / 1.9
    ay = t * 0.80
    ax = 0.56 + 0.14 * math.sin(t * 0.61)

    _bg(fr, t)
    _floor(fr, t, 33, R_RED, 0.30 + 0.34 * p)
    # clean dark field around the globe
    _clear_disc(fr, cx, cy, rx * 1.34, ry * 1.34, lift=1.0)
    # far targeting ring
    th = np.linspace(0, _TAU, 170)
    rad = 1.76 + 0.05 * math.sin(t * 1.7)
    plot(fr, np.round(cy + ry * rad * np.sin(th)).astype(np.int32),
         np.round(cx + rx * rad * np.cos(th)).astype(np.int32), "·",
         rc(R_VIO, 0.40))
    for k in range(4):
        ang = t * 0.7 + k * math.pi * 0.5
        put(fr, cy + ry * rad * math.sin(ang), cx + rx * rad * math.cos(ang),
            "▪", rc(R_VIO, 0.7))
    _orbiters(fr, t, p, cx, cy, rx, ry, ay)
    _incoming(fr, t, p, cx, cy, rx, ry, ay, ax)
    _sphere(fr, t, p, cx, cy, rx, ry, ay, ax)
    _lat_spikes(fr, t, p, cx, cy, rx, ry, ay, ax)
    _scan_ring(fr, t, p, cx, cy, rx, ry, 0.0, "near")

    # peripheral program-interface furniture
    band(fr, 0, 6)
    bigtext(fr, "STIMULATIONS", 0, 96, 8, rc(R_RW, 0.30), WHITE)
    fill(fr, 8, 60, 8, 132, " ", col=DIM, bg=PANEL)
    text(fr, 8, 62, "if I can, if I can, give you all the", rc(R_TEAL, 0.95))
    _plate(fr, 11, 2, 19, 45, "STIMULUS", rc(R_RW, 0.95),
           [(f"  drive  {int(30 + 970 * p):4d} mA   {int(12 + 380 * p):4d} Hz", GOLD),
            (f"  duty   {int(30 + 55 * p):3d} %", DIM),
            ("  target NEURAL GLOBE", TEAL),
            ("  sync   PHASE-CODE", DIM),
            ("  status OVERDRIVE" if p > 0.6 else "  status ESCALATING",
             rc(R_RW, 0.9))])
    _plate(fr, 11, 146, 19, 189, "NEURAL LINK", rc(R_GW, 0.95),
           [(f"  synapses {int(640 + 9400 * p):5d}", GOLD),
            (f"  latency {12.4 - 9.0 * p:5.2f} ms", DIM),
            (f"  gain    {1 + 7.4 * p:5.2f} dB", TEAL),
            (f"  nodes   {int(8 + 120 * p):3d} / 128", DIM),
            ("  risk    CRITICAL" if p > 0.7 else "  risk    RISING",
             rc(R_RW, 0.9))])
    _plate(fr, 23, 2, 31, 45, "ELECTRODE ARRAY", rc(R_GW, 0.95),
           [("  E1   E2   E3   E4", GOLD), ("  E5   E6   E7   E8", GOLD),
            (f"  imp   {int(60 + 340 * p):3d} uA", rc(R_RW, 0.85)),
            (f"  depth {0.30 + 0.55 * p:4.2f} mm", DIM),
            (f"  arcs  {int(6 + 40 * p * (1 + 0.3 * math.sin(t * 4))):3d} /s",
             rc(R_GW, 0.8))])
    _plate(fr, 23, 146, 31, 189, "GLOBE TELEMETRY", rc(R_TEAL, 0.95),
           [(f"  lat   {math.degrees(math.asin(max(-1.0, min(1.0, math.sin(t * 0.9))))):+7.2f}",
             GOLD),
            (f"  lon   {(t * 137.0) % 360.0:7.2f}", GOLD),
            (f"  radius {1.0 + 0.12 * math.sin(t * 1.3):5.3f} r", DIM),
            (f"  scan   {(t * 90.0) % 360.0:6.1f} deg", TEAL),
            ("  status LOCKED", rc(R_GW, 0.9))])
    # peripheral counters / logs
    text(fr, 21, 2, f"PULSE {int(t * 90) % 1000:03d}", rc(R_RED, 0.8))
    text(fr, 21, 168, f"AMP {70 + 30 * p:5.1f} V", rc(R_GW, 0.9))
    text(fr, 33, 2, "> neuron 0x%04X firing" % (int(t * 60) % 65536), rc(R_TEAL, 0.7))
    text(fr, 34, 2, "> axon refractory 12us", rc(R_TEAL, 0.55))
    text(fr, 33, 146, "> gate 7 of 8 open", rc(R_GW, 0.8))
    text(fr, 34, 146, "> synapse lock ON", rc(R_TEAL, 0.55))
    text(fr, 35, 74, "◉ TARGET LOCKED 8/8", rc(R_GW, 0.9))
    _lane(fr, 38, 4, 84, t, 1, p, R_RED, "SPIKE TRAIN  A")
    _lane(fr, 38, 100, 84, t, 3, p, R_TEAL, "SPIKE TRAIN  B")
    fill(fr, 40, 4, 40, 189, " ", col=DIM, bg=PANEL)
    text(fr, 40, 6, f"> charge {int(240 + 7600 * p):5d} uC  ..  discharge CRITICAL",
         rc(R_GOLD, 0.85))
    text(fr, 40, 62, f"ARC {int(4 + 96 * p) + int(6 * math.sin(t * 7)):4d}/s",
         rc(R_GW, 0.8))
    n = int(p * 22)
    text(fr, 40, 82, f"STIM {'▓' * n}{'░' * (22 - n)}", rc(R_GW, 0.95))
    text(fr, 40, 126, f"DOSE {int(p * 100):3d}%", rc(R_GW, 0.95))
    text(fr, 40, 148, f"COIL {38 + 62 * p:4.1f}C", rc(R_RW, 0.8))
    hline(fr, 41, 2, 189, "─", rc(R_RED, 0.30))
    _electrodes(fr, t, p, cx, cy, rx, ry, ay, ax, pulse)
    _hud(fr, t, ctx, p)
    ctx.meta["bloom"] = 0.52 + 0.33 * p
    ctx.meta["flash"] = 0.02 + 0.09 * p * pulse
    ctx.meta["flash_color"] = (255, 240, 255)
    ctx.set_glitch(0.02 + 0.05 * p)
    return fr
