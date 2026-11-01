"""Concrete character / object art rendered as coverage masks.

Each character is drawn once with PIL at high resolution and returned as a
dict of named masks (float32 0..1).  Scenes then paint the masks onto the cell
grid with `Frame.paint_mask`, tinting / animating / glitching the layers.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import font as F

SCALE = 2


def _canvas(w, h):
    im = Image.new("L", (int(w * SCALE), int(h * SCALE)), 0)
    return im, ImageDraw.Draw(im)


def _fin(im, w, h, blur=0.0):
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur * SCALE))
    arr = np.asarray(im.resize((int(w), int(h)), Image.LANCZOS)).astype(np.float32) / 255.0
    return arr


def _ell(d, cx, cy, rx, ry, fill=255, outline=None, width=0):
    d.ellipse([(cx - rx) * SCALE, (cy - ry) * SCALE, (cx + rx) * SCALE, (cy + ry) * SCALE],
              fill=fill, outline=outline, width=int(width * SCALE))


def _circ(d, cx, cy, r, fill=255):
    _ell(d, cx, cy, r, r, fill)


def _poly(d, pts, fill=255, outline=None):
    d.polygon([(x * SCALE, y * SCALE) for x, y in pts], fill=fill, outline=outline)


def _line(d, pts, fill=255, width=3):
    d.line([(x * SCALE, y * SCALE) for x, y in pts], fill=fill, width=int(width * SCALE))


def _arc(d, cx, cy, rx, ry, a0, a1, fill=255, width=3):
    d.arc([(cx - rx) * SCALE, (cy - ry) * SCALE, (cx + rx) * SCALE, (cy + ry) * SCALE],
          a0, a1, fill=fill, width=int(width * SCALE))


def _star_poly(cx, cy, n, r_out, r_in, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ------------------------------------------------------------------ heart ---
def heart(w=600, h=560, holes=(), dents=(), thick=1.0):
    """Heart body mask + optional defects (used by the repair scenes)."""
    m = F.heart_mask(int(w), int(h), holes=holes, dents=dents)
    im, d = _canvas(w, h)
    arr = (np.asarray(im, np.float32))
    # carve the outer ring so the heart reads as a line-art icon sometimes
    return m


def heart_outline(w=600, h=560, thick=0.035, holes=(), dents=()):
    """Hollow heart outline (same silhouette, band around the edge)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx / w - 0.5) * 2.6
    y = -(yy / h - 0.52) * 2.6
    f = (x * x + y * y - 1) ** 3 - x * x * y * y * y
    gy, gx = np.gradient(f)
    g = np.sqrt(gx * gx + gy * gy) + 1e-6
    dist = np.abs(f) / g
    m = np.clip((thick * w * 0.02 - dist) / (thick * w * 0.004), 0, 1)
    for (fx, fy, fr) in holes:
        cx, cy, r = fx * w, fy * h, fr * w
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        m = m * np.clip((d - r) / max(1e-3, r * 0.08), 0, 1)
    return m


# --------------------------------------------------------------- infinity ---
def infinity(w=900, h=400, thick=0.16):
    m = F.infinity_mask(int(w), int(h), thick=thick)
    return m


# -------------------------------------------------------------- eggplant ----
def eggplant(w=640, h=780):
    """Purple eggplant character with calyx, stem, shiny skin and a face."""
    out = {}
    im, d = _canvas(w, h)
    # bulb
    _ell(d, w * 0.50, h * 0.66, w * 0.34, h * 0.28)
    # neck (tapered)
    neck = [(w * 0.36, h * 0.20), (w * 0.66, h * 0.20),
            (w * 0.72, h * 0.48), (w * 0.30, h * 0.48)]
    _poly(d, neck)
    # round the shoulders
    _ell(d, w * 0.36, h * 0.30, w * 0.10, h * 0.11)
    _ell(d, w * 0.66, h * 0.30, w * 0.10, h * 0.11)
    out["body"] = _fin(im, w, h, blur=1.2)

    im, d = _canvas(w, h)
    # calyx: five pointed leaves around the top
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        tipx = w * 0.50 + math.cos(a) * w * 0.20
        tipy = h * 0.22 + math.sin(a) * h * 0.10
        mid = a + 0.32
        p1 = (w * 0.50 + math.cos(mid - 0.4) * w * 0.09, h * 0.22 + math.sin(mid - 0.4) * h * 0.05)
        p2 = (w * 0.50 + math.cos(mid + 0.4) * w * 0.09, h * 0.22 + math.sin(mid + 0.4) * h * 0.05)
        _poly(d, [(w * 0.50, h * 0.235), (tipx, tipy), p1, p2])
    out["leaf"] = _fin(im, w, h, blur=1.0)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.455, h * 0.06), (w * 0.545, h * 0.05),
              (w * 0.535, h * 0.235), (w * 0.465, h * 0.235)])
    _ell(d, w * 0.545, h * 0.055, w * 0.028, h * 0.022)
    out["stem"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    # skin highlight: a long crescent on the left of the bulb
    _ell(d, w * 0.40, h * 0.60, w * 0.075, h * 0.15)
    _ell(d, w * 0.435, h * 0.60, w * 0.070, h * 0.14, fill=0)
    out["shine"] = _fin(im, w, h, blur=1.6)

    # face
    eye_l = (w * 0.38, h * 0.60, w * 0.052)
    eye_r = (w * 0.62, h * 0.60, w * 0.052)
    out["eyes"] = (eye_l, eye_r)
    im, d = _canvas(w, h)
    _circ(d, *eye_l[:2], eye_l[2])
    _circ(d, *eye_r[:2], eye_r[2])
    out["eye"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _circ(d, eye_l[0] - eye_l[2] * 0.3, eye_l[1] - eye_l[2] * 0.3, eye_l[2] * 0.28)
    _circ(d, eye_r[0] - eye_r[2] * 0.3, eye_r[1] - eye_r[2] * 0.3, eye_r[2] * 0.28)
    out["glint"] = _fin(im, w, h, blur=0.4)
    im, d = _canvas(w, h)
    _arc(d, w * 0.50, h * 0.665, w * 0.075, h * 0.035, 20, 160, width=4)
    out["mouth"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _ell(d, w * 0.30, h * 0.665, w * 0.05, h * 0.022)
    _ell(d, w * 0.70, h * 0.665, w * 0.05, h * 0.022)
    out["blush"] = _fin(im, w, h, blur=3.0)
    return out


# ---------------------------------------------------------------- tomato ----
def tomato(w=680, h=680):
    out = {}
    im, d = _canvas(w, h)
    _ell(d, w * 0.50, h * 0.58, w * 0.40, h * 0.37)
    out["body"] = _fin(im, w, h, blur=1.2)

    im, d = _canvas(w, h)
    # star calyx
    _poly(d, _star_poly(w * 0.50, h * 0.235, 6, w * 0.26, w * 0.10))
    out["leaf"] = _fin(im, w, h, blur=1.0)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.485, h * 0.10), (w * 0.525, h * 0.09),
              (w * 0.520, h * 0.235), (w * 0.480, h * 0.235)])
    out["stem"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    _ell(d, w * 0.36, h * 0.44, w * 0.115, h * 0.075)
    out["shine"] = _fin(im, w, h, blur=2.2)

    eye_l = (w * 0.38, h * 0.55, w * 0.05)
    eye_r = (w * 0.62, h * 0.55, w * 0.05)
    out["eyes"] = (eye_l, eye_r)
    im, d = _canvas(w, h)
    _circ(d, *eye_l[:2], eye_l[2])
    _circ(d, *eye_r[:2], eye_r[2])
    out["eye"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _circ(d, eye_l[0] - eye_l[2] * 0.3, eye_l[1] - eye_l[2] * 0.3, eye_l[2] * 0.28)
    _circ(d, eye_r[0] - eye_r[2] * 0.3, eye_r[1] - eye_r[2] * 0.3, eye_r[2] * 0.28)
    out["glint"] = _fin(im, w, h, blur=0.4)
    im, d = _canvas(w, h)
    _arc(d, w * 0.50, h * 0.62, w * 0.07, h * 0.03, 20, 160, width=4)
    out["mouth"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _ell(d, w * 0.30, h * 0.63, w * 0.05, h * 0.022)
    _ell(d, w * 0.70, h * 0.63, w * 0.05, h * 0.022)
    out["blush"] = _fin(im, w, h, blur=3.0)
    return out


# ------------------------------------------------------------- tabby cat ----
def tabby(w=760, h=820):
    """Tabby cat head + shoulders, with stripes, ears, whiskers and a face."""
    out = {}
    im, d = _canvas(w, h)
    # shoulders
    _ell(d, w * 0.50, h * 0.99, w * 0.40, h * 0.30)
    # head
    _ell(d, w * 0.50, h * 0.50, w * 0.29, h * 0.26)
    # ears
    _poly(d, [(w * 0.26, h * 0.40), (w * 0.20, h * 0.10), (w * 0.46, h * 0.28)])
    _poly(d, [(w * 0.74, h * 0.40), (w * 0.80, h * 0.10), (w * 0.54, h * 0.28)])
    out["body"] = _fin(im, w, h, blur=1.2)

    im, d = _canvas(w, h)
    # inner ears
    _poly(d, [(w * 0.30, h * 0.34), (w * 0.26, h * 0.17), (w * 0.41, h * 0.28)])
    _poly(d, [(w * 0.70, h * 0.34), (w * 0.74, h * 0.17), (w * 0.59, h * 0.28)])
    out["inner_ear"] = _fin(im, w, h, blur=0.8)

    im, d = _canvas(w, h)
    # forehead stripes (M mark) + cheek stripes
    _line(d, [(w * 0.44, h * 0.30), (w * 0.47, h * 0.40)], width=5)
    _line(d, [(w * 0.50, h * 0.29), (w * 0.50, h * 0.41)], width=5)
    _line(d, [(w * 0.56, h * 0.30), (w * 0.53, h * 0.40)], width=5)
    for i, dy in enumerate((0.0, 0.035, 0.07)):
        _line(d, [(w * 0.20, h * (0.50 + dy)), (w * 0.30, h * (0.49 + dy))], width=4)
        _line(d, [(w * 0.80, h * (0.50 + dy)), (w * 0.70, h * (0.49 + dy))], width=4)
    out["stripes"] = _fin(im, w, h, blur=0.7)

    im, d = _canvas(w, h)
    # muzzle
    _ell(d, w * 0.50, h * 0.60, w * 0.14, h * 0.095)
    out["muzzle"] = _fin(im, w, h, blur=1.4)

    eye_l = (w * 0.40, h * 0.49, w * 0.075)
    eye_r = (w * 0.60, h * 0.49, w * 0.075)
    out["eyes"] = (eye_l, eye_r)
    im, d = _canvas(w, h)
    _ell(d, eye_l[0], eye_l[1], eye_l[2], eye_l[2] * 0.78)
    _ell(d, eye_r[0], eye_r[1], eye_r[2], eye_r[2] * 0.78)
    out["eye"] = _fin(im, w, h, blur=0.7)
    im, d = _canvas(w, h)
    # slit pupils
    _ell(d, eye_l[0], eye_l[1], eye_l[2] * 0.20, eye_l[2] * 0.60)
    _ell(d, eye_r[0], eye_r[1], eye_r[2] * 0.20, eye_r[2] * 0.60)
    out["pupil"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _circ(d, eye_l[0] + eye_l[2] * 0.25, eye_l[1] - eye_l[2] * 0.25, eye_l[2] * 0.18)
    _circ(d, eye_r[0] + eye_r[2] * 0.25, eye_r[1] - eye_r[2] * 0.25, eye_r[2] * 0.18)
    out["glint"] = _fin(im, w, h, blur=0.4)

    im, d = _canvas(w, h)
    _poly(d, [(w * 0.475, h * 0.555), (w * 0.525, h * 0.555), (w * 0.50, h * 0.585)])
    out["nose"] = _fin(im, w, h, blur=0.6)
    im, d = _canvas(w, h)
    _line(d, [(w * 0.50, h * 0.585), (w * 0.50, h * 0.625)], width=3)
    _arc(d, w * 0.47, h * 0.625, w * 0.03, h * 0.02, 0, 180, width=3)
    _arc(d, w * 0.53, h * 0.625, w * 0.03, h * 0.02, 0, 180, width=3)
    out["mouth"] = _fin(im, w, h, blur=0.6)

    im, d = _canvas(w, h)
    for i, dy in enumerate((-0.02, 0.0, 0.02)):
        _line(d, [(w * 0.44, h * (0.60 + dy)), (w * 0.18, h * (0.585 + dy * 2.2))], width=2)
        _line(d, [(w * 0.56, h * (0.60 + dy)), (w * 0.82, h * (0.585 + dy * 2.2))], width=2)
    out["whiskers"] = _fin(im, w, h, blur=0.6)
    return out


# ------------------------------------------------------------------- misc ---
def circle_mask(w, h, r=None):
    im, d = _canvas(w, h)
    _circ(d, w * 0.5, h * 0.5, (r or w * 0.45))
    return _fin(im, w, h, blur=0.8)


def ring_mask(w, h, thick=0.08):
    im, d = _canvas(w, h)
    _circ(d, w * 0.5, h * 0.5, w * 0.42)
    _circ(d, w * 0.5, h * 0.5, w * (0.42 - thick), fill=0)
    return _fin(im, w, h, blur=0.8)


def cross_mask(w, h, thick=0.12):
    im, d = _canvas(w, h)
    _line(d, [(w * 0.15, h * 0.15), (w * 0.85, h * 0.85)], width=int(w * thick))
    _line(d, [(w * 0.85, h * 0.15), (w * 0.15, h * 0.85)], width=int(w * thick))
    return _fin(im, w, h, blur=0.8)


def speech_bubble(w, h, tail="left"):
    im, d = _canvas(w, h)
    r = min(w, h) * 0.16
    d.rounded_rectangle([w * 0.05 * SCALE, h * 0.08 * SCALE, w * 0.95 * SCALE, h * 0.72 * SCALE],
                        radius=r * SCALE, fill=255)
    if tail == "left":
        _poly(d, [(w * 0.22, h * 0.70), (w * 0.16, h * 0.92), (w * 0.36, h * 0.72)])
    elif tail == "right":
        _poly(d, [(w * 0.78, h * 0.70), (w * 0.84, h * 0.92), (w * 0.64, h * 0.72)])
    return _fin(im, w, h, blur=0.6)


_CACHE = {}


def get(name, **kw):
    key = (name, tuple(sorted(kw.items())))
    if key not in _CACHE:
        fn = {"eggplant": eggplant, "tomato": tomato, "tabby": tabby,
              "heart": heart, "heart_outline": heart_outline, "infinity": infinity,
              "circle": circle_mask, "ring": ring_mask, "cross": cross_mask,
              "bubble": speech_bubble}[name]
        _CACHE[key] = fn(**kw)
    return _CACHE[key]

def heart_fill(w, h, holes=(), dents=()):
    """Solid heart silhouette from the classic implicit curve

        (x^2 + y^2 - 1)^3 - x^2 y^3 <= 0

    Rasterised at 2x and box-filtered down. ``holes`` are circular voids inside
    the body; ``dents`` are shallow concave bites on the silhouette edge (a
    radial deformation of the implicit field, not interior holes).
    """
    import numpy as _np
    w = max(2, int(w))
    h = max(2, int(h))
    ss = 2
    W, H = w * ss, h * ss
    yy, xx = _np.mgrid[0:H, 0:W].astype(_np.float32)
    u = (xx + 0.5) / W
    v = (yy + 0.5) / H
    x = (u * 2.0 - 1.0) * 1.30
    y = 1.22 - v * 2.24
    f = (x * x + y * y - 1.0) ** 3 - x * x * y * y * y
    if dents:
        xc, yc = 0.0, 0.08
        theta = _np.arctan2(y - yc, x - xc)
        a = 0.0
        for (fx, fy, fr) in dents:
            dx = (fx * 2.0 - 1.0) * 1.30
            dy = 1.22 - fy * 2.24
            tk = _np.arctan2(dy - yc, dx - xc)
            sig = max(0.14, 2.4 * fr)
            dth = _np.abs((theta - tk + _np.pi) % (2 * _np.pi) - _np.pi)
            a = a + (0.10 + 1.15 * fr) * _np.exp(-(dth * dth) / (2.0 * sig * sig))
        f = f + a
    m = (f <= 0.0).astype(_np.float32)
    for (fx, fy, fr) in holes:
        cx, cyy, r = fx * W, fy * H, fr * W
        d = _np.sqrt((xx - cx) ** 2 + (yy - cyy) ** 2)
        m *= _np.clip((d - r) / (1.2 * ss), 0.0, 1.0)
    m = m.reshape(h, ss, w, ss).mean(axis=(1, 3))
    return m.astype(_np.float32)
