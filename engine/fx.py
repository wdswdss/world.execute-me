"""Deterministic math / noise helpers and cell-level glitch effects."""
from __future__ import annotations

import numpy as np

from . import font as F
from . import layout as L
from . import palette as P


# -- math --------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def lerp(a, b, f):
    return a + (b - a) * f


def smoothstep(x, a=0.0, b=1.0):
    if a == b:
        return 0.0 if x < a else 1.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_inout(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x, s=1.7):
    x = clamp(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


def hash01(*args):
    """Deterministic float in [0,1) from arbitrary ints/floats."""
    h = 0x811C9DC5
    for a in args:
        v = int(round(float(a) * 1000.0)) & 0xFFFFFFFF
        h ^= v + 0x9E3779B9 + (h << 6) + (h >> 2)
        h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


class Rng:
    """Numpy generator with a stable seed built from the scene + frame."""

    def __init__(self, seed):
        self.gen = np.random.default_rng(int(seed) & 0x7FFFFFFF)
        self.seed = seed

    def random(self, n=None):
        return self.gen.random(n) if n is not None else float(self.gen.random())

    def randint(self, a, b, n=None):
        return self.gen.integers(a, b, size=n) if n is not None else int(self.gen.integers(a, b))

    def choice(self, seq):
        return seq[int(self.gen.integers(0, len(seq)))]


def noise1d(x, seed=0.0, octaves=3):
    """Smooth deterministic pseudo-noise in [-1,1]."""
    v = 0.0
    amp = 1.0
    tot = 0.0
    for o in range(octaves):
        f = (1.7 ** o) * 2.1
        ph = hash01(seed, o) * 6.2831
        v += np.sin(x * f + ph) * amp
        tot += amp
        amp *= 0.55
    return v / tot


def noise2d(x, y, seed=0.0):
    return 0.6 * noise1d(x * 1.1 + y * 0.7 + seed * 13.1, seed) + \
        0.4 * noise1d(y * 1.3 - x * 0.5 + seed * 7.7, seed + 1)


# -- cell effects ------------------------------------------------------------
_PRINTABLE = "".join(chr(c) for c in range(33, 127))


def cells_noise(fr, rng, density=0.1, ramp=None, fg=None, bg=None, region=None,
                chars=None):
    r0, c0, r1, c1 = region or (0, 0, fr.rows - 1, fr.cols - 1)
    r0 = max(0, r0); c0 = max(0, c0)
    r1 = min(fr.rows - 1, r1); c1 = min(fr.cols - 1, c1)
    if r1 < r0 or c1 < c0:
        return
    h, w = r1 - r0 + 1, c1 - c0 + 1
    sel = rng.random((h, w)) < density
    pool = chars or (ramp or P.RAMP_HI)
    idxs = np.array([F.char_index(ch) for ch in pool], np.int16)
    pick = idxs[rng.randint(0, len(idxs), (h, w))]
    cur = fr.ch[r0:r1 + 1, c0:c1 + 1]
    fr.ch[r0:r1 + 1, c0:c1 + 1] = np.where(sel, pick, cur)
    if fg is not None:
        col = np.asarray(fg, np.uint8)
        m = sel[..., None]
        fr.fg[r0:r1 + 1, c0:c1 + 1] = np.where(m, col, fr.fg[r0:r1 + 1, c0:c1 + 1])


def cells_glitch(fr, rng, amount=0.2, region=None):
    """Character corruption + colour tearing + horizontal band shifts."""
    r0, c0, r1, c1 = region or (0, 0, fr.rows - 1, fr.cols - 1)
    r0 = max(0, r0); c0 = max(0, c0)
    r1 = min(fr.rows - 1, r1); c1 = min(fr.cols - 1, c1)
    if r1 < r0 or c1 < c0:
        return
    h, w = r1 - r0 + 1, c1 - c0 + 1
    nband = max(1, int(amount * 6))
    for _ in range(nband):
        y0 = r0 + rng.randint(0, h)
        y1 = min(r1, y0 + rng.randint(1, max(2, int(h * 0.12)) + 1))
        dx = rng.randint(-int(4 + amount * 18), int(4 + amount * 18) + 1)
        if dx:
            band = fr.ch[y0:y1 + 1, c0:c1 + 1].copy()
            fband = fr.fg[y0:y1 + 1, c0:c1 + 1].copy()
            fr.ch[y0:y1 + 1, c0:c1 + 1] = np.roll(band, dx, axis=1)
            fr.fg[y0:y1 + 1, c0:c1 + 1] = np.roll(fband, dx, axis=1)
    sel = rng.random((h, w)) < amount * 0.35
    idxs = np.array([F.char_index(ch) for ch in "#%&@$*!?/\\|<>^~"], np.int16)
    pick = idxs[rng.randint(0, len(idxs), (h, w))]
    fr.ch[r0:r1 + 1, c0:c1 + 1] = np.where(sel, pick, fr.ch[r0:r1 + 1, c0:c1 + 1])
    tint = rng.random((h, w)) < amount * 0.5
    cols = np.array([P.C["red"], P.C["magenta"], P.C["primary"], P.C["white"]], np.uint8)
    pickc = cols[rng.randint(0, len(cols), (h, w))]
    fr.fg[r0:r1 + 1, c0:c1 + 1] = np.where(tint[..., None], pickc, fr.fg[r0:r1 + 1, c0:c1 + 1])


def cells_dim(fr, f=0.5, region=None):
    r0, c0, r1, c1 = region or (0, 0, fr.rows - 1, fr.cols - 1)
    fr.fg[max(0, r0):r1 + 1, max(0, c0):c1 + 1] = (
        fr.fg[max(0, r0):r1 + 1, max(0, c0):c1 + 1].astype(np.float32) * f).astype(np.uint8)


def cells_tint(fr, color, f=0.5, region=None):
    r0, c0, r1, c1 = region or (0, 0, fr.rows - 1, fr.cols - 1)
    r0 = max(0, r0); c0 = max(0, c0)
    r1 = min(fr.rows - 1, r1); c1 = min(fr.cols - 1, c1)
    col = np.asarray(color, np.float32)
    fr.fg[r0:r1 + 1, c0:c1 + 1] = (
        fr.fg[r0:r1 + 1, c0:c1 + 1] * (1 - f) + col * f).astype(np.uint8)


def cells_fade_rows(fr, top=(0, 0, 0), bottom=(0, 0, 0)):
    """Not used yet; reserved for scene authors."""
    pass


def typewriter(s, t, cps=40.0, start=0.0):
    n = max(0, int((t - start) * cps))
    return s[:n]


def wave(t, freq=1.0, phase=0.0, lo=0.0, hi=1.0):
    v = 0.5 + 0.5 * np.sin(t * freq * 2 * np.pi + phase)
    return lo + (hi - lo) * v
