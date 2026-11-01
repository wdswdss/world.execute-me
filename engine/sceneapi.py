"""Scene context, scheduler and registry.

Every scene module exposes `draw(ctx) -> Frame` (45x192 stage) and mutates
`ctx.meta` for post-processing hints.  The scheduler maps a time in seconds to
exactly one scene.
"""
from __future__ import annotations

import importlib
import math

import numpy as np

from . import assets as A
from . import fx
from . import layout as L
from . import timeline as TL
from . import palette as P
from .frame import Frame

# (t0, t1, scene key, module)
SCHEDULE = [
    (0.000, 14.960, "boot", "s01_boot"),
    (14.960, 29.730, "title", "s02_title"),
    (29.730, 44.500, "infinity", "s03_infinity"),
    (44.500, 59.270, "acdc", "s04_acdc"),
    (59.270, 62.962, "stim", "s05_stim"),
    (62.962, 66.654, "satisfy", "s06_satisfy"),
    (66.654, 70.347, "happy", "s07_happy"),
    (70.347, 74.040, "trapped", "s08_trapped"),
    (74.040, 88.810, "characters", "s09_characters"),
    (88.810, 103.580, "transform", "s10_transform"),
    (103.580, 110.964, "heartbeat", "s11_heartbeat"),
    (110.964, 122.041, "leaving", "s12_leaving"),
    (122.041, 133.110, "fragments", "s13_fragments"),
    (133.110, 147.880, "heartfix", "s14_heartfix"),
    (147.880, 162.650, "count", "s15_count"),
    (162.650, 173.727, "onlyexec", "s16_onlyexec"),
    (173.727, 188.496, "study", "s17_study"),
    (188.496, 192.190, "trappedlove", "s18_trappedlove"),
    (192.190, 203.720, "outro99", "s19_outro99"),
    (203.720, 206.960, "redexec", "s20_redexec"),
    (206.960, 211.905, "endtext", "s21_endtext"),
]

SCENE_BY_KEY = {k: m for _, _, k, m in SCHEDULE}

DEFAULT_META = {
    "glitch": 0.0,
    "bloom": 0.35,
    "flash": 0.0,
    "flash_color": (255, 255, 255),
    "shake": (0, 0),
    "tint": None,          # (color, amount)
    "vignette": 1.0,
    "scan": 1.0,
    "grain": 1.0,
}


def scene_at(t):
    for t0, t1, key, mod in SCHEDULE:
        if t0 <= t < t1:
            return key, mod, t0, t1
    return "endtext", "s21_endtext", 206.960, 211.905


class Ctx:
    def __init__(self, t, assets=None):
        self.t = float(t)
        self.fi = int(round(t * L.FPS))
        self.assets = assets or A.get_assets()
        key, mod, t0, t1 = scene_at(t)
        self.scene = key
        self.modname = mod
        self.t0 = t0
        self.t1 = t1
        self.local = t - t0
        self.dur = t1 - t0
        sec, sec_t0, sec_t1 = A.section_at(t)
        self.section = sec
        self.sec_t0 = sec_t0
        self.sec_t1 = sec_t1
        self.sec_local = t - sec_t0
        self.beat_i = A.beat_index(t)
        self.bar_i = A.bar_index(t)
        self.beat_p = A.beat_phase(t)
        self.bar_p = A.bar_phase(t)
        self.pulse = float(math.exp(-5.0 * self.beat_p))
        self.bar_pulse = float(math.exp(-4.0 * self.bar_p))
        self.rms = self.assets.rms_at(t)
        self.bands = self.assets.bands_at(t)
        self.line_i, self.line = TL.line_at(t)
        self.line_p = 0.0
        if self.line:
            self.line_p = (t - self.line["t0"]) / max(1e-6, self.line["t1"] - self.line["t0"])
        self.meta = dict(DEFAULT_META)
        self._rngs = {}
        self.needs_afterimage = False

    # -- helpers ----------------------------------------------------------
    def rng(self, seed=0):
        key = int(seed) & 0xFFFF
        r = self._rngs.get(key)
        if r is None:
            r = fx.Rng((self.fi * 2654435761 + key * 40503 + 17) & 0x7FFFFFFF)
            self._rngs[key] = r
        return r

    def frame(self, bg=None):
        return Frame(L.STAGE_H, L.STAGE_W, bg=bg if bg is not None else P_void())

    def since(self, t_event):
        return self.t - t_event

    def norm(self, t0, t1):
        return fx.clamp((self.t - t0) / max(1e-6, t1 - t0))

    def fade(self, t0, t1, fade_in=0.25, fade_out=0.25):
        """0..1 envelope for a sub-beat inside the scene."""
        a = fx.smoothstep(self.t, t0, t0 + fade_in)
        b = 1.0 - fx.smoothstep(self.t, t1 - fade_out, t1)
        return min(a, b)

    def gate(self, t0, t1):
        return t0 <= self.t < t1

    def beat_phase_at(self, tt):
        return A.beat_phase(tt)

    def assets_bands(self, tt):
        return self.assets.bands_at(tt)

    def set_glitch(self, g):
        self.meta["glitch"] = max(self.meta["glitch"], float(g))

    def shake(self, amp, seed=0):
        r = self.rng(7000 + seed)
        a = float(amp)
        self.meta["shake"] = (r.randint(-int(a), int(a) + 1), r.randint(-int(a), int(a) + 1))


def P_void():
    from .palette import C
    return C["void"]


_MODULES = {}


def load_scene(modname, reload=False):
    full = f"engine.scenes.{modname}"
    if reload:
        if full in _MODULES:
            return importlib.reload(_MODULES[full])
        m = importlib.import_module(full)
        _MODULES[full] = m
        return m
    m = _MODULES.get(full)
    if m is None:
        m = importlib.import_module(full)
        _MODULES[full] = m
    return m


def draw_scene(t, assets=None, reload=False):
    ctx = Ctx(t, assets)
    mod = load_scene(ctx.modname, reload=reload)
    fr = mod.draw(ctx)
    if fr is None:
        fr = ctx.frame()
    return fr, ctx.meta, ctx


def err_frame(t):
    """Fallback stage frame used when a scene raises (render must never stop)."""
    fr = Frame(L.STAGE_H, L.STAGE_W)
    fr.write(14, 40, "SCENE RUNTIME ERROR", fg=P.C["red"])
    fr.write(16, 40, f"t={t:8.3f}  see render log", fg=P.C["dim"])
    return fr
