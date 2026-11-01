"""Audio-derived assets + beat/section helpers."""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "audio")

FPS = 60
DURATION = 211.905
BPM = 130.0
BEAT = 60.0 / BPM                # 0.461538...
BAR = BEAT * 4                   # 1.846154
T0 = 0.190                       # first beat

SECTIONS = [
    ("intro",         0.190,  14.960,  8),
    ("transition_a",  14.960, 29.730,  8),
    ("verse_1",       29.730, 44.500,  8),
    ("bridge_1",      44.500, 59.270,  8),
    ("chorus_1",      59.270, 74.040,  8),
    ("verse_2",       74.040, 88.810,  8),
    ("bridge_2",      88.810, 103.580, 8),
    ("chorus_2",      103.580, 133.110, 16),
    ("transition_b",  133.110, 147.880, 8),
    ("bridge_solo",   147.880, 162.650, 8),
    ("final_chorus",  162.650, 192.190, 16),
    ("outro",         192.190, 206.960, 8),
    ("tail",          206.960, 211.905, 2.675),
]


def section_at(t):
    for name, t0, t1, _ in SECTIONS:
        if t0 <= t < t1:
            return name, t0, t1
    return ("tail", 206.96, 211.905)


# beat helpers -----------------------------------------------------------------

def beat_index(t):
    return int(np.floor((t - T0) / BEAT + 1e-9))


def beat_time(k):
    return T0 + k * BEAT


def bar_index(t):
    return int(np.floor((t - T0) / BAR + 1e-9))


def bar_time(b):
    return T0 + b * BAR


def beat_phase(t):
    return ((t - T0) / BEAT) % 1.0


def bar_phase(t):
    return ((t - T0) / BAR) % 1.0


def beat_pulse(t, decay=5.0):
    """1 at the beat, decaying exponentially until the next one."""
    return float(np.exp(-decay * beat_phase(t)))


def bar_pulse(t, decay=4.0):
    return float(np.exp(-decay * bar_phase(t)))


def frame_index(t):
    return int(round(t * FPS))


def time_of_frame(i):
    return i / FPS


def snap_beat(t):
    return beat_time(round((t - T0) / BEAT))


def _synthetic_spec(fps, dur, beats):
    """A neutral envelope for checkouts without the song.

    The repo cannot ship audio (Mili's copyright), so a fresh clone has no
    audio/spectrum.npz.  Rendering still works: we fake a plausible envelope
    from the beat grid so motion keyed on rms/bands stays alive instead of
    flatlining.  Run `python tools/build_assets.py` with your own copy of the
    song to get the real analysis.
    """
    n = int(dur * fps) + 2
    t = np.arange(n, dtype=np.float32) / float(fps)
    if beats is not None and len(beats) > 1:
        beat = float(np.median(np.diff(beats)))
    else:
        beat = 60.0 / 130.0
    phase = ((t - T0) / max(1e-3, beat)) % 1.0
    env = 0.25 + 0.55 * np.exp(-6.0 * phase)          # (N,)
    tilt = np.linspace(1.25, 0.45, 64, dtype=np.float32)  # low freqs louder
    bands = (env[:, None] * tilt[None, :]).astype(np.float32)
    rms = (0.30 + 0.35 * np.exp(-5.0 * phase)).astype(np.float32)
    vocal = np.zeros(n, np.float32)
    return bands, rms, vocal


class Assets:
    def __init__(self, root=None):
        root = root or ROOT
        audio = os.path.join(root, "audio")
        spec_path = os.path.join(audio, "spectrum.npz")
        if os.path.exists(spec_path):
            spec = np.load(spec_path)
            self.bands = spec["bands"].astype(np.float32)      # (N,64)
            self.rms = spec["rms"].astype(np.float32)
            self.vocal = spec["vocal"].astype(np.float32)
            self.n_frames = self.bands.shape[0]
            self.fps = int(spec["fps"]) if "fps" in spec else FPS
        else:
            # no song in the repo -> synthetic envelope (see _synthetic_spec)
            self.fps = FPS
            beats = None
            try:
                with open(os.path.join(audio, "beats.json"), encoding="utf-8") as f:
                    beats = np.array(json.load(f)["beats"], np.float32)
            except Exception:
                pass
            self.bands, self.rms, self.vocal = _synthetic_spec(FPS, DURATION, beats)
            self.n_frames = self.bands.shape[0]
            print("[assets] audio/spectrum.npz not found - using a synthetic "
                  "envelope (put the song at audio/song.wav and run "
                  "tools/build_assets.py for the real one)")
        try:
            bj = np.load(os.path.join(audio, "beats.npz"))
            self.beats = bj["beats"].astype(np.float32)
            self.downbeats = bj["downbeats"].astype(np.float32)
            self.cues = bj["cues"].astype(np.float32)
        except Exception:
            with open(os.path.join(audio, "beats.json"), encoding="utf-8") as f:
                bj = json.load(f)
            self.beats = np.array(bj["beats"], np.float32)
            self.downbeats = np.array(bj.get("downbeats", []), np.float32)
            self.cues = np.zeros((0, 2), np.float32)

    def _idx(self, t):
        return int(np.clip(round(t * self.fps), 0, self.n_frames - 1))

    def bands_at(self, t):
        return self.bands[self._idx(t)]

    def rms_at(self, t):
        return float(self.rms[self._idx(t)])

    def vocal_at(self, t):
        return float(self.vocal[self._idx(t)])

    def energy(self, t, window=0.25):
        i0 = self._idx(max(0.0, t - window / 2))
        i1 = self._idx(t + window / 2)
        return float(self.rms[i0:i1 + 1].mean()) if i1 >= i0 else 0.0

    def vocal_energy(self, t, window=0.25):
        i0 = self._idx(max(0.0, t - window / 2))
        i1 = self._idx(t + window / 2)
        return float(self.vocal[i0:i1 + 1].mean()) if i1 >= i0 else 0.0

    def bands_smoothed(self, t, k=3):
        i = self._idx(t)
        lo = max(0, i - k)
        hi = min(self.n_frames, i + k + 1)
        return self.bands[lo:hi].mean(axis=0)

    def low_at(self, t):
        return float(self.bands_at(t)[:6].mean())

    def mid_at(self, t):
        return float(self.bands_at(t)[20:40].mean())

    def high_at(self, t):
        return float(self.bands_at(t)[48:].mean())

    def cue_energy(self, t, window=0.35):
        if len(self.cues) == 0:
            return 0.0
        sel = np.abs(self.cues[:, 0] - t) <= window
        return float(self.cues[sel, 1].max()) if sel.any() else 0.0


_ASSETS = None


def get_assets():
    global _ASSETS
    if _ASSETS is None:
        _ASSETS = Assets()
    return _ASSETS
