"""Build derived audio assets + validate the glyph atlas.

    python tools/build_assets.py

Outputs:
    audio/spectrum.npz   per-video-frame spectrum bands, rms, vocal-band energy
    audio/beats.npz      beats / downbeats / cues from audio/beats.json
    qa/atlas.png         glyph atlas proof sheet
"""
from __future__ import annotations

import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import font as F  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "audio")
QA = os.path.join(ROOT, "qa")
FPS = 60
N_BANDS = 64


def read_wav(path):
    with wave.open(path, "rb") as w:
        nch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = (b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        data = v.astype(np.float32) / float(1 << 23)
    elif sw == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise SystemExit(f"unsupported sample width {sw}")
    if nch > 1:
        data = data.reshape(-1, nch).mean(axis=1)
    return data, sr


def build_spectrum(y, sr, duration):
    n_frames = int(round(duration * FPS))
    hop = int(round(sr / FPS))
    win = 2048
    edges = np.geomspace(24.0, 15000.0, N_BANDS + 1)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    band_idx = []
    for i in range(N_BANDS):
        lo, hi = edges[i], edges[i + 1]
        sel = np.where((freqs >= lo) & (freqs < hi))[0]
        if len(sel) == 0:
            sel = np.array([int(np.argmin(np.abs(freqs - (lo + hi) / 2)))])
        band_idx.append(sel)

    bands = np.zeros((n_frames, N_BANDS), np.float32)
    rms = np.zeros(n_frames, np.float32)
    vocal = np.zeros(n_frames, np.float32)
    win_hann = np.hanning(win).astype(np.float32)
    chunk = 256
    # frequency mask for the 300-3000 Hz vocal band
    vmask = (freqs >= 300) & (freqs <= 3000)
    for start in range(0, n_frames, chunk):
        idx = np.arange(start, min(n_frames, start + chunk))
        center = (idx * hop).astype(np.int64)
        lo = center - win // 2
        pad = np.zeros((len(idx), win), np.float32)
        for k, (l, c) in enumerate(zip(lo, idx * hop)):
            a = max(0, l)
            b = min(len(y), a + win)
            if b <= a:
                continue
            seg = y[a:b]
            pad[k, :len(seg)] = seg
        frame = pad * win_hann
        spec = np.abs(np.fft.rfft(frame, axis=1))
        for i, sel in enumerate(band_idx):
            bands[idx, i] = spec[:, sel].mean(axis=1)
        rms[idx] = np.sqrt((pad ** 2).mean(axis=1))
        vocal[idx] = spec[:, vmask].sum(axis=1)
    # normalise to 0..1 with a soft curve
    for i in range(N_BANDS):
        col = bands[:, i]
        hi = np.percentile(col, 98) + 1e-6
        bands[:, i] = np.clip(col / hi, 0, 1)
    rms = np.clip(rms / (np.percentile(rms, 98) + 1e-6), 0, 1)
    vocal = vocal / (np.percentile(vocal, 97) + 1e-6)
    vocal = np.clip(vocal, 0, 1)
    # 3-frame smooth for the spectrum so it reads like a falling analyser
    k = np.array([0.25, 0.5, 0.25], np.float32)
    bands = np.apply_along_axis(lambda c: np.convolve(c, k, mode="same"), 0, bands).astype(np.float32)
    rms = np.convolve(rms, np.array([0.3, 0.4, 0.3], np.float32), mode="same").astype(np.float32)
    return bands, rms, vocal


def main():
    os.makedirs(QA, exist_ok=True)
    wav = os.path.join(AUDIO, "song.wav")
    print("reading", wav)
    y, sr = read_wav(wav)
    duration = len(y) / sr
    print(f"  sr={sr} duration={duration:.3f}s")
    bands, rms, vocal = build_spectrum(y, sr, duration)
    n = bands.shape[0]
    print(f"  frames={n} bands={bands.shape[1]}")
    np.savez_compressed(os.path.join(AUDIO, "spectrum.npz"),
                        bands=bands, rms=rms, vocal=vocal, fps=FPS)
    # beat grid
    with open(os.path.join(AUDIO, "beats.json"), "r", encoding="utf-8") as f:
        bj = json.load(f)
    beats = np.array(bj.get("beats") or [], np.float32)
    downs = np.array(bj.get("downbeats") or [], np.float32)
    cues = np.array([[c.get("time", c.get("t", 0)), c.get("strength", c.get("s", 1.0))]
                     for c in (bj.get("cues") or [])], np.float32)
    np.savez_compressed(os.path.join(AUDIO, "beats.npz"),
                        beats=beats, downbeats=downs, cues=cues,
                        bpm=np.float32(bj.get("bpm", 130.0)))
    print(f"  beats={len(beats)} downbeats={len(downs)} cues={len(cues)}")

    # glyph atlas proof sheet
    atlas, idx = F.build_atlas(verbose=True)
    n_glyphs = atlas.shape[0]
    cols = 32
    rows = (n_glyphs + cols - 1) // cols
    sheet = np.zeros((rows * 18, cols * 10, 3), np.uint8)
    sheet[:] = np.array([8, 14, 20], np.uint8)
    for i in range(n_glyphs):
        r, c = i // cols, i % cols
        a = atlas[i].astype(np.float32) / 255.0
        cell = np.stack([a * 168 + 8, a * 232 + 14, a * 226 + 20], -1)
        sheet[r * 18:(r + 1) * 18, c * 10:(c + 1) * 10] = cell.astype(np.uint8)
    from PIL import Image
    Image.fromarray(sheet).save(os.path.join(QA, "atlas.png"))
    print("wrote", os.path.join(QA, "atlas.png"))


if __name__ == "__main__":
    main()
