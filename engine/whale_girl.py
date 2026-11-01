"""Original pixel-art portrait of the DeepSeek whale girl (鲸鱼娘 fan art).

Drawn procedurally (no photo input) so the palette matches the film's
deep-blue terminal look and the figure melts into the background.
Cells are 2 sub-pixels tall, drawn with half-block glyphs by s09.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

W, H = 46, 54            # cell grid (columns x cell rows)
SS = 2                   # sub-pixels per cell row
PX_W, PX_H = W, H * SS   # 46 x 108 drawing canvas

PAL = [
    (0, 0, 0),            # 0 transparent
    (8, 16, 34),          # 1 outline / shadow
    (18, 34, 66),         # 2 navy dress
    (32, 58, 104),        # 3 blue
    (48, 92, 156),        # 4 mid blue
    (84, 146, 208),       # 5 light blue
    (150, 206, 242),      # 6 pale blue
    (226, 240, 252),      # 7 white frill
    (255, 220, 202),      # 8 skin
    (238, 180, 162),      # 9 skin shade
    (236, 116, 148),      # 10 blush / ribbon
    (120, 226, 255),      # 11 cyan rim
    (24, 44, 84),         # 12 hair shadow
    (34, 34, 44),         # 13 eye line
    (60, 120, 190),       # 14 ribbon blue
    (198, 166, 232),      # 15 lavender accent
]

HAIR = (56, 116, 200, 255)
HAIR_D = (30, 62, 120, 255)
HAIR_L = (110, 178, 234, 255)
SKIN = (255, 220, 202, 255)
WHITE = (232, 242, 252, 255)


def build():
    """Return (idx: (H*SS, W) uint8, pal: list[(r,g,b)])."""
    im = Image.new("RGBA", (PX_W, PX_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def el(x0, y0, x1, y1, col):
        d.ellipse([x0, y0, x1, y1], fill=col)

    def poly(pts, col):
        d.polygon(pts, fill=col)

    def line(pts, col, w=2):
        d.line(pts, fill=col, width=w)

    # ================= whale tail (right, behind the shoulder) ==========
    tail = (52, 104, 178, 255)
    tail_d = (26, 56, 112, 255)
    tail_l = (126, 196, 244, 255)
    poly([(30, 74), (38, 66), (41, 76), (34, 90)], tail)            # stalk
    poly([(36, 44), (46, 38), (46, 52), (38, 60)], tail_l)          # upper fluke
    poly([(36, 62), (46, 62), (46, 78), (36, 72)], tail)            # lower fluke
    line([(38, 62), (45, 40)], (200, 240, 255, 255), 1)
    poly([(33, 58), (37, 62), (38, 70), (35, 66)], tail_d)          # notch

    # ================= hair (back mass + side locks) ====================
    el(7, 18, 39, 86, HAIR)
    poly([(8, 40), (6, 66), (10, 92), (16, 94), (14, 66), (15, 44)], HAIR_D)
    poly([(35, 40), (40, 62), (42, 94), (35, 96), (36, 64)], HAIR)
    poly([(39, 40), (42, 66), (44, 92), (40, 94), (40, 62)], HAIR_D)
    poly([(11, 30), (8, 52), (10, 74), (13, 58)], HAIR_L)           # highlight

    # ================= drooping whale ears (floppy, hang beside the head)
    ear = (58, 118, 196, 255)
    ear_d = (32, 72, 138, 255)
    ear_in = (198, 228, 250, 255)
    poly([(8, 30), (3, 40), (6, 52), (12, 46), (13, 34)], ear)
    poly([(7, 34), (5, 43), (8, 48), (11, 44)], ear_in)
    poly([(8, 30), (3, 40), (5, 44)], ear_d)
    poly([(38, 28), (44, 36), (44, 50), (36, 44), (35, 32)], ear)
    poly([(39, 32), (43, 38), (42, 44), (38, 42)], ear_in)
    poly([(43, 30), (45, 40), (44, 46)], ear_d)
    # whale tail flukes on the ear tips (tiny notches)
    poly([(3, 39), (1, 34), (5, 36)], ear_d)
    poly([(45, 36), (46, 31), (42, 34)], ear_d)

    # ================= face =============================================
    skin = SKIN
    skin_s = (238, 180, 162, 255)
    el(15, 24, 35, 56, skin)
    el(17, 46, 33, 58, skin_s)
    poly([(20, 54), (30, 54), (26, 58)], skin_s)

    # fringe over the forehead (several wisps)
    poly([(12, 30), (16, 20), (22, 26), (26, 19), (31, 26), (36, 20), (38, 32),
          (34, 28), (28, 32), (22, 27), (16, 32)], HAIR)
    poly([(24, 24), (34, 22), (37, 28), (28, 30)], HAIR_L)
    poly([(14, 30), (18, 34), (15, 40), (13, 34)], HAIR_D)

    # frilled headband across the crown
    for k in range(11):
        a = math.radians(198 + k * 14.6)
        x = 25 + math.cos(a) * 13.6
        y = 26 + math.sin(a) * 12.2
        el(x - 1.6, y - 1.6, x + 1.6, y + 1.6, WHITE)
        el(x - 0.7, y - 0.7, x + 0.7, y + 0.7, (206, 226, 246, 255))

    # eyes: right big open, left winking
    el(27, 36, 35, 46, (250, 252, 255, 255))
    el(28.2, 37.2, 33.8, 44.6, (24, 32, 48, 255))
    el(28.8, 37.8, 33.2, 43.8, (48, 114, 216, 255))
    el(29.6, 38.6, 31.6, 41.2, (250, 252, 255, 255))
    el(30.2, 41.0, 31.4, 42.4, (150, 220, 255, 255))
    # wink: a soft closed-eye curve + lash
    d.arc([15, 37, 23, 45], 200, 340, fill=(28, 30, 42, 255), width=2)
    line([(15, 41), (14, 39)], (28, 30, 42, 255), 1)
    line([(23, 41), (25, 39)], (28, 30, 42, 255), 1)
    # blush
    el(13.6, 44, 18.4, 47.4, (236, 116, 148, 255))
    el(32, 44, 36.6, 47.4, (232, 108, 140, 255))
    # mouth: small open smile
    d.arc([23, 47, 29, 52], 15, 165, fill=(150, 58, 76, 255), width=2)
    el(25, 50.4, 27, 51.6, (236, 150, 160, 255))

    # ================= collar / ribbon / dress ==========================
    dress = (22, 42, 82, 255)
    dress_l = (40, 72, 128, 255)
    # neck
    poly([(20, 54), (30, 54), (30, 60), (20, 60)], skin_s)
    # shoulders + bodice
    poly([(4, 62), (20, 56), (30, 56), (42, 62), (44, 108), (2, 108)], dress)
    poly([(10, 62), (18, 58), (24, 64), (14, 70)], dress_l)
    # white collar (two lapels)
    poly([(20, 56), (25, 62), (30, 56), (28, 58), (25, 64), (21, 58)], WHITE)
    # ribbon bow
    poly([(18, 60), (25, 64), (18, 69)], (52, 112, 188, 255))
    poly([(32, 60), (25, 64), (32, 69)], (52, 112, 188, 255))
    el(23, 61.6, 27, 66.4, (110, 196, 250, 255))
    el(24.4, 63, 25.6, 65, (226, 244, 255, 255))
    # tail of the ribbon
    poly([(24, 66), (28, 66), (30, 76), (26, 74)], (40, 92, 158, 255))
    poly([(21, 66), (24, 66), (22, 74), (19, 70)], (40, 92, 158, 255))
    # apron
    poly([(15, 74), (33, 74), (35, 100), (13, 100)], WHITE)
    for yy in range(78, 100, 5):
        line([(15, yy), (33, yy)], (204, 220, 236, 255), 1)
    # puff sleeves
    el(1, 64, 12, 84, (36, 70, 126, 255))
    el(38, 64, 45, 84, (30, 60, 112, 255))
    # bodice buttons
    for yy in range(78, 98, 7):
        el(22.2, yy, 24.6, yy + 2.4, (176, 138, 78, 255))

    # rim light on the right silhouette
    for y in range(24, 104, 3):
        x = 42 + int(2.2 * math.sin(y * 0.33))
        d.point((x, y), fill=(150, 226, 255, 255))

    im = im.convert("RGB")
    small = im.resize((W, H * SS), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32)

    pal = np.array([c for c in PAL[1:]], np.float32)
    flat = arr.reshape(-1, 3)
    dist = ((flat[:, None, :] - pal[None, :, :]) ** 2).sum(2)
    near = dist.argmin(1) + 1
    dark = flat.sum(1) < 26
    near = np.where(dark, 0, near).astype(np.uint8)
    return near.reshape(H * SS, W), PAL


_CACHE = {}


def get():
    if "v" not in _CACHE:
        _CACHE["v"] = build()
    return _CACHE["v"]
