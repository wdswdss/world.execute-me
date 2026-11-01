"""Design sheet v2: the "god girl" (大肥鱼 style) as pure-code pixel art.

Native pixel canvas 128x160, layered construction, three variants.
Run: python tools/god_design.py
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CW, CH = 128, 160

PAL = [
    (0, 0, 0),          # 0 clear
    (10, 16, 34),       # 1 outline
    (22, 36, 70),       # 2 hair deep shadow
    (34, 56, 106),      # 3 hair dark
    (48, 78, 142),      # 4 hair base
    (68, 104, 176),     # 5 hair mid
    (96, 136, 206),     # 6 hair light
    (140, 178, 236),    # 7 hair highlight
    (196, 222, 252),    # 8 hair shine
    (252, 253, 255),    # 9 white
    (226, 237, 250),    # 10 white shade
    (247, 250, 255),    # 11 skin
    (236, 220, 220),    # 12 skin shade
    (216, 190, 196),    # 13 skin deep
    (16, 26, 50),       # 14 navy
    (26, 41, 76),       # 15 navy light
    (38, 60, 106),      # 16 navy hi
    (250, 253, 255),    # 17 sclera
    (58, 130, 222),     # 18 iris
    (24, 82, 168),      # 19 iris deep
    (8, 16, 34),        # 20 pupil/lash
    (255, 255, 255),    # 21 specular
    (247, 158, 178),    # 22 blush
    (140, 74, 100),     # 23 mouth
    (208, 74, 96),      # 24 tongue
    (255, 216, 128),    # 25 halo gold
    (255, 240, 186),    # 26 halo light
    (255, 194, 104),    # 27 beam
    (226, 158, 78),     # 28 beam dim
    (62, 138, 234),     # 29 ribbon
    (40, 100, 190),     # 30 ribbon deep
    (206, 230, 252),    # 31 fin inner
    (176, 205, 240),    # 32 hair shadow line
    (255, 176, 196),    # 33 blush light
    (250, 190, 205),    # 34 ear inner
    (238, 96, 128),     # 35 heart
    (176, 52, 78),      # 36 heart deep
    (255, 214, 224),    # 37 heart shine
]


class C:
    def __init__(self, w=CW, h=CH):
        self.w, self.h = w, h
        self.g = np.zeros((h, w), np.int16)

    def put(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y, x] = c

    def rect(self, x0, y0, x1, y1, c):
        x0, x1 = sorted((int(x0), int(x1)))
        y0, y1 = sorted((int(y0), int(y1)))
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w - 1, x1), min(self.h - 1, y1)
        if x0 <= x1 and y0 <= y1:
            self.g[y0:y1 + 1, x0:x1 + 1] = c

    def ell(self, cx, cy, rx, ry, c):
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
            dy = (y + 0.5 - cy) / ry
            if abs(dy) > 1.0:
                continue
            span = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            a, b = int(round(cx - span)), int(round(cx + span))
            a, b = max(0, a), min(self.w - 1, b)
            if a <= b:
                self.g[y, a:b + 1] = c

    def ring(self, cx, cy, rx, ry, thick, c):
        for y in range(max(0, int(cy - ry) - 2), min(self.h, int(cy + ry) + 3)):
            for x in range(max(0, int(cx - rx) - 2), min(self.w, int(cx + rx) + 3)):
                dx = (x + 0.5 - cx) / rx
                dy = (y + 0.5 - cy) / ry
                r = dx * dx + dy * dy
                if (1.0 - thick) <= r <= 1.0:
                    self.put(x, y, c)

    def tri(self, p0, p1, p2, c):
        xs = [p0[0], p1[0], p2[0]]
        ys = [p0[1], p1[1], p2[1]]
        for y in range(max(0, int(min(ys))), min(self.h, int(max(ys)) + 1)):
            for x in range(max(0, int(min(xs))), min(self.w, int(max(xs)) + 1)):
                x0, y0 = p0
                x1, y1 = p1
                x2, y2 = p2
                d0 = (x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)
                d1 = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
                d2 = (x0 - x2) * (y - y2) - (y0 - y2) * (x - x2)
                if (d0 >= 0 and d1 >= 0 and d2 >= 0) or (d0 <= 0 and d1 <= 0 and d2 <= 0):
                    self.put(x, y, c)

    def poly(self, pts, c):
        for i in range(len(pts) - 2):
            self.tri(pts[0], pts[i + 1], pts[i + 2], c)

    def line(self, p0, p1, c, thick=1):
        x0, y0 = p0
        x1, y1 = p1
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            t = i / max(1, n - 1)
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            for dy in range(thick):
                self.put(x, y + dy, c)

    def clip_above(self, y_max, code=0):
        """clear everything above y_max (used to trim stray shapes)"""
        self.g[:max(0, y_max), :] = np.where(self.g[:max(0, y_max), :] == code, 0, self.g[:max(0, y_max), :])


def beaming(c, cx, cy, with_halo=True, with_beams=True):
    if with_beams:
        for k in range(44):
            a = k / 44.0 * 2 * math.pi + 0.05
            ln = 96 if k % 2 == 0 else 66
            for q in range(46, ln):
                x = int(cx + math.cos(a) * q)
                y = int(cy + math.sin(a) * q * 0.94)
                if 18 <= x <= 110 and 10 <= y <= 158:
                    continue
                c.put(x, y, 27 if q < ln - 16 else 28)
    if with_halo:
        c.ring(cx, 30, 46, 11, 0.10, 25)
        c.ring(cx, 30, 46, 8, 0.16, 26)
        for k in range(28):
            a = k / 28.0 * 2 * math.pi
            c.put(cx + math.cos(a) * 30, 30 + math.sin(a) * 5, 26)


def sprite(with_beams=True, with_halo=True, smile="open"):
    c = C()
    CX = 64
    beaming(c, CX, 80, with_halo=with_halo, with_beams=with_beams)

    # ---------------- back hair ----------------
    c.ell(CX, 74, 45, 56, 3)
    c.ell(CX, 68, 42, 50, 4)
    c.ell(CX, 60, 37, 40, 4)

    # ---------------- dress / shoulders ----------------
    c.ell(CX, 162, 54, 36, 14)
    c.tri((20, 134), (44, 116), (46, 164), 15)
    c.tri((108, 134), (84, 116), (82, 164), 15)
    # puffy maid sleeve caps
    for side in (-1, 1):
        c.ell(CX + side * 34, 130, 10, 8, 15)
        c.ell(CX + side * 34, 127, 8, 5.4, 14)
        c.ell(CX + side * 34, 134, 7, 3.2, 9)
    # white apron
    c.tri((47, 140), (81, 140), (64, 162), 9)
    c.tri((51, 142), (77, 142), (64, 160), 10)

    # ---------------- cupped hands holding a cracked heart ----------------
    for side in (-1, 1):
        # forearm coming forward from the puff sleeve
        c.poly([(CX + side * 40, 136), (CX + side * 26, 140), (CX + side * 20, 152),
                (CX + side * 36, 150)], 15)
        c.poly([(CX + side * 38, 138), (CX + side * 27, 142), (CX + side * 22, 150),
                (CX + side * 35, 148)], 16)
    # broken heart (two lobes + point, with a jagged crack)
    c.ell(CX - 5, 138, 6.5, 6.0, 35)
    c.ell(CX + 5, 138, 6.5, 6.0, 35)
    c.tri((CX - 11, 141), (CX + 11, 141), (CX, 154), 35)
    c.ell(CX - 6, 136, 2.6, 2.0, 37)
    c.ell(CX + 4, 136, 2.0, 1.6, 36)
    for (cx0, cy0, cx1, cy1) in ((CX + 1, 131, CX - 2, 137), (CX - 2, 137, CX + 3, 141),
                                 (CX + 3, 141, CX - 1, 146), (CX - 1, 146, CX + 2, 153)):
        c.line((cx0, cy0), (cx1, cy1), 1, 1)
    # hands cupping underneath
    for side in (-1, 1):
        c.ell(CX + side * 12, 152, 6.5, 5.0, 11)
        c.ell(CX + side * 12, 150, 5.0, 3.0, 12)
        for k in range(3):
            c.put(CX + side * (9 + k * 3), 148, 13)


    # ---------------- neck + face ----------------
    c.rect(57, 98, 71, 116, 12)
    c.ell(CX, 76, 27.5, 28, 11)
    c.rect(40, 62, 88, 86, 11)
    c.tri((40, 84), (88, 84), (CX, 103), 11)
    c.ell(40, 80, 4.5, 9, 12)      # cheek shading
    c.ell(88, 80, 4.5, 9, 12)
    c.ell(CX, 100, 13, 5, 12)      # chin shading

    # ---------------- eyes ----------------
    ex, ey = 83, 78
    c.ell(ex, ey, 11.0, 11.8, 20)
    c.ell(ex, ey, 10.0, 10.8, 17)
    c.ell(ex, ey + 1, 8.8, 9.2, 18)
    c.ell(ex, ey + 4, 8.6, 5.6, 19)
    c.ell(ex, ey + 1, 3.8, 4.4, 20)
    c.ell(ex - 3, ey - 4, 3.6, 3.8, 21)
    c.ell(ex + 4, ey + 5, 1.8, 1.8, 21)
    for x in range(ex - 12, ex + 13):
        t = (x - ex) / 11.0
        y = ey - 10 + int(round(2.4 * t * t))
        c.put(x, y, 20)
        c.put(x, y - 1, 20)
    c.line((ex + 12, ey - 11), (ex + 17, ey - 16), 20, 2)
    c.line((ex - 9, ey - 20), (ex + 9, ey - 23), 12, 2)
    # left wink
    wx0, wx1 = 45, 63
    for x in range(wx0, wx1 + 1):
        t = (x - wx0) / float(wx1 - wx0)
        y = ey - 1 - int(round(5.0 * math.sin(t * math.pi)))
        c.put(x, y, 20)
        c.put(x, y + 1, 20)
    c.line((wx0 - 1, ey - 1), (wx0 - 6, ey - 2), 20, 1)
    c.line((wx1 + 1, ey - 1), (wx1 + 6, ey - 2), 20, 1)
    c.line((wx0 - 7, ey - 20), (wx1 + 5, ey - 22), 12, 2)

    # ---------------- blush / nose / mouth ----------------
    for (bx, by, r) in ((CX - 18, 93, 3), (CX + 18, 93, 3)):
        for y in range(by - 3, by + 4):
            for x in range(bx - r, bx + r + 1):
                if ((x - bx) / float(r)) ** 2 + ((y - by) / 3.2) ** 2 <= 1.0 and (x + y) % 3:
                    c.put(x, y, 22 if (x + y) % 2 else 33)
    c.put(CX, 87, 12)
    c.put(CX + 1, 88, 13)
    if smile == "open":
        c.ell(CX, 95, 5.6, 4.0, 23)
        c.ell(CX, 96, 3.6, 1.8, 24)
        c.ell(CX, 91, 5.6, 1.2, 20)
        c.put(CX - 4, 91, 9)
        c.put(CX - 4, 92, 9)
    else:
        for x in range(CX - 6, CX + 7):
            t = (x - CX) / 6.0
            c.put(x, 97 - int(round(2.0 * (1 - t * t))), 23)
    for (sx, sy) in ((CX + 8, 96), (CX + 9, 97), (CX + 8, 98)):
        c.put(sx, sy, 20)

    # ---------------- bangs: fill from the crown down to a zigzag hairline ----------------
    tips = [(33, 62), (40, 56), (47, 66), (55, 54), (64, 70), (73, 54), (81, 66),
            (88, 56), (95, 62)]

    def hairline(x):
        for k in range(len(tips) - 1):
            x0, y0 = tips[k]
            x1, y1 = tips[k + 1]
            if x0 <= x <= x1:
                t = (x - x0) / float(max(1, x1 - x0))
                return y0 + (y1 - y0) * t
        return tips[-1][1]

    # solid hair plate behind the locks, rounded to the crown ellipse
    for x in range(32, 96):
        for y in range(16, 67):
            dx = (x - CX) / 45.0
            dy = (y - 74) / 56.0
            if dx * dx + dy * dy > 1.0:
                continue
            c.put(x, y, 4 if y > 30 else 5)
    for x in range(32, 96):
        yb = hairline(x)
        for y in range(16, int(round(yb)) + 1):
            dx = (x - CX) / 45.0
            dy = (y - 74) / 56.0
            if dx * dx + dy * dy > 1.0:
                continue
            col = 6 if y < 26 else (5 if y < 42 else 4)
            c.put(x, y, col)
    # point highlights inside the fringe
    for (hx0, hy0, hx1, hy1) in ((37, 30, 40, 52), (60, 26, 62, 44),
                                 (70, 26, 68, 44), (87, 30, 84, 52)):
        c.line((hx0, hy0), (hx1, hy1), 6, 1)
    # darker separation cuts between the bang locks
    for (sx, sy) in ((47, 26), (55, 24), (73, 24), (81, 26)):
        c.line((sx, sy), (sx + 1, 52), 3, 1)
    # side bangs framing the cheeks
    c.poly([(32, 50), (41, 56), (38, 86), (28, 78)], 4)
    c.poly([(96, 50), (87, 56), (90, 86), (100, 78)], 4)
    c.poly([(34, 54), (39, 58), (37, 80), (32, 74)], 5)
    c.poly([(94, 54), (89, 58), (91, 80), (96, 74)], 5)

    # ---------------- frilled headband ----------------
    for x in range(22, 107):
        t = (x - 22) / 84.0
        y = 42 - int(round(16.0 * math.sin(t * math.pi) ** 0.9))
        c.rect(x, y, x, y + 2, 9)
        c.rect(x, y + 2, x, y + 3, 10)
    for k in range(14):
        fx = 24 + k * 6
        t = (fx - 22) / 84.0
        fy = 42 - int(round(16.0 * math.sin(max(0.0, min(1.0, t)) * math.pi) ** 0.9))
        c.ell(fx, fy - 4, 3.8, 4.2, 10)
        c.ell(fx, fy - 4, 2.8, 3.2, 9)
    # ribbon on the headband (right)
    c.poly([(96, 34), (113, 27), (111, 44), (98, 40)], 29)
    c.poly([(97, 39), (111, 45), (99, 52)], 30)
    c.ell(98, 41, 2.6, 3.0, 29)
    c.ell(98, 41, 1.3, 1.5, 9)

    # ---------------- cat ears: sideways right triangles, white outer quarter ----------------
    def _in_tri(px_, py_, A, B, T):
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1 = sign((px_, py_), A, B)
        d2 = sign((px_, py_), B, T)
        d3 = sign((px_, py_), T, A)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    for side in (-1, 1):
        A = (CX + side * 26, 34)      # inner top
        B = (CX + side * 26, 56)      # inner bottom (vertical edge on the head)
        T = (CX + side * 58, 60)      # outward tip (kept inside the canvas)
        inner_x = CX + side * 30
        span = 32.0
        xs = [A[0], B[0], T[0]]
        white_from = 50
        for y in range(32, 60):
            for x in range(min(xs) - 1, max(xs) + 2):
                if not _in_tri(x, y, A, B, T):
                    continue
                if y <= 35 or y >= 57 or x in (min(xs), max(xs)):
                    col = 3
                elif y >= white_from:
                    col = 9 if (x + y) % 5 else 10
                else:
                    col = 6 if y <= 44 else 5
                c.put(x, y, col)
        # rim light along the slanting top edge
        for k in range(3, 26):
            x = int(round(inner_x + side * k))
            y = 36 + int(round(k * 0.42))
            if _in_tri(x, y, A, B, T):
                c.put(x, y, 7)

    # ---------------- collar + bow + whale-tail charm ----------------
    c.tri((44, 116), (CX, 130), (84, 116), 9)
    c.tri((50, 118), (CX, 126), (78, 118), 10)
    c.poly([(52, 120), (38, 130), (60, 128)], 14)
    c.poly([(76, 120), (90, 130), (68, 128)], 14)
    c.ell(CX, 124, 4.4, 4.8, 29)
    c.ell(CX, 124, 2.0, 2.2, 9)
    c.tri((CX - 6, 136), (CX - 14, 132), (CX - 12, 142), 16)
    c.tri((CX - 6, 136), (CX - 10, 144), (CX - 2, 142), 16)
    c.put(CX - 6, 136, 31)

    return c


def to_rgba(c, k):
    pal = np.array(PAL, np.uint8)
    rgb = pal[np.clip(c.g, 0, len(PAL) - 1)]
    a = (c.g > 0).astype(np.uint8) * 255
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    am = Image.fromarray(a, "L")
    return img.resize((c.w * k, c.h * k), Image.NEAREST), am.resize((c.w * k, c.h * k), Image.NEAREST)


def sheet(path, variants, k=4):
    bg = (7, 11, 20)
    pad, title = 26, 52
    cellw, cellh = CW * k, CH * k
    sheet_w = pad + len(variants) * (cellw + pad)
    sheet_h = title + cellh + pad
    out = Image.new("RGB", (sheet_w, sheet_h), bg)
    d = ImageDraw.Draw(out)
    for x in range(0, sheet_w, 32):
        d.line([(x, 0), (x, sheet_h)], fill=(11, 17, 29))
    for y in range(0, sheet_h, 32):
        d.line([(0, y), (sheet_w, y)], fill=(11, 17, 29))
    try:
        f = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 22)
    except Exception:
        f = ImageFont.load_default()
    for i, (label, cv) in enumerate(variants):
        img, am = to_rgba(cv, k)
        bx = pad + i * (cellw + pad)
        out.paste(img, (bx, title), am)
        d.text((bx + 4, 18), label, font=f, fill=(130, 205, 240))
    out.save(path)
    print("wrote", path)


def main():
    a = sprite(with_beams=True, with_halo=True)
    b = sprite(with_beams=False, with_halo=True)
    c = sprite(with_beams=False, with_halo=False, smile="closed")
    sheet("qa/god_design_sheet.png",
          [("A / 圣光 + 光环（推荐）", a),
           ("B / 光环（无光束）", b),
           ("C / 日常版（无光环、微笑）", c)])


if __name__ == "__main__":
    main()
