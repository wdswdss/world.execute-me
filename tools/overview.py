"""Full-timeline contact sheets — eyeball the whole MV in ~15 images.

    python tools/overview.py                       # every 1.0 s, 4x4 tiles/sheet
    python tools/overview.py --step 0.5 --cols 4 --rows 3 --scale 0.32
    python tools/overview.py --step 0.25 --from 147.8 --to 192.2 --out qa/ov_climax

Renders through exactly the same path as tools/still.py
(draw_scene -> Chrome.build -> Frame.compose -> draw_subtitles -> post),
tiles N frames per sheet and labels every tile with time + scene key.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import traceback

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import still                                    # noqa: E402  (same render path)
from engine import layout as L                  # noqa: E402
from engine import sceneapi                     # noqa: E402

FONT_PATH = os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                         "Fonts", "consola.ttf")


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def render_frame(t, chrome, assets):
    """Return (PIL image, scene key, draw ms or None on error, traceback str)."""
    a = time.perf_counter()
    try:
        im, ctx = still.render_frame(t, chrome, assets)
        return im, ctx.scene, (time.perf_counter() - a) * 1000.0, None
    except Exception:
        tb = traceback.format_exc(limit=3)
        # never stop a full-timeline sweep because one frame raised
        fr = sceneapi.err_frame(t)
        try:
            full = chrome.build(fr, t, sceneapi.scene_at(t)[0], assets)
            im = full.compose()
        except Exception:
            im = Image.new("RGB", (L.PX_W, L.PX_H), (24, 4, 8))
        return im, "ERR", (time.perf_counter() - a) * 1000.0, tb


def make_sheet(tiles, cols, rows, scale, out_path, header):
    tw = max(1, int(L.PX_W * scale))
    th = max(1, int(L.PX_H * scale))
    head = 24
    sheet = Image.new("RGB", (cols * tw, head + rows * th), (8, 8, 10))
    d = ImageDraw.Draw(sheet)
    d.text((8, 5), header, font=_font(15), fill=(120, 220, 230))
    f = _font(14)
    for i, (im, label) in enumerate(tiles):
        r, c = i // cols, i % cols
        thumb = im.resize((tw, th), Image.LANCZOS)
        x, y = c * tw, head + r * th
        sheet.paste(thumb, (x, y))
        d.text((x + 6, y + 4), label, font=f, fill=(255, 220, 120))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    sheet.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=float, default=1.0, help="seconds between frames")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=L.DURATION)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--scale", type=float, default=0.35)
    ap.add_argument("--out", default=os.path.join(ROOT, "qa", "overview"))
    args = ap.parse_args()

    if args.step <= 0:
        raise SystemExit("--step must be > 0")
    per_sheet = max(1, args.cols * args.rows)
    os.makedirs(os.path.join(ROOT, "qa"), exist_ok=True)

    chrome = still.Chrome()
    assets = sceneapi.A.get_assets()
    times = []
    t = args.t_from
    while t <= args.t_to + 1e-9:
        times.append(round(t, 6))
        t += args.step

    n_sheets = (len(times) + per_sheet - 1) // per_sheet
    print(f"[overview] {len(times)} frames  t={times[0]:.2f}..{times[-1]:.2f}  "
          f"step={args.step}  {args.cols}x{args.rows}/sheet -> {n_sheets} sheets")
    t_start = time.perf_counter()
    errors = []
    draw_ms = []
    sheet_tiles, sheet_no = [], 1
    written = []

    def flush():
        nonlocal sheet_tiles, sheet_no
        if not sheet_tiles:
            return
        base, ext = os.path.splitext(args.out)
        path = f"{base}_{sheet_no:02d}{ext or '.png'}"
        hdr = (f"WORLD.EXECUTE(ME);  TIMELINE OVERVIEW  "
               f"{times[first_idx]:.2f} .. {times[first_idx + len(sheet_tiles) - 1]:.2f}s  "
               f"step {args.step}s  sheet {sheet_no}/{n_sheets}")
        make_sheet(sheet_tiles, args.cols, args.rows, args.scale, path, hdr)
        print(f"[overview] wrote {os.path.relpath(path, ROOT)}  ({len(sheet_tiles)} frames)")
        written.append(path)
        sheet_tiles = []
        sheet_no += 1

    first_idx = 0
    for i, t in enumerate(times):
        im, scene, ms, tb = render_frame(t, chrome, assets)
        draw_ms.append((t, scene, ms, bool(tb)))
        if tb:
            errors.append((t, tb))
            print(f"  {t:7.2f}s  ERR  {ms:6.1f} ms  {tb.strip().splitlines()[-1]}")
        else:
            print(f"  {t:7.2f}s  {scene:<12s} {ms:6.1f} ms")
        if not sheet_tiles:
            first_idx = i
        sheet_tiles.append((im, f"{t:7.2f}  {scene}"))
        if len(sheet_tiles) >= per_sheet:
            flush()
    flush()

    total = time.perf_counter() - t_start
    vals = sorted(m for _, _, m, _ in draw_ms)
    med = vals[len(vals) // 2] if vals else 0.0
    mx = vals[-1] if vals else 0.0
    print(f"[overview] done: {len(times)} frames in {total:.1f}s  "
          f"({total / max(1, len(times)) * 1000:.0f} ms/frame)  "
          f"draw median {med:.1f} ms / max {mx:.1f} ms  errors={len(errors)}")
    slow = [(t, sc, ms) for t, sc, ms, bad in draw_ms if not bad and med > 0 and ms > 2.5 * med]
    if slow:
        print(f"[overview] {len(slow)} slow frame(s) (> 2.5x median {med:.1f} ms):")
        for t, sc, ms in slow[:12]:
            print(f"  {t:7.2f}s  {sc:<12s} {ms:7.1f} ms")
        if len(slow) > 12:
            print(f"  ... and {len(slow) - 12} more")
    if errors:
        print(f"[overview] {len(errors)} frame(s) raised:")
        for t, tb in errors[:8]:
            print(f"  {t:7.2f}s  {tb.strip().splitlines()[-1][:110]}")
    print("[overview] sheets: " + ", ".join(os.path.relpath(p, ROOT) for p in written))
    if errors:
        print("[overview] first error traceback:")
        print(errors[0][1])
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
