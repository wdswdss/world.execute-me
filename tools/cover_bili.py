#!/usr/bin/env python
"""B站 投稿封面（16:9, 1920x1080）—— 在 tools/cover.py 的海报帧上做「信息流版」。

差异（手机信息流里缩到 ~340px 宽还要一眼看懂）：
  * 中文钩子「大肥鱼眼中的」单独一行，金色、大字距，占住 TikTok 式的第一眼
  * 主标题更大（10 cells），"ME" 仍是金色
  * 底部一行小字交代硬指标：4K60 / 12954 帧 / 非官方同人
  * 中文用 PIL 直接画在合成图上（paint_text 走 Consolas，没有中日韩字形），
    画在 post 之前，所以扫描线/颗粒会一起作用到字上，不会像贴上去的

Usage:
    MV_SCALE=1 python tools/cover_bili.py --out out/bili_cover.png
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import cover as C                              # noqa: E402
from engine import layout as L                 # noqa: E402
from engine import palette as P                # noqa: E402
from engine import font as F                   # noqa: E402
from engine import sceneapi                    # noqa: E402
from engine import timeline as TL              # noqa: E402
from engine.frame import Frame                 # noqa: E402
from engine.chrome import Chrome               # noqa: E402
from engine.post import get_post               # noqa: E402

HOOK = "大肥鱼眼中的"          # 中文钩子
SUB_TAG = "4K60  ·  12954 FRAMES  ·  UNOFFICIAL FAN MV"
CJK_FONT = F.YAHEI_B if os.path.exists(F.YAHEI_B) else F.YAHEI

# ---- 版面（stage 45 行）----------------------------------------------------
INF_W, INF_H = 90, 22
INF_R0, INF_C0 = 2, 51
HOOK_R0, HOOK_ROWS = 25, 5       # 中文钩子占的行
TITLE_H, TITLE_R0 = 10, 32
MILI_R0 = 43
TAG_R0 = 43


def cjk_mask(text, size, track):
    """Return (L-mode mask, w, h) with letterspacing."""
    font = ImageFont.truetype(CJK_FONT, size)
    adv = []
    for ch in text:
        box = font.getbbox(ch)
        adv.append(font.getlength(ch))
    w = int(round(sum(adv) + track * (len(text) - 1))) + 8
    h = size * 2
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    x = 4.0
    for ch, a in zip(text, adv):
        d.text((x, size * 0.18), ch, font=font, fill=255)
        x += a + track
    bbox = im.getbbox()
    if not bbox:
        return im, w, h
    im = im.crop(bbox)
    return im, im.width, im.height


def draw_hook(img, text=HOOK, rows=HOOK_ROWS, target=1.0):
    """金色中文钩子 + 一圈很淡的光晕，直接画在合成图上（post 前）。"""
    cell_h = L.CELL_H
    box_h = rows * cell_h
    size = max(24, int(box_h * 0.62))
    track = int(size * 0.20)
    m, w, h = cjk_mask(text, size, track)
    # 横向目标宽度：占画面 34%，且不许高出这一条带
    scale = min(int(L.PX_W * 0.34) / max(1, w), box_h * 0.86 / max(1, h))
    nw, nh = int(w * scale), int(h * scale)
    m = m.resize((nw, nh), Image.LANCZOS)
    x0 = (L.PX_W - nw) // 2
    y0 = int((L.STAGE_Y + HOOK_R0) * cell_h + (box_h - nh) * 0.5)

    mk = np.asarray(m, np.float32) / 255.0
    gold = np.asarray(P.C["gold"], np.float32)
    # 竖向渐变：上缘偏白，下缘偏金
    grad = np.linspace(1.10, 0.86, nh, dtype=np.float32)[:, None]
    rgb = np.clip(gold[None, None, :] * grad[..., None], 0, 255)

    glow = Image.fromarray((mk * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(max(2.0, size * 0.10)))
    gk = (np.asarray(glow, np.float32) / 255.0)[..., None] * 0.30

    y1 = min(img.shape[0], y0 + nh)
    x1 = min(img.shape[1], x0 + nw)
    hh, ww = y1 - y0, x1 - x0
    a = mk[:hh, :ww][..., None] * target
    roi = img[y0:y1, x0:x1].astype(np.float32)
    roi = roi * (1 - a) + rgb[:hh, :ww] * a + gk[:hh, :ww] * 255.0
    img[y0:y1, x0:x1] = np.clip(roi, 0, 255).astype(np.uint8)
    return img


def draw_tag(stage, text=SUB_TAG):
    """stage 底部一行硬指标（ASCII，跟着引擎走）。"""
    c0 = (L.COLS - len(text)) // 2
    stage.write(TAG_R0, c0, text, fg=P.mix(P.C["void2"], P.C["dim"], 0.85))


def build():
    assets = sceneapi.A.get_assets()
    C.INF_W, C.INF_H, C.INF_R0, C.INF_C0 = INF_W, INF_H, INF_R0, INF_C0
    C.HEART_W, C.HEART_H = 19, 13

    stage = Frame(L.STAGE_H, L.STAGE_W)
    stage.clear(bg=P.C["void"])

    rng = np.random.default_rng(11)
    for _ in range(140):
        r = int(rng.integers(0, L.STAGE_H))
        c = int(rng.integers(0, L.COLS))
        ch = "+" if rng.random() < 0.25 else "·"
        stage.put(r, c, ch, fg=P.mix(P.C["void2"], P.C["grid"], float(rng.random())))

    C.draw_frame_marks(stage)
    C.draw_side_panels(stage)
    C.draw_infinity(stage, t_light=41.3, gain=1.05)
    C.draw_heart(stage)
    C.draw_artist(stage, r0=MILI_R0)
    C.draw_title(stage, h_cells=TITLE_H, r0=TITLE_R0)

    chrome = Chrome()
    fr = chrome.build(stage, 211.4, "s03_infinity", assets,
                      extra={"sem": "THE LOOP REMAINS"})
    C.draw_footer_wave(fr, assets)

    img = fr.compose()
    img = draw_hook(img)                       # ← 中文钩子，post 前
    meta = {"glitch": 0.0, "bloom": 0.55, "grain": 0.7, "shake": (0, 0)}
    img = get_post().process(img, 4444, 38.0, meta)
    d = 3 * L.SCALE
    img[:, :, 0] = np.roll(img[:, :, 0], d, axis=1)
    img[:, :, 2] = np.roll(img[:, :, 2], -d, axis=1)

    idx, ln = TL.line_at(44.4)
    t_sub = (ln["t1"] - 0.06) if ln else 44.4
    img = chrome.draw_subtitles(img, t_sub)
    return Image.fromarray(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "bili_cover.png"))
    args = ap.parse_args()
    im = build()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    im.save(args.out)
    base = os.path.splitext(args.out)[0]
    im.convert("RGB").save(base + ".jpg", quality=92, subsampling=0)
    im.resize((320, 180), Image.LANCZOS).save(base + "_thumb320.png")
    for ext in (".png", ".jpg"):
        p = base + ext
        print(f"wrote {p} {im.size} {os.path.getsize(p) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
