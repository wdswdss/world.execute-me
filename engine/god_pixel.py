"""Pure-code pixel-art portrait of the blue-haired "god" girl (grid-native).

This version paints DIRECTLY on the character grid (44 columns x 108 sub-rows,
two sub-rows per cell row) instead of supersampling a vector drawing, so every
edge is crisp and no anti-aliasing mush can appear.

Coordinate convention: x = 0..43 columns, y = 0..107 sub-rows (cell row = y//2).
"""
from __future__ import annotations

import numpy as np

W, H = 44, 54
SS = 2
GH = H * SS                     # 108 sub-rows

# palette indices into PAL
(
    CLEAR, HAIR_D, HAIR, HAIR_M, HAIR_L, HAIR_H,
    SKIN, SKIN_S, SKIN_D, WHITE, WHITE_S, NAVY, NAVY_L, RIBBON,
    EYE_W, IRIS, IRIS_D, PUPIL, SHINE, BLUSH, MOUTH, TONGUE, EAR_IN, BOW,
) = range(24)

PAL = [
    (0, 0, 0),
    (26, 44, 86),      # HAIR_D
    (42, 71, 132),     # HAIR
    (69, 108, 186),    # HAIR_M
    (123, 164, 230),   # HAIR_L
    (197, 221, 251),   # HAIR_H
    (239, 245, 255),   # SKIN
    (201, 220, 240),   # SKIN_S
    (168, 191, 217),   # SKIN_D
    (251, 253, 255),   # WHITE
    (213, 229, 247),   # WHITE_S
    (21, 35, 63),      # NAVY
    (32, 53, 92),      # NAVY_L
    (28, 53, 102),     # RIBBON
    (253, 254, 255),   # EYE_W
    (59, 130, 218),    # IRIS
    (23, 70, 138),     # IRIS_D
    (11, 23, 46),      # PUPIL
    (244, 252, 255),   # SHINE
    (147, 169, 198),   # BLUSH
    (34, 48, 76),      # MOUTH
    (119, 83, 106),    # TONGUE
    (210, 227, 249),   # EAR_IN
    (63, 134, 224),    # BOW
]


def build():
    g = np.zeros((GH, W), np.uint8)

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < GH:
            g[int(y), int(x)] = c

    def rect(x0, y0, x1, y1, c):
        x0, x1 = sorted((int(x0), int(x1)))
        y0, y1 = sorted((int(y0), int(y1)))
        for y in range(max(0, y0), min(GH, y1 + 1)):
            for x in range(max(0, x0), min(W, x1 + 1)):
                g[y, x] = c

    def disc(cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if rx <= 0 or ry <= 0:
                    continue
                dx = (x - cx) / float(rx)
                dy = (y - cy) / float(ry)
                if dx * dx + dy * dy <= 1.0:
                    px(x, y, c)

    def tri(p0, p1, p2, c):
        xs = [p0[0], p1[0], p2[0]]
        ys = [p0[1], p1[1], p2[1]]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            for x in range(int(min(xs)), int(max(xs)) + 1):
                d0 = (p1[0] - p0[0]) * (y - p0[1]) - (p1[1] - p0[1]) * (x - p0[0])
                d1 = (p2[0] - p1[0]) * (y - p1[1]) - (p2[1] - p1[1]) * (x - p1[0])
                d2 = (p0[0] - p2[0]) * (y - p2[1]) - (p0[1] - p2[1]) * (x - p2[0])
                if (d0 >= 0 and d1 >= 0 and d2 >= 0) or (d0 <= 0 and d1 <= 0 and d2 <= 0):
                    px(x, y, c)

    # ---------------- silhouette: long back hair -------------------------
    rect(11, 26, 33, 100, HAIR_D)
    disc(22, 26, 13, 12, HAIR_D)          # crown mass (sub-rows doubled later)
    tri((8, 60), (1, 92), (13, 104), HAIR_D)
    tri((36, 60), (43, 92), (31, 104), HAIR_D)

    # ---------------- dress / shoulders ---------------------------------
    rect(6, 82, 38, 107, NAVY)
    tri((6, 84), (14, 74), (18, 88), NAVY_L)
    tri((38, 84), (30, 74), (26, 88), NAVY_L)

    # ---------------- head ----------------------------------------------
    disc(22, 48, 12, 13, SKIN)            # face mass
    rect(11, 40, 33, 58, SKIN)
    tri((12, 54), (32, 54), (22, 70), SKIN)   # jaw
    disc(11, 50, 2, 6, SKIN_S)            # ear-side shadow
    disc(33, 50, 2, 6, SKIN_S)

    # ---------------- cat ears (outside the hair) -----------------------
    tri((9, 34), (0, 46), (4, 62), HAIR_M)
    tri((8, 36), (2, 46), (6, 58), EAR_IN)
    tri((35, 34), (44, 46), (40, 62), HAIR_M)
    tri((36, 36), (42, 46), (38, 58), EAR_IN)

    # ---------------- hair crown / fringe -------------------------------
    disc(22, 24, 14, 16, HAIR)
    disc(18, 20, 9, 9, HAIR_M)
    disc(16, 17, 5, 5, HAIR_L)
    disc(15, 15, 3, 3, HAIR_H)
    # fringe: a thick fringe over the forehead with a centre parting
    tri((11, 36), (22, 24), (22, 38), HAIR_M)
    tri((33, 36), (22, 24), (22, 38), HAIR_L)
    tri((11, 36), (15, 30), (18, 42), HAIR)
    tri((33, 36), (29, 30), (26, 42), HAIR_L)
    tri((16, 36), (22, 32), (21, 44), HAIR_M)
    # side locks framing the face
    rect(8, 34, 12, 86, HAIR)
    rect(32, 34, 36, 86, HAIR)

    # ---------------- headband ------------------------------------------
    for x in range(10, 35):
        yy = 30 - int(round(5.0 * np.sin((x - 10) / 24.0 * np.pi)))
        rect(x, yy - 1, x, yy + 1, WHITE)
    for k in range(8):
        fx = 11 + k * 3
        fy = 30 - int(round(5.0 * np.sin((fx - 10) / 24.0 * np.pi)))
        disc(fx, fy - 3, 1.5, 1.9, WHITE)
        disc(fx, fy - 3, 0.7, 0.9, WHITE_S)

    # ---------------- eyes: right open, left winking --------------------
    # right eye (viewer right, x ~ 26)
    disc(27, 45, 4.8, 4.6, EYE_W)
    disc(27, 45, 4.0, 3.9, IRIS)
    disc(27, 47, 4.0, 2.2, IRIS_D)
    disc(27, 45, 1.9, 2.0, PUPIL)
    disc(25, 42, 1.4, 1.5, SHINE)
    disc(29, 48, 1.0, 1.1, SHINE)
    # upper lash line
    for x in range(22, 33):
        px(x, 39 - int(abs(x - 27) * 0.35), PUPIL)
    # left eye: winking curve
    for x in range(13, 22):
        t = (x - 13) / 8.0
        yy = 45 - int(round(3.0 * np.sin(t * np.pi)))
        px(x, yy, PUPIL)
        px(x, yy + 1, PUPIL)
    px(12, 43, PUPIL)
    px(13, 42, PUPIL)

    # ---------------- blush / nose / mouth ------------------------------
    disc(14, 52, 3.2, 1.8, BLUSH)
    disc(30, 52, 3.2, 1.8, BLUSH)
    px(22, 50, SKIN_D)
    px(23, 51, SKIN_D)
    disc(22, 57, 2.8, 2.0, MOUTH)
    disc(22, 58, 2.0, 1.1, TONGUE)

    # ---------------- collar + ribbon -----------------------------------
    tri((14, 78), (22, 90), (30, 78), WHITE)
    tri((17, 80), (22, 87), (27, 80), WHITE_S)
    tri((17, 88), (13, 95), (22, 93), RIBBON)
    tri((27, 88), (31, 95), (22, 93), RIBBON)
    disc(22, 91, 1.6, 2.0, BOW)

    return np.repeat(g, 1, axis=0), [tuple(int(v) for v in c) for c in PAL]


_CACHE = {}


def get():
    if "v" not in _CACHE:
        _CACHE["v"] = build()
    return _CACHE["v"]


def preview(path):
    import os
    from PIL import Image
    idx, pal = get()
    rows = []
    cols = []
    for r in range(H):
        top = idx[r * 2]
        bot = idx[r * 2 + 1]
        row = []
        for c in range(W):
            t, b = int(top[c]), int(bot[c])
            ct = pal[t] if t else (8, 14, 26)
            cb = pal[b] if b else (8, 14, 26)
            row.append((ct, cb))
        rows.append(row)
    img = Image.new("RGB", (W * 6, H * 12), (8, 14, 26))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for r, row in enumerate(rows):
        for c, (ct, cb) in enumerate(row):
            d.rectangle([c * 6, r * 12, c * 6 + 5, r * 12 + 5], fill=ct)
            d.rectangle([c * 6, r * 12 + 6, c * 6 + 5, r * 12 + 11], fill=cb)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path)
