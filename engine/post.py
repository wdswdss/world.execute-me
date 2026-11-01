"""CRT post-processing: scanlines, bloom, glitch, chromatic split, grain.

Everything is a pure function of (image, frame_index, time, meta), so any
frame can be rendered independently (stills, parallel chunks) and look the
same.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from . import layout as L

W, H = L.PX_W, L.PX_H


class Post:
    def __init__(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        nx = xx / (W - 1) * 2 - 1
        ny = yy / (H - 1) * 2 - 1
        r = np.sqrt(nx * nx * 0.86 + ny * ny)
        vig = np.clip(1.06 - 0.26 * r ** 2.1, 0.58, 1.0).astype(np.float32)
        self.vig = vig[:, :, None]
        # scanline mask: every 3rd pixel row darker, 2nd slightly
        pat = np.ones(H, np.float32)
        pat[0::3] = 0.90
        pat[1::3] = 0.96
        self.scan = pat[:, None, None].astype(np.float32)
        # aperture grille: slight horizontal RGB alternation
        gr = np.ones((H, W, 3), np.float32)
        gr[:, 0::3, 0] = 1.05
        gr[:, 1::3, 1] = 1.05
        gr[:, 2::3, 2] = 1.05
        self.grille = gr
        # fused scanline * aperture * vignette multiplier (single pass in process())
        self.mul = (self.scan * self.grille * self.vig).astype(np.float32)
        self.sweep_y = None

    # ------------------------------------------------------------------
    def process(self, img, fi, t, meta):
        f = img.astype(np.float32)
        meta = meta or {}
        g = float(meta.get("glitch", 0.0))
        rng = np.random.default_rng((int(fi) * 2654435761 + 12345) & 0x7FFFFFFF)

        # camera shake (with black edges, no wrap)
        sx, sy = meta.get("shake", (0, 0))
        if sx or sy:
            f = _shift(f, int(sx), int(sy))

        # glitch: horizontal tearing + channel split + block corruption
        if g > 0.02:
            f = self._glitch(f, fi, g, rng)

        # flash
        fl = float(meta.get("flash", 0.0))
        if fl > 0.001:
            fc = np.asarray(meta.get("flash_color", (255, 255, 255)), np.float32)
            f = f * (1 - fl) + fc * fl

        # tint (per-scene colour grade)
        tint = meta.get("tint")
        if tint:
            col, amt = tint
            f = f * (1 - amt) + np.asarray(col, np.float32) * amt

        # bloom: soft phosphor glow around bright cells (kept subtle so text
        # stays crisp)
        bl = float(meta.get("bloom", 0.35))
        if bl > 0.01:
            np.add(f, self._bloom(f, bl), out=f, casting="unsafe")

        # scanlines + aperture grille + vignette in one fused multiply
        f *= self.mul

        # moving refresh band
        y = int((t * 260.0) % (H + 240)) - 120
        y0 = max(0, y - 40)
        y1 = min(H, y + 40)
        if y1 > y0:
            xs = np.arange(y0, y1, dtype=np.float32)
            band = np.exp(-((xs - y) / 18.0) ** 2) * 8.9
            f[y0:y1] += band[:, None, None]

        # ---- global decay: the run gets dirtier the longer it goes on -----
        from . import layout as _L
        _dur = getattr(_L, "DURATION", 215.9)
        dec = max(0.0, min(1.0, (float(t) - 24.0) / max(1.0, _dur - 40.0)))
        if dec > 0.001:
            # slowly widening chromatic fringe (monotonic, never resets)
            k = int(round(dec * 1.6 * getattr(_L, "SCALE", 1)))
            if k >= 1:
                f[:, :, 0] = np.roll(f[:, :, 0], k, axis=1)
                f[:, :, 2] = np.roll(f[:, :, 2], -k, axis=1)
            # darker edges + a faint vertical hold wobble
            f *= 1.0 - 0.10 * dec
            wob = int(round(1.0 * dec))
            if wob >= 1 and (int(t * 30) // 7) % 9 == 0:
                f = _shift(f, 0, wob)

        # grain + flicker (uniform noise: cheaper than gaussian, same film feel)
        gr = float(meta.get("grain", 1.0)) * (1.0 + 0.85 * dec)
        if gr > 0.01:
            amp = 3.1 * gr
            noise = rng.random((H, W, 1), dtype=np.float32)
            noise -= 0.5
            noise *= amp
            f += noise
            f *= 1.0 + 0.02 * gr * (rng.random() - 0.5) * 2

        # ---- two-frame reboot at the cut to black -------------------------
        # a dark blink, not a white strobe: safer on phone screens / eyes
        _fb = int(round(float(t) * 60.0))
        if _fb in (12531, 12532):
            f *= 0.30
            f[::3] += 26.0

        np.clip(f, 0, 255, out=f)
        return f.astype(np.uint8)

    # ------------------------------------------------------------------
    def _glitch(self, f, fi, g, rng):
        h, w = f.shape[:2]
        out = f.copy()
        # horizontal tearing
        n = int(2 + g * 16)
        for _ in range(n):
            y = int(rng.integers(0, h))
            hh = int(rng.integers(2, max(3, int(8 + g * 90))))
            y1 = min(h, y + hh)
            dx = int(rng.integers(-int(8 + g * 140), int(8 + g * 140) + 1))
            out[y:y1] = np.roll(out[y:y1], dx, axis=1)
            if rng.random() < 0.35:
                out[y:y1] = out[y:y1, ::-1] if rng.random() < 0.2 else out[y:y1]
        # channel split
        d = int((1 + g * 9) * getattr(L, 'SCALE', 1))
        out[:, :, 0] = np.roll(out[:, :, 0], d, axis=1)
        out[:, :, 2] = np.roll(out[:, :, 2], -d, axis=1)
        # corrupted blocks: keep structure (rolls / replacements / channel swaps),
        # never flat grey washes -- those read as dead rectangles, not CRT glitch
        nb = min(5, int(g * 14))
        for _ in range(nb):
            bw = int(rng.integers(24, 260))
            bh = int(rng.integers(10, 64))
            x = int(rng.integers(0, max(1, w - bw)))
            y = int(rng.integers(0, max(1, h - bh)))
            r = rng.random()
            blk = out[y:y + bh, x:x + bw]
            if r < 0.45:
                out[y:y + bh, x:x + bw] = np.roll(blk, int(rng.integers(-80, 80)), axis=1)
            elif r < 0.70:
                # borrow a different strip of the frame (structure-preserving corruption)
                ox = int(rng.integers(0, max(1, w - bw)))
                oy = int(rng.integers(0, max(1, h - bh)))
                out[y:y + bh, x:x + bw] = out[oy:oy + bh, ox:ox + bw]
            elif r < 0.88:
                # per-row tear inside the block
                offs = rng.integers(-24, 25, size=bh)
                for i in range(bh):
                    out[y + i, x:x + bw] = np.roll(blk[i], int(offs[i]))
            else:
                # channel-rotation artefact (keeps luminance structure)
                b = blk.astype(np.int16)
                out[y:y + bh, x:x + bw] = np.stack(
                    [b[:, :, 1], b[:, :, 2], b[:, :, 0]], axis=2).astype(np.float32)
        # horizontal noise lines
        nl = int(g * 22)
        for _ in range(nl):
            y = int(rng.integers(0, h))
            out[y] = out[y] * 0.55 + rng.random(w)[:, None] * 120
        return out

    def _us_blur(self, f):
        from PIL import Image as _I, ImageFilter as _F
        im = _I.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        return np.asarray(im.filter(_F.GaussianBlur(1.1)), dtype=np.float32)

    def _bloom(self, f, strength):
        small = f.reshape(H // 4, 4, W // 4, 4, 3).mean(axis=(1, 3))
        bright = np.clip(small - 150.0, 0, 255.0) * (255.0 / 105.0)
        lum = bright.mean(axis=2, keepdims=True)
        src = bright * 0.7 + lum * 0.3 * np.array([0.55, 0.9, 1.0], np.float32)
        src *= 0.50 * strength
        np.clip(src, 0, 255, out=src)
        im = Image.fromarray(src.astype(np.uint8)).filter(ImageFilter.GaussianBlur(7))
        return np.asarray(im.resize((W, H), Image.BILINEAR))

    def frame_render(self, chrome_frame, fi, t, meta, caption_fn=None):
        img = chrome_frame.compose()
        if caption_fn is not None:
            img = caption_fn(img, t)
        return self.process(img, fi, t, meta)


def _shift(f, dx, dy):
    out = np.zeros_like(f)
    h, w = f.shape[:2]
    x0, x1 = max(0, dx), w + min(0, dx)
    y0, y1 = max(0, dy), h + min(0, dy)
    if x1 > x0 and y1 > y0:
        out[y0:y1, x0:x1] = f[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    return out


_POST = None


def get_post():
    global _POST
    if _POST is None:
        _POST = Post()
    return _POST
