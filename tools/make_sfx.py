"""Build a very quiet machine-room sound bed + a few UI beeps.

Output: audio/sfx.wav (48 kHz, stereo, same length as layout.DURATION).
All levels are deliberately low; the bed is mixed under the song.
"""
from __future__ import annotations

import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import layout as L  # noqa: E402

SR = 48000
DUR = float(getattr(L, "DURATION", 215.905))
N = int(round(DUR * SR))
rng = np.random.default_rng(7)


def tone(freq: float, dur: float, amp: float, decay: float = 12.0) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    env = np.exp(-t * decay).astype(np.float32)
    return (np.sin(2 * np.pi * freq * t) * env * amp).astype(np.float32)


def add(buf: np.ndarray, at: float, sig: np.ndarray, pan: float = 0.0) -> None:
    i = int(round(at * SR))
    j = min(N, i + len(sig))
    if i >= N or j <= i:
        return
    seg = sig[: j - i]
    l = 1.0 - max(0.0, pan) * 0.35
    r = 1.0 - max(0.0, -pan) * 0.35
    buf[i:j, 0] += seg * l
    buf[i:j, 1] += seg * r


def main() -> None:
    out = np.zeros((N, 2), np.float32)

    # 1) machine-room bed: mains hum + very low hiss, opening up slowly
    t = np.arange(N, dtype=np.float32) / SR
    hum = (np.sin(2 * np.pi * 55.0 * t) * 0.006
           + np.sin(2 * np.pi * 110.0 * t) * 0.003)
    hiss = rng.standard_normal(N).astype(np.float32) * 0.0016
    # crude low-pass on the hiss so it reads as air, not tape noise
    k = 24
    hiss = np.convolve(hiss, np.ones(k, np.float32) / k, mode="same")
    grow = (0.35 + 0.65 * np.clip((t - 10.0) / 190.0, 0, 1)).astype(np.float32)
    bed = (hum + hiss) * grow
    out[:, 0] += bed
    out[:, 1] += bed

    # 2) boot beeps (under the CRT power-on)
    for at, f in ((0.30, 1180.0), (0.92, 1180.0), (1.55, 880.0)):
        add(out, at, tone(f, 0.055, 0.020, 26.0), pan=-0.2)

    # 3) title lock
    add(out, 25.88, tone(660.0, 0.10, 0.016, 18.0), pan=0.0)
    add(out, 25.95, tone(990.0, 0.07, 0.012, 22.0), pan=0.0)

    # 4) execution slam at the first stamp
    add(out, 161.72, tone(92.0, 0.30, 0.030, 9.0), pan=0.0)
    add(out, 161.72, tone(184.0, 0.12, 0.014, 16.0), pan=0.0)

    # 5) the last execution: a heavier hit
    add(out, 203.72, tone(78.0, 0.42, 0.034, 7.0), pan=0.0)
    add(out, 203.72, tone(156.0, 0.16, 0.016, 12.0), pan=0.0)

    # 6) end of line: two descending beeps as the sentence starts
    add(out, 208.86, tone(740.0, 0.09, 0.016, 18.0), pan=0.0)
    add(out, 208.98, tone(494.0, 0.12, 0.014, 15.0), pan=0.0)

    # gentle fade of the bed at the very end
    tail = np.clip((DUR - t) / 1.2, 0, 1).astype(np.float32)[:, None]
    out *= tail

    peak = float(np.max(np.abs(out))) or 1.0
    out = out / peak * 0.07  # keep it far under the music
    pcm = (np.clip(out, -1.0, 1.0) * 32767.0).astype(np.int16)

    path = os.path.join(ROOT, "audio", "sfx.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", path, f"{N / SR:.3f}s peak {peak:.4f}")


if __name__ == "__main__":
    main()
