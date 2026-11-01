#!/usr/bin/env python
"""Render the whole MV (or a time range) to a 1920x1080 30fps h264 mp4.

Per frame, in parallel workers:
    scene draw -> 45x192 cell stage -> chrome compose -> atlas raster ->
    subtitle PIL overlay -> CRT post -> rgb24 bytes
Main process only orders frames and pipes them into ffmpeg.

Usage:
  python tools/render.py                                    # full -> out/video.mp4
  python tools/render.py --start 0 --end 30                 # range (seconds)
  python tools/render.py --start 55 --end 70 --out out/_t.mp4
  python tools/render.py --sheet qa/shots --start 55 --end 75 --sheet-every 1.0
  python tools/render.py --workers 10 --preset faster
"""
import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import layout as L           # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ffbin import ffmpeg_bin  # noqa: E402

FFMPEG = ffmpeg_bin()

_W = {}


def _init_worker():
    from engine.assets import get_assets
    from engine.chrome import Chrome
    from engine.post import get_post
    _W["assets"] = get_assets()
    _W["chrome"] = Chrome()
    _W["post"] = get_post()


def _render_one(fi):
    """Worker: full frame pipeline -> rgb24 bytes."""
    from engine import sceneapi
    t = fi / L.FPS
    try:
        stage, meta, ctx = sceneapi.draw_scene(t, _W["assets"])
        scene = ctx.scene
    except Exception:
        import traceback
        traceback.print_exc()
        stage, meta, scene = sceneapi.err_frame(t), {"glitch": 0.3}, "error"
    full = _W["chrome"].build(stage, t, scene, _W["assets"], extra=meta)
    cs = (meta or {}).get("collapse")
    if cs is not None and cs < 0.999:
        full = full.squeezed(cs)
    img = full.compose()
    img = _W["post"].process(img, fi, t, meta)
    if not os.environ.get("MV_NOSUB"):
        img = _W["chrome"].draw_subtitles(img, t)
    return fi, img.tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=L.DURATION)
    ap.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 8) - 1))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "video.mp4"))
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--sheet", default=None, help="dump stills prefix instead of video")
    ap.add_argument("--sheet-every", type=float, default=1.0)
    args = ap.parse_args()

    f0 = max(0, int(round(args.start * L.FPS)))
    f1 = min(int(round(L.DURATION * L.FPS)), int(round(args.end * L.FPS)))
    n = f1 - f0
    if n <= 0:
        print("empty range")
        return

    if args.sheet:
        from PIL import Image
        _init_worker()
        stepf = max(1, int(round(args.sheet_every * L.FPS)))
        d = os.path.dirname(args.sheet)
        if d:
            os.makedirs(d, exist_ok=True)
        cnt = 0
        for fi in range(f0, f1, stepf):
            _fi, raw = _render_one(fi)
            import numpy as np
            Image.fromarray(np.frombuffer(raw, np.uint8).reshape(L.PX_H, L.PX_W, 3)).save(
                f"{args.sheet}_{fi / L.FPS:07.3f}.png")
            cnt += 1
        print(f"wrote {cnt} stills -> {args.sheet}_*.png")
        return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{L.PX_W}x{L.PX_H}", "-r", str(L.FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
           "-g", str(L.FPS * 2), "-bf", "2",
           args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=1024 * 1024 * 16)

    t_start = time.time()
    last_report = t_start
    buf = {}
    next_fi = f0

    ctx_pool = mp.get_context("fork") if sys.platform != "win32" else mp.get_context("spawn")
    pool = ctx_pool.Pool(args.workers, initializer=_init_worker)
    try:
        for fi, raw in pool.imap_unordered(_render_one, range(f0, f1), chunksize=1):
            buf[fi] = raw
            while next_fi in buf:
                proc.stdin.write(buf.pop(next_fi))
                next_fi += 1
            now = time.time()
            done = next_fi - f0
            if now - last_report > 3.0 or done == n:
                last_report = now
                el = now - t_start
                rate = done / el if el > 0 else 0
                eta = (n - done) / rate if rate > 0 else 0
                print(f"\r  {done}/{n}  {rate:5.1f} fps  {el:5.0f}s  eta {eta:5.0f}s   ",
                      end="", flush=True)
        print()
    finally:
        pool.close()
        pool.join()
        try:
            proc.stdin.close()
        except Exception:
            pass
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg exited {rc}")
    print(f"wrote {args.out}  ({n} frames, {time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()
