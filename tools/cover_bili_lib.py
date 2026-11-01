#!/usr/bin/env python
"""Small drawing helpers shared by the cover posters (B站 16:9 / 4:3).

The Chinese hook cannot go through Frame.paint_text(): that rasterises with
Consolas, which has no CJK glyphs. So it is drawn with PIL on the composed RGB
buffer *before* the CRT post pass, which keeps it under the same scanlines and
grain as the ASCII art.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from engine import layout as L
from engine import palette as P
from engine import font as F
from engine import chrome as CH

CJK_FONT = F.YAHEI_B if os.path.exists(F.YAHEI_B) else F.YAHEI


def cjk_mask(text, size, track):
    """Rasterise *text* with letterspacing; returns (L mask, w, h)."""
    font = ImageFont.truetype(CJK_FONT, size)
    adv = [font.getlength(ch) for ch in text]
    w = int(round(sum(adv) + track * max(0, len(text) - 1))) + 8
    h = int(size * 2.2)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    x = 4.0
    for ch, a in zip(text, adv):
        d.text((x, size * 0.16), ch, font=font, fill=255)
        x += a + track
    bb = im.getbbox()
    return (im.crop(bb) if bb else im)


def draw_hook(img, text, r0, rows=5, width_frac=0.34, target=1.0,
              col=(255, 201, 107)):
    """Gold CJK hook line, centred, vertically inside stage rows [r0, r0+rows)."""
    cell_h = L.CELL_H
    box_h = rows * cell_h
    box_top = (L.STAGE_Y + r0) * cell_h
    size = max(20, int(box_h * 0.62))
    track = int(size * 0.20)
    m = cjk_mask(text, size, int(size * 0.20))
    w, h = m.size
    scale = min(int(L.PX_W * width_frac) / max(1, w), box_h * 0.86 / max(1, h))
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    m = m.resize((nw, nh), Image.LANCZOS)
    x0 = (L.PX_W - nw) // 2
    y0 = int(box_top + (box_h - nh) * 0.5)

    mk = np.asarray(m, np.float32) / 255.0
    base = np.asarray(col, np.float32)
    grad = np.linspace(1.10, 0.86, nh, dtype=np.float32)[:, None]
    rgb = np.clip(base[None, None, :] * grad[..., None], 0, 255)

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


def measure(text, size, bold=False):
    """Width in px when every run is drawn with a font that has its glyphs."""
    w = 0.0
    for run, fp in CH._runs(text, bold=bold):
        w += CH._font(fp, size).getlength(run)
    return w


def draw_text_line(img, text, row, color, size=None, bold=False, glow=0.0):
    """One centred line of text at stage row *row* (mixed scripts OK)."""
    if size is None:
        size = int(L.CELL_H * 1.15)
    tw = measure(text, size, bold)
    pil = Image.fromarray(img)
    d = ImageDraw.Draw(pil)
    x = (L.PX_W - tw) * 0.5
    y = (L.STAGE_Y + row) * L.CELL_H + (L.CELL_H - size) * 0.5
    col = tuple(int(c) for c in color)
    if glow > 0:
        g = Image.new("RGBA", pil.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        xx = x
        for run, fp in CH._runs(text, bold=bold):
            gd.text((xx, y), run, font=CH._font(fp, size), fill=col + (255,))
            xx += CH._font(fp, size).getlength(run)
        g = g.filter(ImageFilter.GaussianBlur(max(2.0, size * 0.12)))
        pil = Image.alpha_composite(pil.convert("RGBA"), g).convert("RGB")
        d = ImageDraw.Draw(pil)
    xx = x
    for run, fp in CH._runs(text, bold=bold):
        d.text((xx, y), run, font=CH._font(fp, size), fill=col)
        xx += CH._font(fp, size).getlength(run)
    return np.asarray(pil, np.uint8)
