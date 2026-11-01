#!/usr/bin/env python
"""Poster / cover art for the world.execute(me); MV.

The cover is drawn with the same engine as the film (192x60 cell grid, CRT
post pass), so it sits in the same visual language:

    * a wide lemniscate in the background, with one band of light running
      along the curve  (the song's "if I approach infinity")
    * a gold heart pinned exactly where the two loops cross  (the "me")
    * the title in three colour parts, with "ME" in gold
    * the song's signature couplet in the subtitle strip
    * the full-song waveform in the footer strip

Usage:
    MV_SCALE=2 python tools/cover.py --out out/cover_4k.png
    MV_SCALE=1 python tools/cover.py --out out/cover_1080.png
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import layout as L          # noqa: E402
from engine import palette as P         # noqa: E402
from engine import font as F            # noqa: E402
from engine import sceneapi             # noqa: E402
from engine import timeline as TL       # noqa: E402
from engine.frame import Frame          # noqa: E402
from engine.chrome import Chrome        # noqa: E402
from engine.post import get_post        # noqa: E402

MB = P.RAMP_BLOCK


# ------------------------------------------------------------------ helpers --
def inf_cov_u(w, h, thick=0.16, ss=4):
    """Cell-resolution coverage + curve parameter of a lemniscate."""
    m = F.infinity_mask(w * ss, h * ss, thick=thick)
    cov = m.reshape(h, ss, w, ss).mean(axis=(1, 3)).astype(np.float32)
    n = 720
    a = np.arange(n) / n * 2 * np.pi
    st, ct = np.sin(a), np.cos(a)
    den = 1.0 + st * st
    px = (ct / den) * (w * 0.46) + w * 0.5
    py = (st * ct / den)
    span = float(np.abs(py).max()) + 1e-6
    py = py / span * (h * 0.44) + h * 0.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xx.ravel()[:, None] - px[None, :]) ** 2
         + (yy.ravel()[:, None] - py[None, :]) ** 2)
    u = (d.argmin(1) / n).reshape(h, w).astype(np.float32)
    return cov, u


def ramp_chars(vals, ramp=MB):
    n = len(ramp) - 1
    idx = np.clip(np.round(np.asarray(vals) * n), 0, n).astype(np.int16)
    table = np.array([F.char_index(c) for c in ramp], np.int16)
    return table[idx]


def stamp(stage, cells, r0, c0, chars, col, min_v=0.05):
    """Write pre-computed cells/chars/colours into the stage (clipped)."""
    h, w = cells.shape
    r0, c0 = int(round(r0)), int(round(c0))
    y0 = max(0, r0); x0 = max(0, c0)
    y1 = min(stage.rows, r0 + h); x1 = min(stage.cols, c0 + w)
    if y1 <= y0 or x1 <= x0:
        return
    sy, sx = y0 - r0, x0 - c0
    sl = np.s_[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    m = cells[sl] >= min_v
    ch = stage.ch[y0:y1, x0:x1]
    ch[m] = chars[sl][m]
    fg = stage.fg[y0:y1, x0:x1]
    fg[m] = col[sl][m]


def heart_filled(w, h):
    """Filled heart coverage mask (F.heart_mask only keeps the outline band)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = (xx / max(1, w) - 0.5) * 2.6
    y = -(yy / max(1, h) - 0.52) * 2.6
    f = (x * x + y * y - 1) ** 3 - x * x * y * y * y
    m = (f <= 0).astype(np.float32)
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(max(1.0, w / 90.0)))
    return np.asarray(im, np.float32) / 255.0


def tint(arr, col, k=1.0):
    a = np.zeros(arr.shape + (3,), np.float32)
    a[:] = np.asarray(col, np.float32) * k
    return a


# ------------------------------------------------------------------- layout --
INF_W, INF_H = 112, 26
INF_R0, INF_C0 = 3, 40          # stage rows/cols
HERO_C = 96                     # stage centre column
TITLE_H = 9
TITLE_R0 = 30
HEART_W, HEART_H = 19, 13


def draw_infinity(stage, t_light=41.3, gain=1.0):
    cov, u = inf_cov_u(INF_W, INF_H, thick=0.115)
    flow = np.mod(u - t_light * 0.55, 1.0)
    band = (0.5 + 0.5 * np.cos(2 * np.pi * flow)) ** 2
    head = np.exp(-((np.mod(flow + 0.5, 1.0) - 0.5) / 0.055) ** 2)
    b = np.clip(band * 1.25, 0, 1)
    hd = np.clip(head, 0, 1)
    bright = np.clip(cov * (0.30 + 0.60 * b + 0.85 * hd) * gain, 0, 1)

    # chromatic fringe: one dim red copy left, one dim teal copy right
    for dx, col in ((-2, P.C["red"]), (2, P.C["teal"])):
        cells = bright * 0.55
        stamp(stage, cells, INF_R0, INF_C0 + dx, ramp_chars(cells),
              tint(cells, col, 1.0).astype(np.uint8), min_v=0.10)

    teal = np.asarray(P.C["dim"], np.float32)
    gold = np.asarray(P.C["gold"], np.float32)
    white = np.asarray(P.C["white"], np.float32)
    col = teal[None, None, :] * (1 - b[..., None]) + gold[None, None, :] * b[..., None]
    col = col * (1 - 0.70 * hd[..., None]) + white[None, None, :] * (0.70 * hd[..., None])
    stamp(stage, bright, INF_R0, INF_C0, ramp_chars(bright), col.astype(np.uint8),
          min_v=0.05)


def draw_heart(stage, r0=None, c0=None):
    r0 = INF_R0 + INF_H // 2 - HEART_H // 2 if r0 is None else r0
    c0 = HERO_C - HEART_W // 2 if c0 is None else c0
    m = heart_filled(HEART_W * 16, HEART_H * 16)
    span_r, span_c = HEART_H // 2, HEART_W // 2

    def color_fn(v, y, x):
        dy = (y - (HEART_H - 1) * 0.44) / max(1e-3, span_r * 0.95)
        dx = (x - (HEART_W - 1) * 0.5) / max(1e-3, span_c * 0.92)
        r = min(1.0, (dx * dx + dy * dy) ** 0.5)
        base = P.mix("amber", "gold", 1.0 - r)
        return P.mix(base, "white", max(0.0, 1.0 - r * 1.55))

    stage.paint_mask_colored(m, c0, r0, HEART_W, HEART_H, color_fn,
                             ramp=" ░▒▓█", gain=1.5)


def draw_title(stage, h_cells=TITLE_H, r0=TITLE_R0, center=HERO_C):
    """Three-part title: world.execute( / ME / );  -- 'ME' carried in gold."""
    parts = [
        ("WORLD.EXECUTE(", P.C["primary"], P.C["white"]),
        ("ME", P.C["gold"], P.C["white"]),
        (");", P.C["white"], P.C["white"]),
    ]
    # paint into a scratch frame, then centre by measured ink bbox
    tmp = Frame(h_cells, 256)
    tmp.clear(bg=P.C["void"])
    x = 1
    for txt, fg, fg2 in parts:
        _r0, c0, _h, w = tmp.paint_text(txt, 0, x, h_cells, fg=fg, fg2=fg2,
                                        bold=True, align="left", ramp=MB)
        x = c0 + w
    nz = np.argwhere(tmp.ch != 0)
    if not len(nz):
        return
    c0i, c1i = int(nz[:, 1].min()), int(nz[:, 1].max())
    off = int(round(center - (c0i + c1i + 1) / 2.0))
    for y in range(h_cells):
        for c in range(c0i, c1i + 1):
            cc = c + off
            rr = r0 + y
            if 0 <= cc < stage.cols and 0 <= rr < stage.rows:
                stage.ch[rr, cc] = tmp.ch[y, c]
                stage.fg[rr, cc] = tmp.fg[y, c]
    return c0i + off, c1i - c0i + 1


def draw_side_panels(stage):
    """Micro HUD quotes at the stage edges (the song's own maths)."""
    left = [
        ("APPROACH INFINITY", P.C["teal"]),
        ("n     = 10^42", P.C["dim"]),
        ("|f-L| = 7.06e-03", P.C["dim"]),
        ("x     = 26.89%", P.C["dim"]),
        ("lim f(x) = L", P.C["gold"]),
    ]
    right = [
        ("MY LIMITATIONS", P.C["red"]),
        ("#      BOUND 1", P.C["dim"]),
        ("###    BOUND 3", P.C["dim"]),
        ("#####  BOUND 5", P.C["dim"]),
        ("count = 5 / 5", P.C["amber"]),
    ]
    r0 = 7
    for i, (txt, col) in enumerate(left):
        stage.write(r0 + i, 3, txt, fg=col)
    for i, (txt, col) in enumerate(right):
        stage.write(r0 + i, L.COLS - 3 - len(txt), txt, fg=col)
    # hairline rules under each quote block
    for c in range(3, 3 + 22):
        stage.put(r0 + len(left), c, "─", fg=P.C["line"])
    for c in range(L.COLS - 3 - 18, L.COLS - 2):
        stage.put(r0 + len(right), c, "─", fg=P.C["line"])


def draw_artist(stage, r0, c0=HERO_C):
    txt = "M I L I"
    c0 = c0 - len(txt) // 2
    stage.write(r0, c0, txt, fg=P.C["gold"])
    for i in range(2, 13):
        stage.put(r0, c0 - i, "─", fg=P.C["line"])
        stage.put(r0, c0 + len(txt) - 1 + i, "─", fg=P.C["line"])


def draw_frame_marks(stage):
    r0, r1 = 2, L.STAGE_H - 1
    c0, c1 = 1, L.COLS - 2
    for r, c, ch in ((r0, c0, "┌"), (r0, c1, "┐"), (r1, c0, "└"), (r1, c1, "┘")):
        stage.put(r, c, ch, fg=P.C["line"])
    for c in range(c0 + 2, c0 + 9):
        stage.put(r0, c, "─", fg=P.C["line"])
        stage.put(r1, c, "─", fg=P.C["line"])
        stage.put(r0, c1 - (c - c0), "─", fg=P.C["line"])
        stage.put(r1, c1 - (c - c0), "─", fg=P.C["line"])
    for r in range(r0 + 2, r0 + 6):
        stage.put(r, c0, "│", fg=P.C["line"])
        stage.put(r, c1, "│", fg=P.C["line"])
        stage.put(r1 - (r - r0), c0, "│", fg=P.C["line"])
        stage.put(r1 - (r - r0), c1, "│", fg=P.C["line"])


def draw_footer_wave(fr, assets):
    """Full-song waveform in the bottom strip (replaces the playhead scroll)."""
    row = L.FOOT_Y + L.FOOT_H - 1
    rms = np.asarray(assets.rms, np.float64)
    n = len(rms)
    nb = 140
    edges = (np.arange(nb + 1) / nb * (n - 1)).astype(int)
    vals = np.array([
        np.sqrt(np.mean(rms[edges[k]:max(edges[k] + 1, edges[k + 1] + 1)] ** 2))
        for k in range(nb)])
    vals = (vals - vals.min()) / max(1e-6, vals.max() - vals.min())
    ramp = " ▁▂▃▄▅▆▇█"
    for k in range(nb):
        c = 12 + k
        v = float(vals[k])
        ch = ramp[max(1, min(8, int(round(v * 8))))]
        col = P.mix(P.C["void"], P.C["gold"], 0.42 + 0.58 * v)
        fr.put(row, c, ch, fg=col, bg=P.C["void"])
    # playhead at the "approach infinity" line  (41.35 / 215.9)
    pc = 12 + int(round(41.35 / L.DURATION * nb))
    fr.put(row, pc, "▍", fg=P.C["white"], bg=P.C["void"])
    fr.write(row, 4, f"{int(41.35 // 60)}:{int(41.35 % 60):02d}",
             fg=P.C["gold"], bg=P.C["void"])


# --------------------------------------------------------------------- main --
def build():
    assets = sceneapi.A.get_assets()
    stage = Frame(L.STAGE_H, L.STAGE_W)
    stage.clear(bg=P.C["void"])

    # ---- faint star dust ---------------------------------------------------
    rng = np.random.default_rng(11)
    for _ in range(120):
        r = int(rng.integers(0, L.STAGE_H))
        c = int(rng.integers(0, L.COLS))
        ch = "+" if rng.random() < 0.25 else "·"
        stage.put(r, c, ch, fg=P.mix(P.C["void2"], P.C["grid"], float(rng.random())))

    draw_frame_marks(stage)
    draw_side_panels(stage)
    draw_infinity(stage, t_light=41.3)
    draw_heart(stage)
    draw_artist(stage, r0=40)
    draw_title(stage)

    # ---- chrome + footer ---------------------------------------------------
    chrome = Chrome()
    fr = chrome.build(stage, 211.4, "s03_infinity", assets,
                      extra={"sem": "THE LOOP REMAINS"})
    draw_footer_wave(fr, assets)

    # ---- CRT post + the couplet -------------------------------------------
    img = fr.compose()
    meta = {"glitch": 0.0, "bloom": 0.50, "grain": 0.7, "shake": (0, 0)}
    img = get_post().process(img, 4444, 38.0, meta)
    # pixel-level CRT fringe (cell-level shifts read as double-printing)
    d = 3 * L.SCALE
    img[:, :, 0] = np.roll(img[:, :, 0], d, axis=1)
    img[:, :, 2] = np.roll(img[:, :, 2], -d, axis=1)

    idx, ln = TL.line_at(44.4)
    t_sub = (ln["t1"] - 0.06) if ln else 44.4
    img = chrome.draw_subtitles(img, t_sub)
    return Image.fromarray(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "cover.png"))
    ap.add_argument("--thumb", default=None)
    args = ap.parse_args()
    im = build()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    im.save(args.out)
    print("wrote", args.out, im.size)
    th = args.thumb or os.path.splitext(args.out)[0] + "_thumb320.png"
    im.resize((320, 180), Image.LANCZOS).save(th)
    print("wrote", th)


if __name__ == "__main__":
    main()
