"""s04_acdc - "switch my current, AC to DC".  A rectifier pretending to be a
love confession, drawn as three working panels:

    left     AC SOURCE      v(t) sine traced live, phase / amplitude readout
    middle   BRIDGE 4x DIODE  the two half-waves folded over into one
    right    DC OUTPUT      flat line + ripple %, "STATUS: AC LIVE" -> IDLE

Above them the state line counts up:
"AC >>> DC  [ ARMED ]" -> "[ SWITCHING ]" -> "[ RECTIFIED ]".

44.500 - 59.270
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
R_REDW = ramp(RED, WHITE)
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
    # clean coordinate ticks (no letter column: it read as noise on small screens)
    ph = int(t * 20) % 6
    tick = rc(R_TEAL, 0.42)
    for r in range(2, 45):
        ch = "·"
        if (r + ph) % 6 == 0:
            ch = "├"
        elif (r + ph) % 3 == 0:
            ch = "┊"
        fr.ch[r, 0] = ci(ch)
        fr.fg[r, 0] = tick
    for r in range(2, 45):
        ch = "·"
        if (r + ph) % 6 == 0:
            ch = "┤"
        elif (r + ph) % 3 == 0:
            ch = "┊"
        fr.ch[r, 191] = ci(ch)
        fr.fg[r, 191] = rc(R_TEAL, 0.30)


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



# =============================================================== s04 AC/DC ===
_S04_LINES = (0.0, 3.692, 7.385, 11.077, 14.770)
_PHASE_TAG = {1: "RECTIFY", 2: "DIZZY", 3: "A.D / B.C", 4: "UNITE"}

_ip = 0.0
_T = 0.0


def _phase(lt):
    for i in range(4):
        if lt < _S04_LINES[i + 1]:
            return i + 1, fx.clamp((lt - _S04_LINES[i]) /
                                   (_S04_LINES[i + 1] - _S04_LINES[i]))
    return 4, 1.0


def _rail(fr, r, tbl, a, step=3, c0=2, c1=190):
    if 0 <= r < ROWS:
        fr.ch[r, c0:c1:step] = ci("─")
        fr.fg[r, c0:c1:step] = rc(tbl, a)


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


# ------------------------------------------------------------ background ------
def _wire(fr, t):
    for k, (r, a) in enumerate(((8, 0.42), (21, 0.30), (34, 0.36))):
        _rail(fr, r, R_TEAL, a, 3)
    for c in range(5, 190, 9):
        r0 = 8 + (c // 9 % 3) * 13
        r1 = min(34, r0 + 6 + (c // 9 % 4) * 2)
        fr.ch[r0:r1, c] = ci("│")
        fr.fg[r0:r1, c] = rc(R_LINE, 0.42)
        put(fr, r1, c, "┴", rc(R_TEAL, 0.55))
    k = np.arange(46, dtype=np.float64)
    X = ((_h01(k + 3) * COLS + t * (6 + (k % 3) * 3)) % COLS).astype(np.int32)
    Y = ((_h01(k * 2.3 + 1) * ROWS + t * 1.7) % ROWS).astype(np.int32)
    plot(fr, Y, X, "·", rc(R_PRIM, 0.50))


def _scope_grid(fr):
    for r in range(9, 36, 4):
        fr.ch[r, 2:190:2] = ci("·")
        fr.fg[r, 2:190:2] = rc(R_LINE, 0.55)
    for c in range(6, 190, 8):
        fr.ch[9:36, c] = ci("·")
        fr.fg[9:36, c] = rc(R_GRID, 1.0)


def _flow(fr, t, r0=23, r1=32):
    rows = np.arange(r0, r1)
    k = np.arange(520, dtype=np.float64)
    X = ((_h01(k * 1.3) * COLS + t * (14 + (k % 7) * 3)) % COLS).astype(np.int32)
    Y = (r0 + (_h01(k * 2.7) * (r1 - r0))).astype(np.int32)
    b = 0.45 + 0.5 * _h01(k * 5.1)
    CH = np.where(k % 5 == 0, ci("→"), ci("·"))
    COLS2 = (np.asarray(V, np.float32)[None, :] * (1 - b[:, None]) +
             np.asarray(TEAL, np.float32)[None, :] * b[:, None]).astype(np.uint8)
    plot(fr, Y, X, CH, np.clip(COLS2, 0, 255))


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


# ------------------------------------------------------- phase 1: rectify ----
def _ph_rect(fr, t, pl):
    cy, amp = 21.0, 8.5
    cy_i = int(round(cy))
    xs = np.arange(2, 190)
    wv = 3.0 * 2.0 * math.pi / 188.0
    ph = t * 2.6
    s = np.sin(xs * wv - ph)
    m = fx.smoothstep(pl, 0.06, 0.72)
    blend = (1 - m) * s + m * np.abs(s)
    ys = cy - amp * blend
    sr = np.sign(blend)
    _scope_grid(fr)
    # bar fill between centre rail and the curve
    for k in range(1, int(amp) + 1):
        mk = np.abs(blend) * amp >= k
        fk = 0.28 + 0.030 * k
        plot(fr, (cy - sr * k)[mk], xs[mk], "░" if k % 3 else "▒",
             rc(R_TEAL, fk))
    # reference AC ghost
    yg = cy - amp * np.sin(xs * wv - ph)
    plot(fr, np.round(yg).astype(np.int32), xs, "·", rc(R_LINE, 0.8))
    # DC level line
    dc = cy - amp * 0.6366 * m
    if m > 0.02:
        r = int(round(dc))
        fr.ch[r, 2:190:2] = ci("═")
        fr.fg[r, 2:190:2] = rc(R_GW, 0.55 + 0.3 * m)
        fr.ch[r, 3:190:2] = ci("═")
        fr.fg[r, 3:190:2] = rc(R_GW, 0.55 + 0.3 * m)
    text(fr, 22, 46, "DC = 2/pi * Vp", rc(R_GOLD, 0.9))
    # curve
    Y = np.round(ys).astype(np.int32)
    plot(fr, Y, xs, "▀", rc(R_PW, 0.95))
    plot(fr, np.clip(Y - sr * 1, 0, ROWS - 1), xs, "▄", rc(R_PRIM, 0.55))
    _flow(fr, t, 24, 33)
    xa = np.linspace(0, 2 * math.pi * 3, 9)
    _vbar(fr, 33, 8, np.abs(np.sin(t * 2.6 + xa)) * (0.35 + 0.65 * (1 - m)),
          3, R_RED, 0.30)
    _vbar(fr, 33, 152, np.full(9, 0.28 + 0.62 * m), 4, R_GW, 0.40)
    text(fr, 34, 6, "AC INPUT  V(t)", rc(R_RED, 0.7))
    text(fr, 34, 149, "DC OUTPUT  V", rc(R_GOLD, 0.85))
    fr.ch[cy_i, 2:190:2] = ci("─")
    fr.fg[cy_i, 2:190:2] = rc(R_LINE, 0.9)
    text(fr, cy_i, 2, "0V", DIM)
    # scan cursor
    cx = int(2 + (t * 46.0) % 186)
    line(fr, 10, cx, 33, cx, rc(R_GOLD, 0.55), ch="╎")
    put(fr, 10, cx, "▾", GOLD)
    if 0 <= int(round(ys[min(cx - 2, len(ys) - 1)])) < ROWS:
        put(fr, int(round(ys[min(cx - 2, len(ys) - 1)])), cx, "◉", WHITE)
    band(fr, 0, 8)
    bigtext(fr, "AC / DC", 0, 96, 9, rc(R_PRIM, 0.35), WHITE)
    if m < 0.02:
        sw_txt, sw_col = "SWITCH MY CURRENT  //  AC  >>>  DC   [ ARMED ]", rc(R_TEAL, 0.85)
    elif m < 0.98:
        sw_txt, sw_col = "SWITCH MY CURRENT  //  AC  >>>  DC   [ SWITCHING ]", rc(R_GOLD, 0.95)
    else:
        sw_txt, sw_col = "SWITCH MY CURRENT  //  AC  >>>  DC   [ RECTIFIED ]", rc(R_GW, 0.95)
    text(fr, 9, 52, sw_txt, sw_col)
    nsw = int(m * 28)
    text(fr, 10, 52, "CONVERSION " + "▓" * nsw + "░" * (28 - nsw) + f" {int(m * 100):3d}%",
         rc(R_GOLD if m < 0.98 else R_GW, 0.9))
    ac_state = "AC LIVE" if m < 0.02 else ("FADING" if m < 0.98 else "OFFLINE")
    fill(fr, 11, 3, 19, 46, " ", P.C["void"])
    fill(fr, 11, 145, 19, 189, " ", P.C["void"])
    _plate(fr, 11, 3, 19, 46, "AC SOURCE", rc(R_TEAL, 0.9),
           [("  ~ 220 V   50 Hz", GOLD),
            (f"  phase {math.degrees((t * 2.6) % (2 * math.pi)):6.1f} deg", DIM),
            (f"  V(t)  {220 * math.sin(t * 2.6) * (1 - m):+7.1f} V", TEAL),
            (f"  STATUS  {ac_state}", rc(R_TEAL, 0.7))])
    dc_state = "IDLE" if m < 0.02 else ("CHARGING" if m < 0.98 else "RECTIFIED")
    _plate(fr, 11, 145, 19, 189, "DC OUTPUT", rc(R_GOLD, 0.95),
           [(f"  == {311 * m:6.1f} V   RIPPLE", GOLD),
            (f"  ripple {4.2 * (1 - m):5.2f} %", DIM),
            (f"  I(t)  {4.2 * m + 0.4:6.2f} A", TEAL),
            (f"  STATUS  {dc_state}", rc(R_GOLD, 0.8))])
    # bridge rectifier glyph
    bx, by = 96, 30
    put(fr, by, bx, "◇", rc(R_TEAL, 0.9))
    for dx, dy, ch in ((-5, 0, "◀"), (5, 0, "▶"), (0, -3, "▲"), (0, 3, "▼")):
        put(fr, by + dy, bx + dx, ch, GOLD)
    line(fr, by - 2, bx, by - 1, bx, rc(R_TEAL, 0.7), ch="│")
    line(fr, by + 1, bx, by + 2, bx, rc(R_TEAL, 0.7), ch="│")
    text(fr, by + 5, bx - 9, "BRIDGE 4x DIODE", rc(R_TEAL, 0.6))
    # duty readouts
    text(fr, 40, 4, f"f = 50.0 Hz   T = 20.00 ms   duty {(0.5 + 0.5 * m) * 100:5.1f}%",
         rc(R_TEAL, 0.75))
    text(fr, 40, 118, f"Vdc/Vp = {0.6366 * m:6.4f}", rc(R_GOLD, 0.8))
    text(fr, 41, 4, "> rectifier bridge  ..  ONLINE", rc(R_TEAL, 0.6))
    text(fr, 41, 118, f"> smooth capacitor  ..  {int(100 * m):3d}%", rc(R_TEAL, 0.6))


# -------------------------------------------------------- phase 2: dizzy ----
def _spiral(fr, t, pl, cx, cy, rx, ry, turns, col, ch="·", a0=0.0, n=1200):
    th = np.linspace(0, turns * 2 * math.pi, n) + a0
    rr = th / (turns * 2 * math.pi)
    Y = np.round(cy + ry * rr * np.sin(th)).astype(np.int32)
    X = np.round(cx + rx * rr * np.cos(th)).astype(np.int32)
    plot(fr, Y, X, ch, col)


def _warp(fr, t, pl, r0=5, r1=38, c0=3, c1=151):
    rr = np.arange(r0, r1)
    off = (np.sin(t * 5.5 + rr * 0.50) * (1.2 + 5.0 * pl) +
           np.sin(t * 15.0 + rr * 2.3) * 1.4 * pl)
    for i in range(len(rr)):
        k = int(round(off[i]))
        if k:
            r = int(rr[i])
            fr.ch[r, c0:c1] = np.roll(fr.ch[r, c0:c1], k)
            fr.fg[r, c0:c1] = np.roll(fr.fg[r, c0:c1], k, axis=0)


def _ph_dizzy(fr, t, pl):
    cx, cy = 96.0, 24.0
    a0 = t * 2.2
    for dp, tb in ((0.0, R_TEAL), (0.16, R_RED), (-0.16, R_VIO)):
        _spiral(fr, t, pl, cx, cy, 60.0, 17.0, 5.0, rc(tb, 0.55), "·", a0 + dp)
    _spiral(fr, t, pl, cx, cy, 54.0, 15.0, 3.4, rc(R_TW, 0.75), "─", -a0 * 1.6)
    # ---- eye ----
    rx, ry = 74.0, 12.0
    dx = np.linspace(-1, 1, 1100)
    lid = ry * (1 - dx * dx) ** 0.85
    XX = np.round(cx + dx * rx).astype(np.int32)
    plot(fr, np.round(cy - lid).astype(np.int32), XX, "▀", rc(R_PW, 0.95))
    plot(fr, np.round(cy + lid).astype(np.int32), XX, "▄", rc(R_PW, 0.95))
    plot(fr, np.round(cy - lid - 1).astype(np.int32), XX, "·", rc(R_PRIM, 0.75))
    plot(fr, np.round(cy + lid + 1).astype(np.int32), XX, "·", rc(R_PRIM, 0.75))
    for j, (ir, ch, tb, br) in enumerate(((10.5, "●", R_TEAL, 0.85),
                                          (7.6, "○", R_DIMC, 1.0),
                                          (5.0, "●", R_GOLD, 0.8))):
        th = np.linspace(0, 2 * math.pi, 360) + t * (0.9 + 0.3 * j)
        plot(fr, np.round(cy + ir * np.sin(th)).astype(np.int32),
             np.round(cx + ir * 1.8 * np.cos(th)).astype(np.int32), ch, rc(tb, br))
    for k in range(16):
        a = t * 1.4 + k * math.pi / 8
        line(fr, cy, cx, cy + 10.0 * math.sin(a), cx + 18.0 * math.cos(a),
             rc(R_LINE, 0.9), ch="·")
    put(fr, int(cy), int(cx), "◉", WHITE)
    put(fr, int(cy) - 1, int(cx) - 1, "█", rc(R_TEAL, 0.8))
    put(fr, int(cy) - 1, int(cx) + 1, "█", rc(R_TEAL, 0.8))
    text(fr, int(cy) + 4, int(cx) - 6, "◉ pupil", rc(R_TEAL, 0.8))
    # spinning markers ring
    for k in range(12):
        a = a0 * 2.4 + k * math.pi / 6
        rr = 17.0
        put(fr, int(cy + rr * math.sin(a)), int(cx + rr * 1.8 * math.cos(a)),
            "▲▼◀▶"[k % 4], rc(R_GOLD, 0.85))
    # ---- warp the eye zone only ----
    _warp(fr, t, pl, 12, 37, 4, 152)
    # ---- titles drawn after the warp ----
    bigtext(fr, "DIZZY", 4, 90 + int(7 * math.sin(t * 3.1)), 10,
            rc(R_RED, 0.40), rc(R_RED, 0.7), gain=0.75)
    bigtext(fr, "DIZZY", 3, 102, 10, rc(R_PW, 0.30), WHITE)
    text(fr, 30, 60, "so dizzy, so dizzy, so dizzy",
         rc(R_TEAL, 0.9))
    # panels below the eye
    _plate(fr, 38, 3, 41, 56, "VISION", rc(R_RED, 0.95),
           [(f"  blur 92%   rot {int(t * 398) % 360:3d}   ghosts {1 + int(pl * 3)}",
             GOLD)])
    _plate(fr, 38, 130, 41, 189, "VESTIBULAR", rc(R_VIO, 0.95),
           [(f"  gyro OUT OF RANGE   spin {int(360 * pl):3d} deg", TEAL)])
    txt = "SO DIZZY  //  "
    n = len(txt)
    off = int(t * 18) % n
    text(fr, 41, 60, (txt * 6)[off:off + 68], rc(R_VIO, 0.9))


# ------------------------------------------------------ phase 3: A.D / B.C ---
def _portal(fr, t, cx, cy, rx, ry, col, lab, lab_col, rate=1.0):
    for j, a in ((1.0, 0.85), (0.80, 0.6), (0.58, 0.45), (0.36, 0.32)):
        th = np.linspace(0, 2 * math.pi, 300)
        plot(fr, np.round(cy + ry * j * np.sin(th)).astype(np.int32),
             np.round(cx + rx * j * np.cos(th)).astype(np.int32),
             "·" if j < 1.0 else "▫", rc(R_TEAL, a))
    for j in range(12):
        a = t * (1.6 * rate) + j * math.pi / 6
        line(fr, cy, cx, cy + ry * math.sin(a), cx + rx * math.cos(a),
             rc(R_TEAL, 0.55), ch="·")
    put(fr, int(cy - ry), int(cx), "◆", col)
    put(fr, int(cy + ry), int(cx), "◆", col)
    put(fr, int(cy), int(cx - rx), "◆", col)
    put(fr, int(cy), int(cx + rx), "◆", col)
    text(fr, int(cy - ry) - 2, int(cx - len(lab) / 2), lab, lab_col)


def _ph_time(fr, t, pl):
    cy = 21
    _portal(fr, t, 34.0, cy, 29.0, 15.5, GOLD, "   A.D   ", rc(R_GOLD, 0.95), 1.0)
    _portal(fr, t, 158.0, cy, 29.0, 15.5, RED, "   B.C   ", rc(R_RED, 0.95), 1.4)
    yr_f = 2025 + int(pl * 6900)
    yr_b = 1205 - int(pl * 1200)
    for (cc0, cc1) in ((14, 54), (132, 172)):
        fr.fill_rect(13, cc0, 24, cc1, " ", bg=P.C["void"])
    for (val, cc, c_lo, c_hi) in (
            (f"{yr_f:04d}", 34, rc(R_GW, 0.95), WHITE),
            (f"{max(1, yr_b):04d}", 152, rc(R_REDW, 0.90), rc(R_RED, 1.0))):
        tm = F.text_mask(val, 8 * 18, bold=True)
        w = max(1, int(round(tm.shape[1] / 10.0)))
        fr.paint_mask(tm, int(round(cc - w / 2)), 14, w,
                      max(1, int(round(tm.shape[0] / 18.0))),
                      ramp=P.RAMP_BLOCK, fg=c_lo, fg2=c_hi,
                      bg=P.C["void"], gain=2.8)
    text(fr, 24, 26, f"{yr_f}  YEARS  ASCENDING", rc(R_GOLD, 0.85))
    text(fr, 24, 138, f"{max(1, yr_b)}  YEARS  DESCENDING", rc(R_RED, 0.85))
    # time axis between the portals
    fr.ch[cy, 64:130:2] = ci("═")
    fr.fg[cy, 64:130:2] = rc(R_VIO, 0.9)
    for i, c in enumerate(range(64, 131, 8)):
        put(fr, cy, c, "╪", rc(R_VIO, 1.0))
        put(fr, cy - 1, c, "│", rc(R_VIO, 0.7))
        put(fr, cy + 1, c, "│", rc(R_VIO, 0.7))
        if i % 2 == 0:
            text(fr, cy - 2, c - 2, f"{abs(8 - i)}", rc(R_VIO, 0.75))
    # travelling packet
    pos = 0.5 - 0.5 * math.cos(pl * math.pi * 2.2)
    px = 96 + 60 * (1 - 2 * pos)
    for k in range(9):
        xx = int(px + (28 if pos < 0.5 else -28) * k * 0.16)
        if 62 < xx < 132:
            put(fr, cy, xx, "◆", rc(R_GW, max(0.10, 1.0 - k * 0.10)))
    put(fr, cy - 1, int(px), "▼", WHITE)
    put(fr, cy - 3, int(px) - 3, f"{yr_f:04d}", GOLD)
    band(fr, 0, 4)
    bigtext(fr, "A.D  >  B.C", 0, 96, 8, rc(R_VIO, 0.45), WHITE)
    text(fr, 30, 56, "TRAVEL  //  TEMPORAL DISPLACEMENT", rc(R_VIO, 0.9))
    _plate(fr, 33, 3, 41, 54, "TEMPORAL TRANSIT", rc(R_VIO, 0.95),
           [("  origin  A.D 2077", GOLD),
            ("  target  B.C 0124", DIM),
            (f"  dt     -{1953 + int(pl * 4000)} y", TEAL),
            (f"  v      {int(pl * 99)}.9 c", rc(R_VIO, 0.9))])
    _plate(fr, 33, 138, 41, 189, "PARADOX GUARD", rc(R_RED, 0.95),
           [("  causality LOCKED", GOLD),
            (f"  loops    {int(pl * 12)}", DIM),
            (f"  drift    {pl * 4.2:.2f} y", TEAL),
            ("  status   SAFE", rc(R_TEAL, 0.9))])
    text(fr, 29, 64, "<<  back to the beginning", rc(R_TEAL, 0.8))
    text(fr, 42, 4, f"> warp {int(pl * 100):3d}%  ..  tachyon lock", rc(R_VIO, 0.8))


# ---------------------------------------------------------- phase 4: unite ---
def _half(fr, cx, cy, rx, ry, side, col, ch):
    th = np.linspace(-math.pi / 2, math.pi / 2, 640) if side > 0 else \
        np.linspace(math.pi / 2, 3 * math.pi / 2, 640)
    Y = np.round(cy + ry * np.sin(th)).astype(np.int32)
    X = np.round(cx + rx * np.cos(th)).astype(np.int32)
    plot(fr, Y, X, ch, col)
    plot(fr, Y + 1, X, "▄" if ch == "▀" else "▄", col)


def _ph_unite(fr, t, pl):
    cx, cy = 96.0, 21.0
    gap = (1.0 - fx.ease_out(pl)) * 50.0
    rx, ry = 33.0, 15.0
    _half(fr, cx - gap, cy, rx, ry, -1, rc(R_TW, 0.95), "▀")
    _half(fr, cx + gap, cy, rx, ry, +1, rc(R_GW, 0.95), "▀")
    # flat faces where the two halves will meet + internal hatching
    for (gx, cc, chh) in ((cx - gap, rc(R_TW, 0.95), "║"),
                          (cx + gap, rc(R_GW, 0.95), "┃")):
        for r in range(int(cy - ry), int(cy + ry) + 1):
            put(fr, r, int(gx), chh, cc)
    for k in range(-3, 4):
        r = int(cy + k * 4)
        if abs(k) * 4 < ry:
            wide = rx * math.sqrt(max(0.0, 1 - (k * 4 / ry) ** 2))
            line(fr, r, cx - gap - wide, r, cx - gap, rc(R_TEAL, 0.45), ch="·")
            line(fr, r, cx + gap, r, cx + gap + wide, rc(R_GOLD, 0.45), ch="·")
    # inner spokes
    for k in range(11):
        a = -math.pi / 2 + k * math.pi / 10
        line(fr, cy, cx - gap, cy + ry * math.sin(a), cx - gap + rx * math.cos(a),
             rc(R_TEAL, 0.65), ch="·")
        line(fr, cy, cx + gap, cy + ry * math.sin(a), cx + gap + rx * math.cos(a),
             rc(R_GOLD, 0.65), ch="·")
    # particles converging
    k = np.arange(260, dtype=np.float64)
    ang = _h01(k * 1.7) * 2 * math.pi + t * 0.7
    rad = (0.12 + 0.88 * _h01(k * 3.1)) * (1 - 0.88 * pl)
    PX = np.round(cx + np.cos(ang) * rad * 92).astype(np.int32)
    PY = np.round(cy + np.sin(ang) * rad * 30).astype(np.int32)
    plot(fr, PY, PX, np.where(k % 3 == 0, ci("•"), ci("·")), rc(R_PRIM, 0.75))
    # seam
    merged = gap < 3.0
    seam = WHITE if merged else rc(R_PW, 0.9)
    for r in range(int(cy - ry) - 2, int(cy + ry) + 3):
        put(fr, r, int(cx), "║", seam)
    if merged:
        kk = np.arange(90, dtype=np.float64)
        put(fr, int(cy), int(cx), "◆", WHITE)
        for j in range(7):
            ry2 = (j + (t * 2.6) % 1.0) * 2.6
            th = np.linspace(0, 2 * math.pi, 240)
            plot(fr, np.round(cy + ry2 * np.sin(th)).astype(np.int32),
                 np.round(cx + ry2 * 1.8 * np.cos(th)).astype(np.int32),
                 "·", rc(R_GW, 0.95 - 0.10 * j))
        sx = np.clip(np.round(cx + (kk - 45) * 1.1).astype(np.int32), 0, COLS - 1)
        sy = np.clip(np.round(cy + (t * 40 + kk * 7) % 30 - 15).astype(np.int32), 0, ROWS - 1)
        plot(fr, sy, sx, "✦", rc(R_GW, 0.8))
    band(fr, 0, 6)
    bigtext(fr, "UNITE", 0, 96, 10, rc(R_GW, 0.40), WHITE)
    text(fr, 8, 70, "and we can unite, so deeply", rc(R_TEAL, 0.9))
    if merged:
        text(fr, 9, 62, "◆  U N I T E D  ◆", rc(R_GW, 0.95))
    _plate(fr, 32, 3, 41, 46, "MERGE", rc(R_TEAL, 0.95),
           [("  left   A.D", rc(R_GOLD, 0.95)),
            ("  right  B.C", rc(R_RED, 0.95)),
            (f"  dx     {gap * 10:6.2f} px", DIM),
            (f"  merge  {min(100.0, pl * 100):5.1f} %", rc(R_GW, 0.9))])
    _plate(fr, 32, 146, 41, 189, "ENTANGLE", rc(R_GW, 0.95),
           [("  pairs   2 / 2", GOLD),
            ("  bond    MAX", DIM),
            (f"  depth   {pl * 100:5.1f} %", TEAL),
            (f"  dt      {gap * 1.4:6.3f} s", rc(R_TEAL, 0.9))])
    text(fr, 29, 66, "two halves, one simulation", rc(R_VIO, 0.85))
    text(fr, 42, 4, f"> weld {int(min(100, pl * 100)):3d}%  ..  seam {gap:5.2f}",
         rc(R_TEAL, 0.8))


# ------------------------------------------------------------------- HUD -----
def _hud(fr, t, ctx, p, phase):
    _rulers(fr, t)
    fill(fr, 42, 2, 43, 189, " ", col=DIM, bg=PANEL)
    put(fr, 0, 2, "┌", rc(R_TEAL, 0.6))
    put(fr, 0, 189, "┐", rc(R_TEAL, 0.6))
    put(fr, 44, 2, "└", rc(R_TEAL, 0.6))
    put(fr, 44, 189, "┘", rc(R_TEAL, 0.6))
    text(fr, 42, 4, f"s04 SIGNAL // {_PHASE_TAG.get(phase, '?')}", rc(R_TEAL, 0.8))
    text(fr, 42, 36, f"T+{t:9.2f}", DIM)
    text(fr, 42, 50, f"BEAT {ctx.beat_i:03d}  BAR {ctx.bar_i:03d}", DIM)
    text(fr, 42, 74, "BRIDGE 1 : AC / DC", rc(R_TEAL, 0.55))
    n = int(p * 24)
    text(fr, 43, 4, f"BRIDGE {'▓' * n}{'░' * (24 - n)}", rc(R_TEAL, 0.9))
    text(fr, 43, 34, f"RMS {ctx.rms * 100:4.1f}", rc(R_GOLD, 0.9))
    text(fr, 43, 46, f"PH {phase} / 4", DIM)
    text(fr, 43, 170, f"{int(p * 100):3d}%", rc(R_GW, 0.9))


# ------------------------------------------------------------------ draw -----
def draw(ctx):
    global _ip, _T
    fr = ctx.frame()
    t = ctx.t
    _T = t
    _ip = ctx.pulse
    lt = ctx.local
    p = fx.clamp(lt / ctx.dur)
    phase, pl = _phase(lt)
    _bg(fr, t)
    _wire(fr, t)
    if phase != 1:
        _floor(fr, t, 26, R_TEAL if phase != 2 else R_VIO, 0.45)
    if phase == 1:
        _ph_rect(fr, t, pl)
    elif phase == 2:
        _ph_dizzy(fr, t, pl)
    elif phase == 3:
        _ph_time(fr, t, pl)
    else:
        _ph_unite(fr, t, pl)
    _hud(fr, t, ctx, p, phase)
    ctx.meta["bloom"] = 0.45 + 0.25 * p
    g = 0.04 + 0.10 * pl
    if phase == 2:
        g += 0.05 + 0.05 * pl
    if phase == 4 and pl > 0.86:
        g += 0.10 * (pl - 0.86) / 0.14
    ctx.set_glitch(g)
    ctx.meta["flash"] = 0.05 * ctx.pulse + (0.10 * pl if phase == 4 else 0.0)
    ctx.meta["flash_color"] = GOLD if phase == 4 else (RED if phase == 2 else PRIMARY)
    return fr
