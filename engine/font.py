from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from engine import layout as _L
CELL_W = _L.CELL_W
CELL_H = _L.CELL_H
FONT_SIZE = int(round(16 * _L.SCALE))
BASELINE = int(round(14 * _L.SCALE))

# --- font discovery -------------------------------------------------------
# The engine rasterises every glyph itself, so it needs real outline fonts.
# The ones the artwork was drawn with (Consolas, Microsoft YaHei, Malgun
# Gothic) are proprietary and are NOT shipped with this repo.  We look for
# them - or a substitute - in this order:
#
#   1. $ASCIIMV_FONTS       extra dirs, ':' or ';' separated
#   2. <repo>/fonts/        drop your own .ttf/.ttc here (git-ignored)
#   3. the platform font directories below
#
# Each role takes the first file that exists, so a stock Linux box will run
# with DejaVu / Noto substitutes: glyph shapes differ slightly, the 10x18 cell
# grid (and therefore every layout constant) does not.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _font_dirs():
    dirs = []
    env = os.environ.get("ASCIIMV_FONTS", "")
    for d in env.replace(";", os.pathsep).split(os.pathsep):
        if d.strip():
            dirs.append(d.strip())
    dirs.append(os.path.join(_REPO_ROOT, "fonts"))
    dirs += [
        r"C:\Windows\Fonts",
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
        "/usr/share/fonts",
        "/usr/share/fonts/truetype",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.local/share/fonts"),
        os.path.expanduser("~/.fonts"),
    ]
    return [d for d in dirs if os.path.isdir(d)]


@lru_cache(maxsize=None)
def _font_index():
    """basename(lower) -> path, walking the font dirs two levels deep."""
    idx = {}
    for d in _font_dirs():
        base = d.rstrip(os.sep).count(os.sep)
        for root, subdirs, files in os.walk(d):
            if root.rstrip(os.sep).count(os.sep) - base >= 2:
                subdirs[:] = []
            for f in files:
                if f.lower().endswith((".ttf", ".ttc", ".otf")):
                    idx.setdefault(f.lower(), os.path.join(root, f))
    return idx


def font_path(*names):
    """First installed font among *names* (case-insensitive); '' if none."""
    idx = _font_index()
    for n in names:
        p = idx.get(n.lower())
        if p:
            return p
    return ""


WIN_FONTS = r"C:\Windows\Fonts"
CONSOLA = font_path("consola.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",
                    "NotoSansMono-Regular.ttf", "Menlo.ttc", "cour.ttf")
CONSOLA_B = font_path("consolab.ttf", "DejaVuSansMono-Bold.ttf",
                      "LiberationMono-Bold.ttf", "NotoSansMono-Bold.ttf", "Menlo.ttc",
                      "courbd.ttf") or CONSOLA
SEGUISYM = font_path("seguisym.ttf", "DejaVuSans.ttf", "NotoSansSymbols-Regular.ttf",
                     "Symbola.ttf", "NotoSansSymbols2-Regular.ttf") or CONSOLA
ARIAL = font_path("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
                  "NotoSans-Regular.ttf") or CONSOLA
ARIAL_B = font_path("arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                    "NotoSans-Bold.ttf") or ARIAL
YAHEI = font_path("msyh.ttc", "NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf",
                  "PingFang.ttc", "Hiragino Sans GB.ttc", "wqy-microhei.ttc",
                  "DroidSansFallbackFull.ttf") or CONSOLA
YAHEI_B = font_path("msyhbd.ttc", "NotoSansCJK-Bold.ttc", "NotoSansCJKsc-Bold.otf",
                    "PingFang.ttc", "wqy-microhei.ttc") or YAHEI
MALGUN = font_path("malgun.ttf", "AppleSDGothicNeo.ttc", "NotoSansCJK-Regular.ttc",
                   "NotoSansKR-Regular.otf") or YAHEI
MALGUN_B = font_path("malgunbd.ttf", "AppleSDGothicNeo-Bold.ttc",
                     "NotoSansCJK-Bold.ttc", "NotoSansKR-Bold.otf") or MALGUN

BOX_CHARS = (
    "─│┌┐└┘├┤┬┴┼╭╮╰╯═║╔╗╚╝╠╣╦╩╬"
    "━┃┏┓┗┛┣┫┳┻╋"
    "╱╲╳"
)
BLOCK_CHARS = "▁▂▃▄▅▆▇█▀▄░▒▓▔▏▎▍▌▋▊▉▕"
QUAD_CHARS = "▖▗▘▙▚▛▜▝▞▟"
SYMBOL_CHARS = (
    "●○◉◯◍◎◆◇◈■□▪▫▲▼◀▶★☆✦✧⚡♥♡♪♫∞≈≠≤≥±×÷∑ΔπΩ√∫∂←→↑↓↔↕⇒⇐⇔↻↺⟳⟲✓✗✕✔✘·•∙°′″‰⌁⚑⚐"
)
MISC_CHARS = "☰☷⏻⏼⏸⏹⏺⌘⌂§¶©®™※⎔⌬⌖⌗⌦⌫"
EXTRA_CHARS = "╨…▸—▐›◂"
BRAILLE_CHARS = "".join(chr(0x2800 + i) for i in range(256))


def _blank():
    return np.zeros((CELL_H, CELL_W), np.uint8)


def _put(mask, x, y, v=255):
    if 0 <= y < CELL_H and 0 <= x < CELL_W:
        mask[y, x] = v


def _rect(mask, x0, y0, x1, y1, v=255):
    x0, x1 = max(0, int(x0)), min(CELL_W - 1, int(x1))
    y0, y1 = max(0, int(y0)), min(CELL_H - 1, int(y1))
    if x1 >= x0 and y1 >= y0:
        mask[y0:y1 + 1, x0:x1 + 1] = v


# --- box drawing ------------------------------------------------------------

# (left, right, up, down) with 0=none, 1=single, 2=double, 3=heavy
BOX_EDGES = {
    "─": (1, 1, 0, 0), "│": (0, 0, 1, 1),
    "┌": (0, 1, 0, 1), "┐": (1, 0, 0, 1),
    "└": (0, 1, 1, 0), "┘": (1, 0, 1, 0),
    "├": (0, 1, 1, 1), "┤": (1, 0, 1, 1),
    "┬": (1, 1, 0, 1), "┴": (1, 1, 1, 0),
    "┼": (1, 1, 1, 1),
    "╭": (0, 1, 0, 1), "╮": (1, 0, 0, 1),
    "╰": (0, 1, 1, 0), "╯": (1, 0, 1, 0),
    "═": (2, 2, 0, 0), "║": (0, 0, 2, 2),
    "╔": (0, 2, 0, 2), "╗": (2, 0, 0, 2),
    "╚": (0, 2, 2, 0), "╝": (2, 0, 2, 0),
    "╠": (0, 2, 2, 2), "╣": (2, 0, 2, 2),
    "╦": (2, 2, 0, 2), "╩": (2, 2, 2, 0),
    "╬": (2, 2, 2, 2),
    "━": (3, 3, 0, 0), "┃": (0, 0, 3, 3),
    "┏": (0, 3, 0, 3), "┓": (3, 0, 0, 3),
    "┗": (0, 3, 3, 0), "┛": (3, 0, 3, 0),
    "┣": (0, 3, 3, 3), "┫": (3, 0, 3, 3),
    "┳": (3, 3, 0, 3), "┻": (3, 3, 3, 0),
    "╋": (3, 3, 3, 3),
    "╱": (-1, -1, -1, -1), "╲": (-2, -2, -2, -2), "╳": (-3, -3, -3, -3),
}


def _box_mask(ch):
    left, right, up, down = BOX_EDGES[ch]
    m = _blank()
    if left == -1:  # diagonal /
        for i in range(CELL_H):
            x = int(round(i * (CELL_W - 1) / (CELL_H - 1)))
            _put(m, x, CELL_H - 1 - i)
        return m
    if left == -2:  # diagonal \
        for i in range(CELL_H):
            x = int(round(i * (CELL_W - 1) / (CELL_H - 1)))
            _put(m, x, i)
        return m
    if left == -3:  # X
        for i in range(CELL_H):
            x = int(round(i * (CELL_W - 1) / (CELL_H - 1)))
            _put(m, x, i)
            _put(m, x, CELL_H - 1 - i)
        return m
    cx, cy = 5, 9
    # singles: full-span lines through the centre
    if left == 1 or right == 1:
        if left == 1 and right == 1:
            _rect(m, 0, cy, CELL_W - 1, cy)
        elif left == 1:
            _rect(m, 0, cy, cx, cy)
        else:
            _rect(m, cx, cy, CELL_W - 1, cy)
    if up == 1 or down == 1:
        if up == 1 and down == 1:
            _rect(m, cx, 0, cx, CELL_H - 1)
        elif up == 1:
            _rect(m, cx, 0, cx, cy)
        else:
            _rect(m, cx, cy, cx, CELL_H - 1)
    # doubles: 2 parallel lines, outer meet at the cell border
    if left == 2 or right == 2:
        ys = (8, 10)
        if left == 2 and right == 2:
            for y in ys:
                _rect(m, 0, y, CELL_W - 1, y)
        elif left == 2:
            for y in ys:
                _rect(m, 0, y, 4 if up or down else cx, y)
        else:
            for y in ys:
                _rect(m, 4 if up or down else cx, y, CELL_W - 1, y)
    if up == 2 or down == 2:
        xs = (4, 6)
        if up == 2 and down == 2:
            for x in xs:
                _rect(m, x, 0, x, CELL_H - 1)
        elif up == 2:
            for x in xs:
                _rect(m, x, 0, x, 8)
        else:
            for x in xs:
                _rect(m, x, 8, x, CELL_H - 1)
    if right == 2 and down == 2:   # ╔ join
        _put(m, 4, 8)
    if left == 2 and down == 2:    # ╗
        _put(m, 6, 8)
    if right == 2 and up == 2:     # ╚
        _put(m, 4, 10)
    if left == 2 and up == 2:      # ╝
        _put(m, 6, 10)
    # heavy: 2px lines
    if left == 3 or right == 3:
        ys = (8, 9)
        if left == 3 and right == 3:
            for y in ys:
                _rect(m, 0, y, CELL_W - 1, y)
        elif left == 3:
            for y in ys:
                _rect(m, 0, y, cx, y)
        else:
            for y in ys:
                _rect(m, cx, y, CELL_W - 1, y)
    if up == 3 or down == 3:
        xs = (4, 5)
        if up == 3 and down == 3:
            for x in xs:
                _rect(m, x, 0, x, CELL_H - 1)
        elif up == 3:
            for x in xs:
                _rect(m, x, 0, x, cy)
        else:
            for x in xs:
                _rect(m, x, cy, x, CELL_H - 1)
    return m


# --- block elements ---------------------------------------------------------

def _block_mask(ch):
    m = _blank()
    if ch == "█":
        _rect(m, 0, 0, CELL_W - 1, CELL_H - 1)
    elif ch == "▀":
        _rect(m, 0, 0, CELL_W - 1, CELL_H // 2 - 1)
    elif ch == "▄":
        _rect(m, 0, CELL_H // 2, CELL_W - 1, CELL_H - 1)
    elif ch == "▔":
        _rect(m, 0, 0, CELL_W - 1, 1)
    elif ch == "░":
        for y in range(CELL_H):
            for x in range(0, CELL_W, 2):
                _put(m, x + (y % 2), y, 200)
    elif ch == "▒":
        for y in range(CELL_H):
            for x in range(CELL_W):
                if (x + y) % 2 == 0:
                    _put(m, x, y, 230)
    elif ch == "▓":
        for y in range(CELL_H):
            for x in range(CELL_W):
                if (x + y) % 2 == 1:
                    _put(m, x, y, 255)
    elif ch in "▁▂▃▄▅▆▇█":
        k = "▁▂▃▄▅▆▇█".index(ch) + 1
        hh = int(round(k * CELL_H / 8))
        _rect(m, 0, CELL_H - hh, CELL_W - 1, CELL_H - 1)
    elif ch in "▏▎▍▌▋▊▉":
        k = "▏▎▍▌▋▊▉".index(ch) + 1
        ww = int(round(k * CELL_W / 8))
        _rect(m, 0, 0, ww - 1, CELL_H - 1)
    elif ch == "▕":
        _rect(m, 1, 0, CELL_W - 1, CELL_H - 1)
    elif ch == "▖":
        _rect(m, 0, CELL_H // 2, CELL_W // 2 - 1, CELL_H - 1)
    elif ch == "▗":
        _rect(m, CELL_W // 2, CELL_H // 2, CELL_W - 1, CELL_H - 1)
    elif ch == "▘":
        _rect(m, 0, 0, CELL_W // 2 - 1, CELL_H // 2 - 1)
    elif ch == "▝":
        _rect(m, CELL_W // 2, 0, CELL_W - 1, CELL_H // 2 - 1)
    elif ch == "▙":
        _rect(m, 0, CELL_H // 2, CELL_W // 2 - 1, CELL_H - 1)
        _rect(m, 0, 0, CELL_W // 2 - 1, CELL_H // 2 - 1)
        _rect(m, CELL_W // 2, CELL_H // 2, CELL_W - 1, CELL_H - 1)
    elif ch == "▚":
        _rect(m, 0, 0, CELL_W // 2 - 1, CELL_H // 2 - 1)
        _rect(m, CELL_W // 2, CELL_H // 2, CELL_W - 1, CELL_H - 1)
    elif ch == "▛":
        _rect(m, 0, 0, CELL_W // 2 - 1, CELL_H - 1)
        _rect(m, CELL_W // 2, 0, CELL_W - 1, CELL_H // 2 - 1)
    elif ch == "▜":
        _rect(m, CELL_W // 2, 0, CELL_W - 1, CELL_H - 1)
        _rect(m, 0, 0, CELL_W // 2 - 1, CELL_H // 2 - 1)
    elif ch == "▞":
        _rect(m, CELL_W // 2, 0, CELL_W - 1, CELL_H // 2 - 1)
        _rect(m, 0, CELL_H // 2, CELL_W // 2 - 1, CELL_H - 1)
    elif ch == "▟":
        _rect(m, CELL_W // 2, 0, CELL_W - 1, CELL_H - 1)
        _rect(m, 0, CELL_H // 2, CELL_W // 2 - 1, CELL_H - 1)
    return m


# --- braille ----------------------------------------------------------------

_BRAILLE_BITS = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))
_BRAILLE_POS = ((2, 3), (2, 8), (2, 13), (7, 3), (7, 8), (7, 13), (2, 17), (7, 17))


def _braille_mask(ch):
    code = ord(ch) - 0x2800
    m = _blank()
    for bit, (x, y) in enumerate(_BRAILLE_POS):
        if code & (1 << bit):
            _rect(m, x - 1, y - 1, x + 1, y + 1)
    return m


# --- symbols ----------------------------------------------------------------

def _circle(m, cx, cy, r, fill=True, aa=True):
    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    if fill:
        v = np.clip((r - d) * 255, 0, 255)
    else:
        v = np.clip((1.2 - np.abs(d - r)) * 255, 0, 255)
    np.maximum(m, v.astype(np.uint8), out=m)


def _star(m, cx, cy, r_out, r_in, rot=-np.pi / 2, fill=True):
    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    ang = np.arctan2(yy - cy, xx - cx)
    rad = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # 5 points
    a = (ang - rot) % (2 * np.pi / 5)
    frac = a / (2 * np.pi / 5)
    edge_r = r_in + (r_out - r_in) * np.abs(1 - 2 * np.abs(frac - 0.5) * 2)
    v = np.clip((edge_r - rad) * 255, 0, 255)
    np.maximum(m, v.astype(np.uint8), out=m)


def _line(m, x0, y0, x1, y1, thick=1.0, v=255):
    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    dx, dy = x1 - x0, y1 - y0
    L = max(1e-6, dx * dx + dy * dy)
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L, 0, 1)
    px, py = x0 + t * dx, y0 + t * dy
    d = np.sqrt((xx - px) ** 2 + (yy - py) ** 2)
    val = np.clip((thick - d) * 255, 0, 255)
    np.maximum(m, val.astype(np.uint8), out=m)


def _sym_mask(ch):
    m = _blank()
    if ch in "●◉":
        _circle(m, 4.5, 8.5, 3.6)
        if ch == "◉":
            _circle(m, 4.5, 8.5, 1.4, fill=False)
    elif ch in "○◯":
        _circle(m, 4.5, 8.5, 3.6, fill=False)
    elif ch == "◎":
        _circle(m, 4.5, 8.5, 3.8, fill=False)
        _circle(m, 4.5, 8.5, 1.4, fill=False)
    elif ch == "◍":
        _circle(m, 4.5, 8.5, 4.0, fill=False)
        _line(m, 0, 8.5, 9, 8.5, 0.6)
        _line(m, 4.5, 0, 4.5, 18, 0.6)
    elif ch == "◆":
        _star(m, 4.5, 8.5, 4.6, 0.0, 0, fill=True)
    elif ch == "◇":
        _star(m, 4.5, 8.5, 4.8, 2.6, 0, fill=True)
    elif ch == "◈":
        _star(m, 4.5, 8.5, 4.8, 0, 0)
        _star(m, 4.5, 8.5, 1.6, 0, 0)
    elif ch == "■":
        _rect(m, 1, 5, 8, 12)
    elif ch == "□":
        for x in range(1, 9):
            _put(m, x, 5)
            _put(m, x, 12)
        for y in range(5, 13):
            _put(m, 1, y)
            _put(m, 8, y)
    elif ch == "▪":
        _rect(m, 3, 7, 6, 10)
    elif ch == "▫":
        for x in range(3, 7):
            _put(m, x, 7)
            _put(m, x, 10)
    elif ch == "▲":
        for i in range(8):
            _rect(m, 4 - i // 2, 3 + i, 5 + i // 2, 3 + i)
    elif ch == "▼":
        for i in range(8):
            _rect(m, i // 2, 13 - i, 9 - i // 2, 13 - i)
    elif ch == "◀":
        for i in range(8):
            _rect(m, 2 + i // 2, 4 + i, 2 + i // 2, 12 - i)
    elif ch == "▶":
        for i in range(8):
            _rect(m, 1 + i // 2, 12 - i, 1 + i // 2, 4 + i)
    elif ch in "★☆":
        _star(m, 5, 9, 5.2, 2.2)
        if ch == "☆":
            _star(m, 5, 9, 3.4, 1.0)
            m[4:14, 2:8] = np.where(m[4:14, 2:8] > 100, 0, 0)
    elif ch in "✦":
        _line(m, 5, 1, 5, 16, 0.8)
        _line(m, 0, 8.5, 9, 8.5, 0.8)
    elif ch in "✧":
        _line(m, 5, 3, 5, 14, 0.5)
        _line(m, 2, 8.5, 7, 8.5, 0.5)
    elif ch == "⚡":
        pts = [(6, 0), (2, 9), (5, 9), (3, 17), (8, 6), (5, 6), (8, 0)]
        _poly(m, pts)
    elif ch in "♥":
        _heart_small(m, fill=True)
    elif ch in "♡":
        _heart_small(m, fill=False)
    elif ch in "♪":
        _rect(m, 4, 3, 4, 12)
        _line(m, 4, 3, 7, 2, 0.9)
        _circle(m, 2.6, 13.4, 2.2)
    elif ch == "♫":
        _rect(m, 2, 3, 2, 12)
        _rect(m, 6, 2, 6, 11)
        _line(m, 2, 3, 6, 2, 0.9)
        _circle(m, 1.0, 13.4, 2.0)
        _circle(m, 5.0, 12.4, 2.0)
    elif ch == "∞":
        _circle(m, 2.4, 9, 2.6, fill=False)
        _circle(m, 7.4, 9, 2.6, fill=False)
    elif ch in "≈":
        _line(m, 1, 6, 8, 5, 0.8)
        _line(m, 1, 11, 8, 10, 0.8)
    elif ch == "≠":
        _line(m, 1, 7, 8, 7, 0.7)
        _line(m, 1, 10, 8, 10, 0.7)
        _line(m, 6, 2, 3, 16, 0.7)
    elif ch == "≤":
        _line(m, 7, 4, 2, 8, 0.8)
        _line(m, 2, 8, 7, 12, 0.8)
        _line(m, 2, 15, 7, 15, 0.7)
    elif ch == "≥":
        _line(m, 2, 4, 7, 8, 0.8)
        _line(m, 7, 8, 2, 12, 0.8)
        _line(m, 2, 15, 7, 15, 0.7)
    elif ch == "±":
        _line(m, 1, 8, 8, 8, 0.8)
        _line(m, 4.5, 4, 4.5, 12, 0.8)
        _line(m, 1, 15, 8, 15, 0.7)
    elif ch == "×":
        _line(m, 2, 4, 7, 12, 0.8)
        _line(m, 7, 4, 2, 12, 0.8)
    elif ch == "÷":
        _line(m, 1, 9, 8, 9, 0.8)
        _circle(m, 4.5, 4.5, 1.0)
        _circle(m, 4.5, 13.0, 1.0)
    elif ch in "∑":
        _line(m, 8, 3, 2, 3, 0.8)
        _line(m, 2, 3, 6, 9, 0.8)
        _line(m, 6, 9, 2, 15, 0.8)
        _line(m, 2, 15, 8, 15, 0.8)
    elif ch == "Δ":
        _line(m, 4.5, 3, 1, 15, 0.8)
        _line(m, 4.5, 3, 8, 15, 0.8)
        _line(m, 1, 15, 8, 15, 0.8)
    elif ch == "π":
        _line(m, 1, 4, 8, 4, 0.8)
        _line(m, 3, 4, 3, 15, 0.8)
        _line(m, 6.5, 4, 6.5, 15, 0.8)
    elif ch == "Ω":
        _circle(m, 4.5, 7, 3.2)
        _rect(m, 2, 10, 7, 13)
        _line(m, 2, 15, 7, 15, 0.8)
        _line(m, 3, 13, 3, 15, 0.8)
        _line(m, 6, 13, 6, 15, 0.8)
    elif ch == "√":
        _line(m, 1, 10, 3, 15, 0.8)
        _line(m, 3, 15, 8, 2, 0.8)
    elif ch == "∫":
        _line(m, 6, 2, 4, 4, 0.8)
        _line(m, 4, 4, 6, 14, 0.8)
        _line(m, 6, 14, 3, 16, 0.8)
    elif ch == "∂":
        _circle(m, 4.5, 9, 3.2, fill=False)
        _line(m, 7, 3, 7, 13, 0.8)
    elif ch == "←":
        _line(m, 8, 9, 1, 9, 0.9)
        _line(m, 1, 9, 4, 5, 0.9)
        _line(m, 1, 9, 4, 13, 0.9)
    elif ch == "→":
        _line(m, 1, 9, 8, 9, 0.9)
        _line(m, 8, 9, 5, 5, 0.9)
        _line(m, 8, 9, 5, 13, 0.9)
    elif ch == "↑":
        _line(m, 5, 16, 5, 1, 0.9)
        _line(m, 5, 1, 1, 5, 0.9)
        _line(m, 5, 1, 9, 5, 0.9)
    elif ch == "↓":
        _line(m, 5, 1, 5, 16, 0.9)
        _line(m, 5, 16, 1, 12, 0.9)
        _line(m, 5, 16, 9, 12, 0.9)
    elif ch == "↔":
        _line(m, 1, 9, 8, 9, 0.9)
        _line(m, 1, 9, 4, 5, 0.9)
        _line(m, 1, 9, 4, 13, 0.9)
        _line(m, 8, 9, 5, 5, 0.9)
        _line(m, 8, 9, 5, 13, 0.9)
    elif ch == "↕":
        _line(m, 5, 1, 5, 16, 0.9)
        _line(m, 5, 1, 1, 5, 0.9)
        _line(m, 5, 1, 9, 5, 0.9)
        _line(m, 5, 16, 1, 11, 0.9)
        _line(m, 5, 16, 9, 11, 0.9)
    elif ch in "⇒":
        _line(m, 1, 9, 8, 9, 0.9)
        _line(m, 8, 9, 5, 5, 0.9)
        _line(m, 8, 9, 5, 13, 0.9)
        _line(m, 1, 5, 1, 13, 0.7)
    elif ch in "⇐":
        _line(m, 1, 9, 8, 9, 0.9)
        _line(m, 1, 9, 4, 5, 0.9)
        _line(m, 1, 9, 4, 13, 0.9)
        _line(m, 8, 5, 8, 13, 0.7)
    elif ch == "⇔":
        _line(m, 1, 9, 8, 9, 0.9)
        _line(m, 8, 9, 5, 5, 0.9)
        _line(m, 8, 9, 5, 13, 0.9)
        _line(m, 1, 9, 4, 5, 0.9)
        _line(m, 1, 9, 4, 13, 0.9)
    elif ch in "↻⟳":
        _circle(m, 4.5, 9, 3.4, fill=False)
        _line(m, 4.5, 2.6, 7.6, 4.5, 0.9)
        _line(m, 4.5, 2.6, 1.4, 4.5, 0.9)
    elif ch in "↺⟲":
        _circle(m, 4.5, 9, 3.4, fill=False)
        _line(m, 4.5, 2.6, 1.4, 4.5, 0.9)
        _line(m, 4.5, 2.6, 7.6, 4.5, 0.9)
    elif ch in "✓✔":
        _line(m, 1, 9, 4, 13, 1.0)
        _line(m, 4, 13, 8, 3, 1.0)
    elif ch in "✗✕✘":
        _line(m, 2, 3, 7, 14, 1.0)
        _line(m, 7, 3, 2, 14, 1.0)
    elif ch == "·":
        _circle(m, 4.5, 9, 1.2)
    elif ch in "•∙":
        _circle(m, 4.5, 9, 1.8)
    elif ch == "°":
        _circle(m, 4.5, 5, 1.6, fill=False)
    elif ch == "′":
        _line(m, 5, 3, 4, 8, 0.8)
    elif ch == "″":
        _line(m, 3, 3, 2, 8, 0.8)
        _line(m, 7, 3, 6, 8, 0.8)
    elif ch == "‰":
        _circle(m, 2.5, 6, 1.0, fill=False)
        _circle(m, 2.5, 12.5, 1.0, fill=False)
        _line(m, 8, 3, 1, 15, 0.7)
    elif ch == "⌁":
        _line(m, 1, 11, 3, 5, 0.8)
        _line(m, 3, 5, 5, 12, 0.8)
        _line(m, 5, 12, 7, 5, 0.8)
    elif ch in "⚑⚐":
        _line(m, 2, 1, 2, 16, 0.8)
        _poly(m, [(3, 2), (9, 4), (3, 8)])
    elif ch == "⏻":
        _circle(m, 4.5, 9.5, 3.6, fill=False)
        _rect(m, 2, 4, 7, 5)
        _rect(m, 4, 0, 5, 6)
    elif ch == "⏼":
        _circle(m, 4.5, 9, 3.6, fill=False)
        _line(m, 4.5, 0.5, 4.5, 7, 1.0)
    elif ch == "⏸":
        _rect(m, 2, 3, 3, 15)
        _rect(m, 6, 3, 7, 15)
    elif ch == "⏹":
        _rect(m, 2, 5, 7, 13)
    elif ch == "⏺":
        _circle(m, 4.5, 9, 3.2)
    elif ch == "☰":
        for y in (4, 9, 14):
            _rect(m, 1, y, 8, y)
    elif ch == "☷":
        for y in (4, 6, 8, 10, 12, 14):
            _rect(m, 1, y, 8, y)
    elif ch == "⌘":
        _circle(m, 2.5, 4, 1.6, fill=False)
        _circle(m, 7.5, 4, 1.6, fill=False)
        _circle(m, 2.5, 14, 1.6, fill=False)
        _circle(m, 7.5, 14, 1.6, fill=False)
        _rect(m, 2, 4, 7, 14)
        _rect(m, 4, 6, 5, 12)
    elif ch == "⌂":
        _poly(m, [(1, 8), (5, 2), (9, 8)])
        _rect(m, 2, 8, 7, 14)
    elif ch == "§":
        _circle(m, 4.5, 5, 2.4, fill=False)
        _circle(m, 4.5, 12, 2.4, fill=False)
    elif ch == "¶":
        _rect(m, 3, 3, 7, 9)
        _rect(m, 6, 3, 7, 15)
    elif ch in "©®":
        _circle(m, 4.5, 9, 4.2, fill=False)
        _circle(m, 4.5, 9, 1.8, fill=False)
        if ch == "®":
            _line(m, 4, 8, 6, 5, 0.6)
    elif ch == "™":
        _line(m, 1, 5, 3, 5, 0.7)
        _line(m, 2, 5, 2, 12, 0.7)
        _line(m, 5, 12, 5, 5, 0.7)
        _line(m, 5, 5, 6, 9, 0.7)
        _line(m, 6, 9, 8, 5, 0.7)
        _line(m, 8, 5, 8, 12, 0.7)
    elif ch == "※":
        _line(m, 4.5, 1, 4.5, 7, 0.7)
        _line(m, 4.5, 11, 4.5, 17, 0.7)
        _line(m, 1, 9, 7, 9, 0.7)
        _line(m, 8, 9, 9, 9, 0.7)
    elif ch == "⎔":
        _poly(m, [(5, 2), (8, 5), (8, 12), (5, 15), (2, 12), (2, 5)], closed=True)
    elif ch == "⌬":
        _poly(m, [(5, 1), (8, 5), (5, 9), (2, 5)], closed=True)
        _poly(m, [(5, 9), (8, 13), (5, 17), (2, 13)], closed=True)
    elif ch == "⌖":
        _circle(m, 4.5, 9, 2.6, fill=False)
        for d in range(1, 4):
            _put(m, 4 + d, 9)
            _put(m, 4 - d, 9)
            _put(m, 4, 9 + d)
            _put(m, 4, 9 - d)
    elif ch == "⌗":
        _line(m, 2, 4, 2, 14, 0.7)
        _line(m, 7, 4, 7, 14, 0.7)
        _line(m, 0, 7, 9, 7, 0.7)
        _line(m, 0, 11, 9, 11, 0.7)
    elif ch == "⌦":
        _line(m, 1, 9, 7, 9, 0.8)
        _line(m, 7, 9, 4, 6, 0.8)
        _line(m, 7, 9, 4, 12, 0.8)
        _line(m, 8, 3, 8, 15, 0.8)
    elif ch == "⌫":
        _poly(m, [(2, 5), (9, 5), (9, 13), (2, 13)])
        _line(m, 3, 7, 6, 11, 0.7)
        _line(m, 6, 7, 3, 11, 0.7)
    return m


def _poly(m, pts, closed=True, v=255):
    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    inside = np.zeros((CELL_H, CELL_W), bool)
    n = len(pts)
    for i in range(n if closed else n - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cond = ((y0 > yy) != (y1 > yy))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x1 - x0) * (yy - y0) / (y1 - y0 + 1e-9) + x0
        inside ^= cond & (xx < xint)
    # antialias-ish: blur border by supersampling tiny amount
    np.maximum(m, np.where(inside, v, 0).astype(np.uint8), out=m)


def _heart_small(m, fill=True):
    yy, xx = np.mgrid[0:CELL_H, 0:CELL_W]
    x = (xx - 4.5) / 3.2
    y = -(yy - 8.0) / 3.4
    f = (x * x + y * y - 1) ** 3 - x * x * y * y * y
    if fill:
        v = np.clip((-f) * 900, 0, 255)
    else:
        v = np.clip((0.12 - np.abs(f)) * 1600, 0, 255)
    np.maximum(m, v.astype(np.uint8), out=m)


# --- text rasterisation -----------------------------------------------------

_FONT_CACHE = {}


def _font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            font = ImageFont.truetype(path, size) if path else None
        except Exception:
            font = None
        if font is None:            # no usable TTF on this box
            try:
                font = ImageFont.load_default(size=size)
            except TypeError:        # Pillow < 10.1
                font = ImageFont.load_default()
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


def _raster_text(ch, size=FONT_SIZE, path=CONSOLA, baseline=BASELINE, cellw=CELL_W, cellh=CELL_H):
    img = Image.new("L", (cellw * 3, cellh * 3), 0)
    d = ImageDraw.Draw(img)
    try:
        font = _font(path, size)
        d.text((cellw, baseline + cellh), ch, font=font, fill=255, anchor="ls")
    except Exception:
        return None
    arr = np.asarray(img.crop((cellw, cellh, cellw * 2, cellh * 2))).astype(np.float32)
    # punch up the antialiased edges so stems survive the CRT pass
    arr = np.clip(arr, 0.0, 255.0)
    return arr.astype(np.uint8)


def _raster_any(ch):
    """Try a few fonts and keep the first non-empty raster.

    Bold Consolas is preferred for the ASCII range: at 16 px in a 10x18 cell
    the regular weight loses its stems once the CRT pass dims it, while bold
    stays readable.
    """
    ascii_ch = ord(ch) < 127
    paths = (CONSOLA, SEGUISYM, ARIAL)
    for path in paths:
        if not os.path.exists(path):
            continue
        for size, base in ((FONT_SIZE, BASELINE), (FONT_SIZE + 1, BASELINE)):
            arr = _raster_text(ch, size=size, path=path, baseline=base)
            if arr is not None and arr.max() > 0:
                return arr
    return None


# ---------------------------------------------------------------------------

_ALL_CHARS = None
_CHAR_TO_IDX = None
_ATLAS = None
IDX_CHARS = [" "]   # index -> char, index 0 = blank


def _glyph_list():
    chars = "".join(chr(c) for c in range(32, 127))
    chars += BOX_CHARS + BLOCK_CHARS + QUAD_CHARS + SYMBOL_CHARS + MISC_CHARS + EXTRA_CHARS
    chars += BRAILLE_CHARS
    # unique, keep order
    seen = set()
    out = []
    for ch in chars:
        if ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out


def _proc_mask(fn, ch):
    """Build a procedural glyph at the reference 10x18 cell, then upscale."""
    global CELL_W, CELL_H
    if _L.SCALE == 1:
        return fn(ch)
    cw, chh = CELL_W, CELL_H
    CELL_W, CELL_H = 10, 18
    try:
        m = fn(ch)
    finally:
        CELL_W, CELL_H = cw, chh
    from PIL import Image as _Im
    im = _Im.fromarray(np.ascontiguousarray(m), "L").resize((cw, chh), _Im.NEAREST)
    return np.asarray(im, np.uint8)


def build_atlas(verbose=False):
    global _ALL_CHARS, _CHAR_TO_IDX, _ATLAS, IDX_CHARS
    glyphs = _glyph_list()
    atlas = np.zeros((len(glyphs) + 1, CELL_H, CELL_W), np.uint8)  # 0 = blank
    idx = {" ": 0}
    missing = []
    for i, ch in enumerate(glyphs):
        if ch == " ":
            continue
        if ch in BOX_EDGES:
            m = _proc_mask(_box_mask, ch)
        elif ch in BLOCK_CHARS or ch in QUAD_CHARS:
            m = _proc_mask(_block_mask, ch)
        elif 0x2800 <= ord(ch) <= 0x28FF:
            m = _proc_mask(_braille_mask, ch)
        elif ch in SYMBOL_CHARS or ch in MISC_CHARS:
            m = _proc_mask(_sym_mask, ch)
            if m.max() == 0:
                m = _raster_any(ch)
                if m is None:
                    missing.append(ch)
                    m = _blank()
        else:
            m = _raster_any(ch)
            if m is None:
                missing.append(ch)
                m = _blank()
        atlas[i + 1] = m
        idx[ch] = i + 1
    _ALL_CHARS = glyphs
    _CHAR_TO_IDX = idx
    _ATLAS = atlas
    IDX_CHARS = [" "] + glyphs
    if verbose:
        print(f"[font] atlas: {len(glyphs)} glyphs, missing: {missing}")
    return atlas, idx


def get_atlas():
    if _ATLAS is None:
        build_atlas()
    return _ATLAS, _CHAR_TO_IDX


def char_index(ch):
    if _CHAR_TO_IDX is None:
        build_atlas()
    return _CHAR_TO_IDX.get(ch, 0)


def cell_width(ch):
    """Terminal display width of a char (CJK = 2)."""
    o = ord(ch)
    if (0x2E80 <= o <= 0xA4CF) or (0xAC00 <= o <= 0xD7A3) or (0xF900 <= o <= 0xFAFF) \
            or (0xFE30 <= o <= 0xFE4F) or (0xFF00 <= o <= 0xFF60) or (0xFFE0 <= o <= 0xFFE6):
        return 2
    return 1


# --- large masks ------------------------------------------------------------

_MASK_CACHE = {}



def erode_mask(mask, px):
    """Thin a coverage mask by `px` pixels (morphological erosion), for thin V3-style strokes."""
    if px <= 0:
        return mask
    im = Image.fromarray(np.clip(mask * 255.0, 0, 255).astype(np.uint8), "L")
    size = int(px) * 2 + 1
    im = im.filter(ImageFilter.MinFilter(size))
    return np.asarray(im, np.float32) / 255.0


def text_mask(text, px_h=120, bold=False, line_gap=0.18, max_px_w=None):
    """Render text with Consolas into a float32 coverage mask (0..1)."""
    key = (text, int(px_h), bool(bold), line_gap)
    if key in _MASK_CACHE:
        return _MASK_CACHE[key]
    path = CONSOLA_B if bold else CONSOLA
    size = max(6, int(px_h))
    font = _font(path, size)
    lines = text.split("\n")
    # measure
    tmp = Image.new("L", (10, 10))
    d = ImageDraw.Draw(tmp)
    widths = []
    heights = []
    for ln in lines:
        bbox = d.textbbox((0, 0), ln, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    gap = int(size * line_gap)
    W = max(1, max(widths))
    H = max(1, sum(heights) + gap * (len(lines) - 1))
    img = Image.new("L", (W + 4, H + 4), 0)
    d = ImageDraw.Draw(img)
    y = 2
    for ln, h in zip(lines, heights):
        bbox = d.textbbox((0, 0), ln, font=font)
        d.text((2 - bbox[0], y - bbox[1]), ln, font=font, fill=255)
        y += h + gap
    arr = np.asarray(img).astype(np.float32) / 255.0
    # trim
    nz = np.argwhere(arr > 0.02)
    if len(nz):
        y0, x0 = nz.min(0)
        y1, x1 = nz.max(0) + 1
        arr = arr[y0:y1, x0:x1]
    if max_px_w and arr.shape[1] > max_px_w:
        scale = max_px_w / arr.shape[1]
        im = Image.fromarray((arr * 255).astype(np.uint8)).resize(
            (max_px_w, max(1, int(round(arr.shape[0] * scale)))), Image.LANCZOS)
        arr = np.asarray(im).astype(np.float32) / 255.0
    # big words: thin the strokes by 1 px and sharpen the coverage edge so the
    # cell grid renders crisp binary letters instead of a soft dither halo.
    if int(px_h) >= 88:
        arr = erode_mask(arr, 1)
        arr = np.clip((arr - 0.40) / 0.22, 0.0, 1.0)
    _MASK_CACHE[key] = arr
    return arr


def resize_mask(mask, w, h):
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)).astype(np.float32) / 255.0


def heart_mask(w, h, holes=(), dents=(), notch=0.0):
    """Parametric heart coverage mask with optional defects.

    holes: iterable of (fx, fy, fr) in 0..1 normalised coords, carved out.
    dents:  iterable of (fx, fy, fr) shallow bites on the outline.
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx / max(1, w) - 0.5) * 2.6
    y = -(yy / max(1, h) - 0.52) * 2.6
    f = (x * x + y * y - 1) ** 3 - x * x * y * y * y
    m = (f <= 0).astype(np.float32)
    # soft edge
    edge = np.clip((0.06 + f * 0.5) * 6, 0, 1)
    m = m * edge
    for (fx, fy, fr) in holes:
        cx, cy, r = fx * w, fy * h, fr * w
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        m = m * np.clip((d - r) / max(1e-3, r * 0.08), 0, 1)
    for (fx, fy, fr) in dents:
        cx, cy, r = fx * w, fy * h, fr * w
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        m = m * (1.0 - np.clip((r - d) / max(1e-3, r * 0.25), 0, 1))
    return np.clip(m, 0, 1)


def infinity_mask(w, h, thick=0.16):
    """Thick lemniscate-of-Bernoulli coverage mask (real distance field)."""
    w = max(8, int(w)); h = max(8, int(h))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.linspace(0.0, 2.0 * np.pi, 512, endpoint=False, dtype=np.float32)
    st_, ct = np.sin(t), np.cos(t)
    den = 1.0 + st_ * st_
    px = (ct / den) * (w * 0.46) + w * 0.5
    py = (st_ * ct / den)
    span = float(np.max(np.abs(py))) + 1e-6
    py = py / span * (h * 0.44) + h * 0.5
    best = np.full((h, w), 1e9, np.float32)
    for i2 in range(px.shape[0]):
        dy = yy - py[i2]
        dx = xx - px[i2]
        np.minimum(best, dx * dx + dy * dy, out=best)
    d = np.sqrt(best)
    rad = max(1.0, thick * h * 0.5)
    m = np.clip((rad - d) / max(1.0, rad * 0.55), 0, 1)
    return m
