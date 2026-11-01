"""Render still frames (and contact sheets) for scene development.

    python tools/still.py --t 5.0
    python tools/still.py --t 5,10,15 --out qa/still
    python tools/still.py --scene title --n 8 --sheet qa/sheet_title.png
    python tools/still.py --scene all --n 3 --sheet qa/sheet_all.png
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outpath import ensure_parent, ensure_dir  # noqa: E402
sys.path.insert(0, ROOT)

from engine import layout as L          # noqa: E402
from engine import sceneapi            # noqa: E402
from engine.chrome import Chrome       # noqa: E402
from engine.post import get_post       # noqa: E402


def render_frame(t, chrome, assets, reload=False):
    fr, meta, ctx = sceneapi.draw_scene(t, assets, reload=reload)
    full = chrome.build(fr, t, ctx.scene, assets, extra=meta)
    cs = (meta or {}).get("collapse")
    if cs is not None and cs < 0.999:
        full = full.squeezed(cs)
    img = full.compose()
    img = get_post().process(img, int(round(t * L.FPS)), t, meta)
    img = chrome.draw_subtitles(img, t)
    return Image.fromarray(img), ctx


def times_for_scene(key, n):
    for t0, t1, k, mod in sceneapi.SCHEDULE:
        if k == key:
            # sample inside, avoiding the exact boundary
            return [t0 + (t1 - t0) * (i + 0.5) / n for i in range(n)]
    raise SystemExit(f"unknown scene {key}")


def contact_sheet(images, cols, out, scale=0.35, labels=None):
    w = int(L.PX_W * scale)
    h = int(L.PX_H * scale)
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (10, 10, 12))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                               "Fonts", "consola.ttf"), 14)
    except Exception:
        font = ImageFont.load_default()
    for i, im in enumerate(images):
        r, c = i // cols, i % cols
        thumb = im.resize((w, h), Image.LANCZOS)
        sheet.paste(thumb, (c * w, r * h))
        if labels:
            d.text((c * w + 6, r * h + 4), labels[i], font=font, fill=(255, 220, 120))
    ensure_parent(out)
    sheet.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t", default=None, help="comma separated times")
    ap.add_argument("--scene", default=None, help="scene key or 'all'")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--out", default=None)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=float, default=0.35)
    args = ap.parse_args()

    os.makedirs(os.path.join(ROOT, "qa"), exist_ok=True)
    chrome = Chrome()
    assets = sceneapi.A.get_assets()
    imgs, labels = [], []
    if args.scene:
        keys = [k for _, _, k, _ in sceneapi.SCHEDULE] if args.scene == "all" else [args.scene]
        for k in keys:
            for t in times_for_scene(k, args.n):
                im, ctx = render_frame(t, chrome, assets)
                imgs.append(im)
                labels.append(f"{k} {t:6.2f}")
        out = args.sheet or os.path.join(ROOT, "qa", "sheet.png")
        for t, im in zip([None], [None]):
            pass
        contact_sheet(imgs, args.cols, out, args.scale, labels)
        print("wrote", out)
    else:
        ts = [float(x) for x in (args.t or "5").split(",")]
        for t in ts:
            im, ctx = render_frame(t, chrome, assets)
            name = args.out or os.path.join(ROOT, "qa", f"still_{t:07.3f}.png")
            if not os.path.splitext(name)[1]:
                name += ".png"
            if len(ts) > 1:
                base, ext = os.path.splitext(name)
                name = f"{base}_{t:07.3f}{ext or '.png'}"
            ensure_parent(name)
            im.save(name)
            print("wrote", name, "scene=", ctx.scene)


if __name__ == "__main__":
    main()
