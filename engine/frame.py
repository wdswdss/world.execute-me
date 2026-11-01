"""Cell-buffer frame: the drawing surface every scene writes into.

A Frame holds, per character cell, a glyph index plus fg/bg colours.  Scene
code draws on a stage-sized frame (192x45); the chrome layer (header, rules,
subtitle strip, spectrum) is composited afterwards.  `compose()` turns the
cell buffer into a 1920x1080 uint8 RGB array through the glyph atlas.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from . import font as F
from . import layout as L
from . import palette as P

_BLANK = 0


def _col(c):
    if c is None:
        return None
    return np.asarray(c, dtype=np.float32)


class Frame:
    def __init__(self, rows: int, cols: int, bg=P.C["void"]):
        self.rows = int(rows)
        self.cols = int(cols)
        self.ch = np.zeros((self.rows, self.cols), np.int16)
        self.fg = np.zeros((self.rows, self.cols, 3), np.uint8)
        self.bg = np.zeros((self.rows, self.cols, 3), np.uint8)
        self.bg[:] = np.asarray(bg, np.uint8)
        self.fg[:] = np.asarray(P.C["fg"], np.uint8)

    # -- basic ------------------------------------------------------------
    def clear(self, bg=P.C["void"], fg=P.C["fg"]):
        self.ch[:] = _BLANK
        self.bg[:] = np.asarray(bg, np.uint8)
        self.fg[:] = np.asarray(fg, np.uint8)
        return self

    def clone(self):
        f = Frame.__new__(Frame)
        f.rows, f.cols = self.rows, self.cols
        f.ch = self.ch.copy()
        f.fg = self.fg.copy()
        f.bg = self.bg.copy()
        return f

    def squeezed(self, scale, center=None):
        """Vertical fold: resample every row toward `center` (for the ending)."""
        out = self.clone()
        out.ch[:] = _BLANK
        out.bg[:] = np.asarray(P.C["void"], np.uint8)
        out.fg[:] = np.asarray(P.C["fg"], np.uint8)
        cy = (self.rows - 1) / 2.0 if center is None else float(center)
        inv = 1.0 / max(1e-3, float(scale))
        for r in range(self.rows):
            sr = int(round(cy + (r - cy) * inv))
            if 0 <= sr < self.rows:
                out.ch[r] = self.ch[sr]
                out.fg[r] = self.fg[sr]
                out.bg[r] = self.bg[sr]
        return out

    def inb(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def put(self, r, c, ch_=" ", fg=None, bg=None):
        r = int(r)
        c = int(c)
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return
        if isinstance(ch_, int):
            self.ch[r, c] = ch_
        else:
            idx = F.char_index(ch_)
            if idx == 0 and ch_ not in (" ", ""):
                idx = F.char_index("?") or 63   # loud fallback: missing glyph
            self.ch[r, c] = idx
        if fg is not None:
            self.fg[r, c] = np.asarray(fg, np.uint8)
        if bg is not None:
            self.bg[r, c] = np.asarray(bg, np.uint8)

    def get(self, r, c):
        return F.IDX_CHARS[self.ch[r, c]]

    def set_idx(self, r, c, idx, fg=None, bg=None):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.ch[r, c] = idx
            if fg is not None:
                self.fg[r, c] = np.asarray(fg, np.uint8)
            if bg is not None:
                self.bg[r, c] = np.asarray(bg, np.uint8)

    # -- text -------------------------------------------------------------
    def write(self, r, c, s, fg=None, bg=None):
        cc = int(c)
        for ch_ in s:
            if ch_ == "\n":
                r += 1
                cc = int(c)
                continue
            w = F.cell_width(ch_)
            if w == 2:
                # CJK is not in the pixel atlas; leave a blank slot
                if 0 <= r < self.rows:
                    for k in range(2):
                        self.put(r, cc + k, " ", fg=fg, bg=bg)
                cc += 2
                continue
            self.put(r, cc, ch_, fg=fg, bg=bg)
            cc += 1
        return cc

    def ctext(self, r, s, fg=None, bg=None):
        c = (self.cols - len(s)) // 2
        return self.write(r, c, s, fg=fg, bg=bg)

    def rtext(self, r, s, fg=None, bg=None, pad=0):
        c = self.cols - len(s) - pad
        return self.write(r, c, s, fg=fg, bg=bg)

    def text_block(self, r, c, lines, fg=None, bg=None, gap=0):
        for i, ln in enumerate(lines):
            self.write(r + i * (1 + gap), c, ln, fg=fg, bg=bg)

    # -- shapes -----------------------------------------------------------
    def fill_rect(self, r0, c0, r1, c1, ch_=" ", fg=None, bg=None):
        r0 = max(0, int(r0)); c0 = max(0, int(c0))
        r1 = min(self.rows - 1, int(r1)); c1 = min(self.cols - 1, int(c1))
        if r1 < r0 or c1 < c0:
            return
        self.ch[r0:r1 + 1, c0:c1 + 1] = F.char_index(ch_) if not isinstance(ch_, int) else ch_
        if fg is not None:
            self.fg[r0:r1 + 1, c0:c1 + 1] = np.asarray(fg, np.uint8)
        if bg is not None:
            self.bg[r0:r1 + 1, c0:c1 + 1] = np.asarray(bg, np.uint8)

    def hline(self, r, c0, c1, ch_="─", fg=None, bg=None):
        if c1 < c0:
            c0, c1 = c1, c0
        for c in range(int(c0), int(c1) + 1):
            self.put(r, c, ch_, fg=fg, bg=bg)

    def vline(self, c, r0, r1, ch_="│", fg=None, bg=None):
        if r1 < r0:
            r0, r1 = r1, r0
        for r in range(int(r0), int(r1) + 1):
            self.put(r, c, ch_, fg=fg, bg=bg)

    def box(self, r0, c0, r1, c1, style=1, fg=None, bg=None, title=None):
        """style 1=single, 2=double, 3=heavy."""
        sets = {
            1: ("┌", "┐", "└", "┘", "─", "│"),
            2: ("╔", "╗", "╚", "╝", "═", "║"),
            3: ("┏", "┓", "┗", "┛", "━", "┃"),
        }
        tl, tr, bl, br, hz, vt = sets[style]
        r0, c0, r1, c1 = int(r0), int(c0), int(r1), int(c1)
        self.put(r0, c0, tl, fg, bg)
        self.put(r0, c1, tr, fg, bg)
        self.put(r1, c0, bl, fg, bg)
        self.put(r1, c1, br, fg, bg)
        self.hline(r0, c0 + 1, c1 - 1, hz, fg, bg)
        self.hline(r1, c0 + 1, c1 - 1, hz, fg, bg)
        self.vline(c0, r0 + 1, r1 - 1, vt, fg, bg)
        self.vline(c1, r0 + 1, r1 - 1, vt, fg, bg)
        if title:
            self.write(r0, c0 + 2, f" {title} ", fg=fg, bg=bg)

    def frame_border(self, style=1, fg=None, bg=None):
        self.box(0, 0, self.rows - 1, self.cols - 1, style, fg, bg)

    def grid_bg(self, step=4, fg=P.C["grid"], ch_="·"):
        for r in range(0, self.rows, step):
            for c in range(0, self.cols, step):
                self.put(r, c, ch_, fg=fg)

    def gradient_rows(self, c0, c1, fg_top, fg_bot):
        fg_top = np.asarray(fg_top, np.float32)
        fg_bot = np.asarray(fg_bot, np.float32)
        for r in range(self.rows):
            a = r / max(1, self.rows - 1)
            self.fg[r, c0:c1 + 1] = (fg_top * (1 - a) + fg_bot * a).astype(np.uint8)

    # -- sprite / art -----------------------------------------------------
    def paint_rows(self, rows, r0, c0, fg=None, bg=None, char_map=None):
        """Draw literal ASCII art rows (list of strings)."""
        for dy, line in enumerate(rows):
            r = r0 + dy
            if not (0 <= r < self.rows):
                continue
            for dx, ch_ in enumerate(line):
                c = c0 + dx
                if not (0 <= c < self.cols):
                    continue
                if ch_ == " " and char_map is None:
                    if bg is not None:
                        self.bg[r, c] = np.asarray(bg, np.uint8)
                    continue
                self.put(r, c, ch_, fg=fg, bg=bg)

    def paint_mask(self, mask, c0, r0, w=None, h=None, ramp=None,
                   fg=None, fg2=None, bg=None, gain=1.0, alpha=1.0,
                   keep_empty=False, min_v=0.02, shade_from=None,
                   hard=None):
        """Sample a float coverage mask (any resolution) onto the cell grid."""
        mask = np.asarray(mask, np.float32)
        if w is None:
            w = mask.shape[1] / L.CELL_W
        if h is None:
            h = mask.shape[0] / L.CELL_H
        w = max(1, int(round(w)))
        h = max(1, int(round(h)))
        if mask.shape[0] != h * L.CELL_H or mask.shape[1] != w * L.CELL_W:
            mask = F.resize_mask(mask, w * L.CELL_W, h * L.CELL_H)
        cells = mask.reshape(h, L.CELL_H, w, L.CELL_W).mean(axis=(1, 3))
        cells = np.clip(cells * gain, 0, 1)
        ramp = ramp or P.RAMP_HI
        n = len(ramp) - 1
        fg = np.asarray(fg if fg is not None else P.C["fg"], np.float32)
        fg2 = np.asarray(fg2, np.float32) if fg2 is not None else None
        r0, c0 = int(round(r0)), int(round(c0))
        for y in range(h):
            r = r0 + y
            if not (0 <= r < self.rows):
                continue
            for x in range(w):
                c = c0 + x
                if not (0 <= c < self.cols):
                    continue
                v = float(cells[y, x])
                if hard is not None:
                    if v < hard * 0.30:
                        if bg is not None:
                            self.bg[r, c] = np.asarray(bg, np.uint8)
                        continue
                    self.ch[r, c] = F.char_index(ramp[-1])
                    col = np.asarray(fg, np.float32)
                    if v < hard:
                        col = col * 0.62 + np.asarray(P.C["void"], np.float32) * 0.38
                    self.fg[r, c] = np.clip(col, 0, 255).astype(np.uint8)
                    if bg is not None:
                        self.bg[r, c] = np.asarray(bg, np.uint8)
                    continue
                if v < min_v:
                    if keep_empty and bg is not None:
                        self.bg[r, c] = np.asarray(bg, np.uint8)
                    continue
                idx = F.char_index(ramp[int(v * n + 0.5)])
                self.ch[r, c] = idx
                if fg2 is None:
                    col = fg
                elif shade_from is not None:
                    tv = float(np.clip((v - shade_from) / max(1e-6, 1.0 - shade_from), 0.0, 1.0))
                    col = fg * (1.0 - tv) + fg2 * tv
                else:
                    col = fg * (1 - v) + fg2 * v
                if alpha >= 0.999:
                    self.fg[r, c] = col.astype(np.uint8)
                else:
                    self.fg[r, c] = (self.fg[r, c] * (1 - alpha) + col * alpha).astype(np.uint8)
                if bg is not None:
                    self.bg[r, c] = np.asarray(bg, np.uint8)

    def paint_text(self, text, r0, c0, h_cells, fg=None, fg2=None, bg=None,
                   ramp=None, bold=False, align="center", w_cells=None,
                   alpha=1.0, max_cols=None, gain=None, hard=None, thin=0):
        """Render large text as character cells. Returns (r0, c0, h, w).

        Small glyph heights need a much higher coverage gain: without it the
        per-cell coverage stays patchy and the dither ramp eats the strokes.
        """
        tm = F.text_mask(text, int(h_cells * L.CELL_H), bold=bold)
        h_cells = max(1, int(h_cells))
        thin_px = int(thin)
        if thin_px:
            tm = F.erode_mask(tm, thin_px)
        w_cells = max(1, int(round(tm.shape[1] / L.CELL_W)))
        if max_cols and w_cells > max_cols:
            scale = max_cols / w_cells
            w_cells = int(max_cols)
            h_cells = max(1, int(round(h_cells * scale)))
            tm = F.text_mask(text, int(h_cells * L.CELL_H), bold=bold)
            w_cells = max(1, int(round(tm.shape[1] / L.CELL_W)))
        if align == "center":
            c0 = int(round(c0 - w_cells / 2))
        elif align == "right":
            c0 = int(round(c0 - w_cells))
        if gain is None:
            gain = 2.1 if h_cells <= 5 else 2.2
        if hard is None:
            hard = 0.45
        self.paint_mask(tm, c0, r0, w_cells, h_cells, ramp=ramp or P.RAMP_BLOCK,
                        fg=fg, fg2=fg2, bg=bg, alpha=alpha, gain=gain,
                        min_v=0.04, shade_from=0.55, hard=hard)
        return int(r0), c0, h_cells, w_cells

    def paint_mask_colored(self, mask, c0, r0, w, h, color_fn, ramp=None, **kw):
        """Paint a coverage mask where colour depends on coverage value."""
        mask = np.asarray(mask, np.float32)
        w = max(1, int(round(w)))
        h = max(1, int(round(h)))
        if mask.shape[0] != h * L.CELL_H or mask.shape[1] != w * L.CELL_W:
            mask = F.resize_mask(mask, w * L.CELL_W, h * L.CELL_H)
        cells = mask.reshape(h, L.CELL_H, w, L.CELL_W).mean(axis=(1, 3))
        cells = np.clip(cells, 0, 1)
        ramp = ramp or P.RAMP_HI
        n = len(ramp) - 1
        r0, c0 = int(round(r0)), int(round(c0))
        for y in range(h):
            r = r0 + y
            if not (0 <= r < self.rows):
                continue
            for x in range(w):
                c = c0 + x
                if not (0 <= c < self.cols):
                    continue
                v = float(cells[y, x])
                if v < 0.02:
                    continue
                self.ch[r, c] = F.char_index(ramp[int(v * n + 0.5)])
                self.fg[r, c] = np.asarray(color_fn(v, y, x), np.uint8)
        return r0, c0, h, w

    # -- cell-level effects inside a region -------------------------------
    def scramble_region(self, r0, c0, r1, c1, rng, density=1.0):
        r0 = max(0, r0); c0 = max(0, c0)
        r1 = min(self.rows - 1, r1); c1 = min(self.cols - 1, c1)
        if r1 < r0 or c1 < c0:
            return
        h, w = r1 - r0 + 1, c1 - c0 + 1
        ncell = h * w
        sel = rng.random((h, w)) < density
        chars = rng.integers(1, len(F.IDX_CHARS), size=(h, w)).astype(np.int16)
        self.ch[r0:r1 + 1, c0:c1 + 1] = np.where(sel, chars, self.ch[r0:r1 + 1, c0:c1 + 1])
        self.ch[r0:r1 + 1, c0:c1 + 1] = np.where(
            sel & (rng.random((h, w)) < 0.25), 0, self.ch[r0:r1 + 1, c0:c1 + 1])

    def shift_region(self, r0, c0, r1, c1, dr, dc):
        r0 = max(0, r0); c0 = max(0, c0)
        r1 = min(self.rows - 1, r1); c1 = min(self.cols - 1, c1)
        if r1 < r0 or c1 < c0:
            return
        ch = self.ch[r0:r1 + 1, c0:c1 + 1].copy()
        fg = self.fg[r0:r1 + 1, c0:c1 + 1].copy()
        for rr in range(r0, r1 + 1):
            sr = rr - dr
            for cc in range(c0, c1 + 1):
                sc = cc - dc
                if r0 <= sr <= r1 and c0 <= sc <= c1:
                    self.ch[rr, cc] = ch[sr - r0, sc - c0]
                    self.fg[rr, cc] = fg[sr - r0, sc - c0]

    def tint_region(self, r0, c0, r1, c1, color, factor=1.0):
        r0 = max(0, r0); c0 = max(0, c0)
        r1 = min(self.rows - 1, r1); c1 = min(self.cols - 1, c1)
        if r1 < r0 or c1 < c0:
            return
        col = np.asarray(color, np.float32)
        self.fg[r0:r1 + 1, c0:c1 + 1] = (
            self.fg[r0:r1 + 1, c0:c1 + 1] * (1 - factor) + col * factor).astype(np.uint8)

    def dim_region(self, r0, c0, r1, c1, f=0.5):
        r0 = max(0, r0); c0 = max(0, c0)
        r1 = min(self.rows - 1, r1); c1 = min(self.cols - 1, c1)
        if r1 < r0 or c1 < c0:
            return
        self.fg[r0:r1 + 1, c0:c1 + 1] = (self.fg[r0:r1 + 1, c0:c1 + 1] * f).astype(np.uint8)

    # -- compose ----------------------------------------------------------
    def compose(self):
        atlas, _ = F.get_atlas()
        ch = np.asarray(self.ch, dtype=np.int32)
        mask = atlas[ch]                       # (R,C,H,W) uint8
        a = mask.astype(np.float32) * (1.0 / 255.0)
        fg = self.fg.astype(np.float32)
        bg = self.bg.astype(np.float32)
        a5 = a[:, :, :, :, None]
        out = np.empty(a5.shape[:4] + (3,), np.float32)
        np.multiply((fg - bg)[:, :, None, None, :], a5, out=out)
        np.add(out, bg[:, :, None, None, :], out=out)
        np.clip(out, 0, 255, out=out)
        out = out.astype(np.uint8)
        out = out.transpose(0, 2, 1, 3, 4).reshape(
            self.rows * L.CELL_H, self.cols * L.CELL_W, 3)
        return out

    def compose_rows(self, r0, r1):
        """Compose a horizontal band of rows only (cheaper for HUD redraws)."""
        atlas, _ = F.get_atlas()
        ch = np.asarray(self.ch[r0:r1 + 1], dtype=np.int32)
        mask = atlas[ch]
        a = mask.astype(np.float32) * (1.0 / 255.0)
        fg = self.fg[r0:r1 + 1].astype(np.float32)
        bg = self.bg[r0:r1 + 1].astype(np.float32)
        a5 = a[:, :, :, :, None]
        out = np.empty(a5.shape[:4] + (3,), np.float32)
        np.multiply((fg - bg)[:, :, None, None, :], a5, out=out)
        np.add(out, bg[:, :, None, None, :], out=out)
        np.clip(out, 0, 255, out=out)
        out = out.astype(np.uint8)
        n = r1 - r0 + 1
        return out.transpose(0, 2, 1, 3, 4).reshape(n * L.CELL_H, self.cols * L.CELL_W, 3)

    def to_image(self):
        return Image.fromarray(self.compose())


def stage_frame(bg=P.C["void"]):
    return Frame(L.STAGE_H, L.STAGE_W, bg=bg)
