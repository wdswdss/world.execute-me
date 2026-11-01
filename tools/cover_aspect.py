#!/usr/bin/env python
"""One cover design, two aspect ratios: 16:9 (1920x1080) and 4:3 (1440x1080).

Two variants:
  plain : lemniscate + heart + title + MILI credit only  (the default)
  hook  : additionally the gold "大肥鱼眼中的" hook and the song's couplet

The engine grid is cell based (10x18 px cells at SCALE=1), so an aspect ratio is
a different number of columns, not a crop:

    16:9 -> 192 cols x 45 rows -> 1920x1080   (with the film's page chrome)
     4:3 -> 144 cols x 45 rows -> 1440x1080   (same art, clean poster frame)

Usage:
    MV_SCALE=1 python tools/cover_aspect.py --aspect 16x9 --out out/bili_cover
    MV_SCALE=1 python tools/cover_aspect.py --aspect 4x3  --out out/cover_4x3
    MV_SCALE=1 python tools/cover_aspect.py --aspect 16x9 --variant hook --out out/cover_hook
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from engine import layout as L                    # noqa: E402

ASPECTS = {"16x9": (192, 1920), "4x3": (144, 1440)}
HOOK = "大肥鱼眼中的"
COUPLET_EN = "If I approach infinity, then you can be my limitations"
COUPLET_ZH = "若我趋近无穷，你便能成为我的界限"

# inf_w/inf_h keep the lemniscate's 4.09:1 cell aspect
LAYOUT = {
    "16x9": {
        "plain": dict(inf_w=107, inf_h=26, inf_r0=2, title_h=10, title_r0=30,
                      mili_r0=41, hook_r0=25, hook_frac=0.34, chrome=False,
                      stage_top=7),
        "hook": dict(inf_w=90, inf_h=22, inf_r0=2, title_h=10, title_r0=32,
                     mili_r0=43, hook_r0=25, hook_frac=0.34, chrome=True,
                     stage_top=2),
    },
    "4x3": {
        "plain": dict(inf_w=98, inf_h=24, inf_r0=1, title_h=8, title_r0=29,
                      mili_r0=42, hook_r0=25, hook_frac=0.37, chrome=False,
                      stage_top=7),
        "hook": dict(inf_w=86, inf_h=22, inf_r0=2, title_h=8, title_r0=31,
                     mili_r0=40, hook_r0=25, hook_frac=0.37, chrome=False,
                     stage_top=2),
    },
}


def apply_aspect(name):
    cols, px_w = ASPECTS[name]
    L.COLS = cols
    L.STAGE_W = cols
    L.PX_W = px_w
    return cols, px_w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", choices=sorted(ASPECTS), default="16x9")
    ap.add_argument("--variant", choices=("plain", "hook"), default="plain")
    ap.add_argument("--out", required=True, help="output basename (no extension)")
    ap.add_argument("--chrome", type=int, default=-1, help="override: 1/0")
    args = ap.parse_args()

    cols, px_w = apply_aspect(args.aspect)
    cfg = dict(LAYOUT[args.aspect][args.variant])
    if args.chrome >= 0:
        cfg["chrome"] = bool(args.chrome)
    show_hook = args.variant == "hook"

    # engines read L.* at import time -> import them after apply_aspect()
    import cover as C                              # noqa: E402
    from engine import palette as P                # noqa: E402
    from engine import sceneapi                    # noqa: E402
    from engine import timeline as TL              # noqa: E402
    from engine.frame import Frame                 # noqa: E402
    from engine.chrome import Chrome               # noqa: E402
    from engine.post import get_post               # noqa: E402
    from cover_bili_lib import draw_hook, draw_text_line   # noqa: E402

    C.INF_W, C.INF_H = cfg["inf_w"], cfg["inf_h"]
    C.INF_R0, C.INF_C0 = cfg["inf_r0"], (cols - cfg["inf_w"]) // 2
    hero_c = cols // 2
    C.HERO_C = hero_c

    assets = sceneapi.A.get_assets()
    stage = Frame(L.STAGE_H, cols)
    stage.clear(bg=P.C["void"])

    rng = np.random.default_rng(11)
    for _ in range(int(120 * cols / 192) + 20):
        r = int(rng.integers(0, L.STAGE_H))
        c = int(rng.integers(0, cols))
        ch = "+" if rng.random() < 0.25 else "·"
        stage.put(r, c, ch, fg=P.mix(P.C["void2"], P.C["grid"], float(rng.random())))

    C.draw_frame_marks(stage)
    C.draw_side_panels(stage)
    C.draw_infinity(stage, t_light=41.3, gain=1.05)
    C.draw_heart(stage)
    C.draw_artist(stage, r0=cfg["mili_r0"], c0=hero_c)
    C.draw_title(stage, h_cells=cfg["title_h"], r0=cfg["title_r0"], center=hero_c)

    chrome = Chrome()
    if cfg["chrome"]:
        fr = chrome.build(stage, 211.4, "s03_infinity", assets,
                          extra={"sem": "THE LOOP REMAINS"})
        C.draw_footer_wave(fr, assets)
    else:
        fr = _clean_frame(stage, cols, P, Frame, cfg["stage_top"])

    img = fr.compose()
    if show_hook:
        img = draw_hook(img, HOOK, cfg["hook_r0"], rows=5, width_frac=cfg["hook_frac"])

    meta = {"glitch": 0.0, "bloom": 0.55, "grain": 0.7, "shake": (0, 0)}
    img = get_post().process(img, 4444, 38.0, meta)
    d = 3 * L.SCALE
    img[:, :, 0] = np.roll(img[:, :, 0], d, axis=1)
    img[:, :, 2] = np.roll(img[:, :, 2], -d, axis=1)

    if cfg["chrome"] and show_hook:
        _idx, ln = TL.line_at(44.4)
        t_sub = (ln["t1"] - 0.06) if ln else 44.4
        img = chrome.draw_subtitles(img, t_sub)
    elif show_hook:
        img = draw_text_line(img, COUPLET_EN, L.SUB_Y + 2, P.C["white"],
                             size=int(L.CELL_H * 1.30))
        img = draw_text_line(img, COUPLET_ZH, L.SUB_Y + 5, (128, 192, 255),
                             size=int(L.CELL_H * 1.30))

    im = Image.fromarray(img)
    out = args.out
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    ensure_parent(out + ".png")
    im.save(out + ".png")
    im.convert("RGB").save(out + ".jpg", quality=92, subsampling=0)
    im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).save(
        out + "_thumb320.png")
    for ext in (".png", ".jpg"):
        print(f"wrote {out}{ext} {im.size} {os.path.getsize(out + ext) / 1e6:.2f} MB")


def _clean_frame(stage, cols, P, Frame, top):
    """4:3 poster frame: thin rules, no HUD, stage centred vertically."""
    fr = Frame(L.ROWS, cols)
    fr.clear(bg=P.C["void"])
    fr.ch[top:top + L.STAGE_H] = stage.ch
    fr.fg[top:top + L.STAGE_H] = stage.fg
    fr.bg[top:top + L.STAGE_H] = stage.bg

    fr.write(1, 2, "WORLD.EXECUTE(ME);", fg=P.C["primary"])
    fr.rtext(1, "4K60  ·  12954F", fg=P.C["dim"], pad=2)
    for c in range(cols):
        fr.put(3, c, "─", fg=P.C["line"])
        fr.put(top + L.STAGE_H, c, "─", fg=P.C["line"])
    fr.write(top + L.STAGE_H + 2, 2, "MILI", fg=P.C["gold"])
    fr.rtext(top + L.STAGE_H + 2, "UNOFFICIAL FAN MV", fg=P.C["dim"], pad=2)
    return fr


if __name__ == "__main__":
    main()
