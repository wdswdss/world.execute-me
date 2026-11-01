#!/usr/bin/env python
"""Render ONLY the subtitle layer as a PNG sequence with alpha.

The base film is rendered with MV_NOSUB=1 (no subtitles burned in); this layer
is composited over it by tools/compose_subs.py.  Editing a lyric or a colour
therefore costs minutes instead of a full re-render.

Usage:
  python tools/render_subs.py --outdir out/subs_v28
  python tools/render_subs.py --start 60 --end 66 --outdir out/subs_test
"""
import argparse
import multiprocessing as mp
import os
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import layout as L           # noqa: E402

_W = {}


def _init_worker():
    from engine.chrome import Chrome
    _W["chrome"] = Chrome()


def _one(job):
    fi, outdir = job
    t = fi / L.FPS
    zero = np.zeros((L.PX_H, L.PX_W, 3), np.uint8)
    rgb = _W["chrome"].draw_subtitles(zero, t)
    mx = rgb.max(axis=2).astype(np.float32)
    if mx.max() <= 0.0:
        out = np.zeros((L.PX_H, L.PX_W, 4), np.uint8)
    else:
        a = mx / 255.0
        col = np.clip(rgb.astype(np.float32) / np.maximum(a[..., None], 1e-3),
                      0.0, 255.0).astype(np.uint8)
        out = np.empty((L.PX_H, L.PX_W, 4), np.uint8)
        out[..., :3] = col
        out[..., 3] = np.clip(mx, 0, 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(outdir, f"{fi:05d}.png"),
                                      "PNG", compress_level=1)
    return fi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=L.DURATION)
    ap.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 8) - 1))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "out", "subs"))
    args = ap.parse_args()

    f0 = max(0, int(round(args.start * L.FPS)))
    f1 = min(int(round(L.DURATION * L.FPS)), int(round(args.end * L.FPS)))
    os.makedirs(args.outdir, exist_ok=True)

    ctx = mp.get_context("spawn")
    t0 = time.time()
    n = max(1, f1 - f0)
    done = 0
    last = t0
    with ctx.Pool(args.workers, initializer=_init_worker) as pool:
        jobs = [(fi, args.outdir) for fi in range(f0, f1)]
        for _fi in pool.imap_unordered(_one, jobs, chunksize=4):
            done += 1
            now = time.time()
            if now - last > 3.0:
                fps = done / max(1e-6, now - t0)
                print(f"  {done}/{n}", f"{fps:.1f} fps", f"eta {(n-done)/max(0.1,fps):.0f}s",
                      end="\r", flush=True)
                last = now
    print()
    print(f"wrote {n} PNG frames into {args.outdir}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
