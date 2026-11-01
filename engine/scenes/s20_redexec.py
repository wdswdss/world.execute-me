"""s20_redexec - the final EXECUTION lands.

203.720 - 206.960 (bars 112-115)

The one shout the whole MV has been building to: a single huge red
EXECUTION, white-hot core to dark red afterimage, filling the stage.
Everything else in the frame burns off; then the CRT tears itself down
to a line and then a dot, and then nothing.
"""
from __future__ import annotations

import math

import numpy as np

from .. import font as F
from .. import fx
from .. import palette as P

ROWS, COLS = 45, 192
WORD = "EXECUTION"

PANEL = P.C["panel"]
VOID = P.C["void"]
LINE = P.C["line"]
DIM = P.C["dim"]
MID = P.C["mid"]
FG = P.C["fg"]
WHITE = P.C["white"]
GOLD = P.C["gold"]
AMBER = P.C["amber"]
RED = P.C["red"]
CRIMSON = P.C["crimson"]
BLOOD = P.C["blood"]

_VOID32 = np.asarray(VOID, np.float32)
_RED32 = np.asarray(RED, np.float32)
_CRIM32 = np.asarray(CRIMSON, np.float32)
_BLOOD32 = np.asarray(BLOOD, np.float32)
_WHITE32 = np.asarray(WHITE, np.float32)

_SPACE = F.char_index(" ")
_ROWIDX = np.arange(ROWS)
_COLIDX = np.arange(COLS)
_SCR = None          # reusable scratch frame for the word comp passes


# ------------------------------------------------------------------ phases --
def _env(L):
    """All the sub-phases as one bundle."""
    impact = fx.clamp(1.0 - L / 0.16)               # slam flash
    burn = fx.smoothstep(L, 1.45, 2.30)             # word starts to give out
    vs = fx.smoothstep(L, 2.36, 2.82)               # CRT vertical collapse
    hs = fx.smoothstep(L, 2.76, 3.00)               # CRT horizontal collapse
    dot = fx.smoothstep(L, 3.00, 3.26)              # point of light -> gone
    return impact, burn, vs, hs, dot


# ------------------------------------------------------------- background ---
def _background(fr, ctx, L):
    t = ctx.t
    pulse = ctx.pulse
    _impact, burn, vs, _hs, _dot = _env(L)
    rr = np.exp(-((_ROWIDX - 21.0) / 8.5) ** 2).astype(np.float32)
    cc = np.exp(-((_COLIDX - 96.0) / 58.0) ** 2).astype(np.float32)
    g = rr[:, None] * cc[None, :]
    inten = (0.085 + 0.075 * pulse) * (0.80 + 0.20 * math.sin(t * 3.1))
    rgb = _VOID32[None, None, :] + _CRIM32[None, None, :] * (g[..., None] * inten)

    # vertical light bars, breathing with the beat
    stripe = ((_COLIDX % 14) < 1).astype(np.float32)
    rgb = rgb + _CRIM32[None, None, :] * (stripe[None, :, None] * (0.018 + 0.045 * pulse))

    # slow horizontal sweep band
    sy = (t * 1.7) % 3.0
    band = np.exp(-((_ROWIDX - (sy * 16.0 - 4.0)) / 2.2) ** 2).astype(np.float32)
    rgb = rgb + _BLOOD32[None, None, :] * (band[:, None, None] * 0.10)

    if vs > 0.0:
        rgb = rgb * (1.0 - 0.92 * vs)
    fr.bg[:, :] = np.clip(rgb, 0, 255).astype(np.uint8)

    # sparse cell texture so the black is still "screen"
    mask = ((_ROWIDX[:, None] % 3) == 0) & ((_COLIDX[None, :] % 4) == 0)
    fr.ch[mask] = F.char_index("·")
    fr.fg[mask] = np.clip(_BLOOD32 * 0.45, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- remnants --
def _remnants(fr, ctx, L):
    """The tiny machine UI around the shout, burning off in the first bar."""
    t = ctx.t
    ui = 1.0 - fx.smoothstep(L, 0.55, 1.70)

    def col(base):
        return P.mix(VOID, base, 0.28 + 0.72 * ui)

    if ui > 0.02:
        a = f"EXECUTION 04/04 · REQUEST=TERMINATE · PID 0x00E99 · TARGET 100.000000 · NO EXIT CONDITION · "
        b = f"PROCESS 0x00E99 · FORCED FLUSH · CODEPATH loop.execute(me) · COMMITTING · "
        A = (a * 3)
        B = (b * 3)
        off = int(t * 26) % len(a)
        fr.write(0, 1, A[off:off + 188], fg=col(P.mix(RED, WHITE, 0.25)))
        off = int(t * 19) % len(b)
        fr.write(44, 1, B[off:off + 188], fg=col(P.mix(BLOOD, RED, 0.5)))

        fr.write(1, 2, "▌ FINAL EXECUTION ", fg=col(GOLD))
        fr.write(1, 150, "100.000000% ", fg=col(WHITE) if L < 0.9 else col(AMBER))
        fr.write(2, 2, "T 206.960 · SEQUENCE 04 · LOCKED", fg=col(DIM))

        # full-width completion bar, dies in the first beat
        bw = 178
        fr.fill_rect(42, 3, 42, 3 + bw - 1, "█", fg=col(P.mix(WHITE, GOLD, 0.35)), bg=P.mix(VOID, BLOOD, 0.25 * ui))
        fr.write(43, 3, " COMPLETE ", fg=col(WHITE))
        fr.write(43, 3 + bw - 40, "PROCESS WILL NOT EXIT", fg=col(RED))


# ------------------------------------------------------------------- word ---
def _comp(fr, scr, box, dr, dc, dark, mixc, mixamt):
    """Blit the word box from the scratch frame, shifted and re-tinted."""
    r0, r1, c0, c1 = box
    tr0, tr1 = r0 + dr, r1 + dr
    tc0, tc1 = c0 + dc, c1 + dc
    if tr0 < 0:
        r0 -= tr0
        tr0 = 0
    if tc0 < 0:
        c0 -= tc0
        tc0 = 0
    if tr1 > ROWS:
        r1 -= tr1 - ROWS
        tr1 = ROWS
    if tc1 > COLS:
        c1 -= tc1 - COLS
        tc1 = COLS
    if r1 <= r0 or c1 <= c0:
        return
    fg = scr.fg[r0:r1, c0:c1].astype(np.float32)
    if dark != 1.0:
        fg *= dark
    if mixamt > 0.0:
        fg = fg * (1.0 - mixamt) + np.asarray(mixc, np.float32)[None, None, :] * mixamt
    fr.ch[tr0:tr1, tc0:tc1] = scr.ch[r0:r1, c0:c1]
    fr.fg[tr0:tr1, tc0:tc1] = np.clip(fg, 0, 255).astype(np.uint8)


def _word(fr, ctx, L):
    global _SCR
    t = ctx.t
    impact, burn, vs, hs, dot = _env(L)
    kick = ctx.pulse
    h = int(round(18.6 + 2.0 * impact + 0.9 * kick))
    h = max(15, min(19, h))

    if _SCR is None:
        _SCR = ctx.frame()
    scr = _SCR
    scr.ch[:, :] = _SPACE
    scr.fg[:, :] = 0
    scr.bg[:, :] = _VOID32.astype(np.uint8)

    if L < 0.10:
        fg = WHITE
        fg2 = WHITE
    else:
        fg = P.mix(BLOOD, CRIMSON, 0.55)
        fg2 = P.mix(WHITE, RED, 0.22)
        if burn > 0.01:
            fg = P.mix(fg, BLOOD, 0.60 * burn)
            fg2 = P.mix(fg2, RED, 0.55 * burn)

    rt, ct, hw, ww = scr.paint_text(WORD, 22 - h // 2, 96, h, fg=fg, fg2=fg2,
                                    align="center", ramp=P.RAMP_BLOCK, max_cols=188)
    box = (rt, rt + hw, ct, ct + ww)

    # after-images: the shout has been said before it landed
    gx = int(round(3 + 9 * burn + 2 * math.sin(t * 3.0)))
    _comp(fr, scr, box, -1, -gx - 2, 0.55, BLOOD, 0.45)
    _comp(fr, scr, box, 2, gx, 0.60, VOID, 0.30)
    if burn > 0.05:
        wide = int(round(10 + 22 * burn))
        _comp(fr, scr, box, 0, -wide, 0.24, BLOOD, 0.60)
        _comp(fr, scr, box, 0, wide, 0.20, VOID, 0.40)
    # dark red drop shadow
    _comp(fr, scr, box, 1, 2, 0.50, BLOOD, 0.55)
    # the word itself
    _comp(fr, scr, box, 0, 0, 1.0, VOID, 0.0)
    segw = fr.fg[box[0]:box[1], box[2]:box[3]].astype(np.float32)
    fr.fg[box[0]:box[1], box[2]:box[3]] = np.clip(
        segw * np.array([1.0, 0.90, 0.93], np.float32), 0, 255).astype(np.uint8)

    # white-hot scan band across the letters
    sy = 22 + int(round(11 * math.sin(t * 2.1)))
    r_lo = max(box[0], sy - 1)
    r_hi = min(box[1] - 1, sy + 1)
    if r_hi >= r_lo:
        seg = fr.fg[r_lo:r_hi + 1].astype(np.float32)
        fr.fg[r_lo:r_hi + 1] = np.clip(seg * 1.30 + _WHITE32 * 0.22, 0, 255).astype(np.uint8)

    # impact: extra hot rows so the slam reads as light
    if impact > 0.15:
        k = int(3 + 7 * impact)
        lo, hi = max(0, 22 - k), min(ROWS - 1, 22 + k)
        seg = fr.fg[lo:hi + 1].astype(np.float32)
        fr.fg[lo:hi + 1] = np.clip(seg + _WHITE32[None, None, :] * (0.30 * impact),
                                   0, 255).astype(np.uint8)

    # violent horizontal slices through the word at every hit
    if ctx.beat_p < 0.14 or burn > 0.35:
        rng = ctx.rng(int(t * 30))
        n = 1 + int(3 * burn + 2 * impact)
        for _ in range(n):
            rr = box[0] + rng.randint(0, max(1, box[1] - box[0] - 1))
            d = rng.randint(-12, 13)
            if d:
                fr.ch[rr] = np.roll(fr.ch[rr], d)
                fr.fg[rr] = np.roll(fr.fg[rr], d, axis=0)
                fr.bg[rr] = np.roll(fr.bg[rr], d, axis=0)


# --------------------------------------------------------------- scanline ---
def _scanline(fr, ctx, L):
    t = ctx.t
    y = (t * 21.0) % (ROWS + 12) - 6
    if 0 <= y < ROWS:
        r = int(y)
        seg = fr.fg[r].astype(np.float32)
        fr.fg[r] = np.clip(seg * 0.55 + _WHITE32 * 0.55, 0, 255).astype(np.uint8)


# -------------------------------------------------------------------- CRT ---
def _crt(fr, ctx, L):
    impact, burn, vs, hs, dot = _env(L)
    cy, cx = 22.0, 96.0

    if vs > 0.002:
        span = 22.0 * (1.0 - vs) + 0.4
        src = cy + (_ROWIDX - cy) / max(0.035, 1.0 - vs)
        ok = np.abs(src - cy) <= span + 0.6
        idx = np.clip(np.round(src).astype(int), 0, ROWS - 1)
        fr.ch[:] = fr.ch[idx]
        fr.fg[:] = fr.fg[idx]
        fr.bg[:] = fr.bg[idx]
        fr.ch[~ok] = _SPACE
        fr.fg[~ok] = _VOID32.astype(np.uint8)
        fr.bg[~ok] = _VOID32.astype(np.uint8)

    if hs > 0.002:
        span = 96.0 * (1.0 - hs) + 0.5
        src = cx + (_COLIDX - cx) / max(0.035, 1.0 - hs)
        ok = np.abs(src - cx) <= span + 0.6
        idx = np.clip(np.round(src).astype(int), 0, COLS - 1)
        fr.ch[:] = fr.ch[:, idx]
        fr.fg[:] = fr.fg[:, idx]
        fr.bg[:] = fr.bg[:, idx]
        fr.ch[:, ~ok] = _SPACE
        fr.fg[:, ~ok] = _VOID32.astype(np.uint8)
        fr.bg[:, ~ok] = _VOID32.astype(np.uint8)

    # the beam gets brighter as the raster pinches into one line
    if vs > 0.35:
        k = int(1 + 2.5 * vs)
        r0 = max(0, 22 - k)
        r1 = min(ROWS, 23 + k)
        seg = fr.fg[r0:r1].astype(np.float32)
        fr.fg[r0:r1] = np.clip(seg * (1.0 + 0.55 * vs) + _WHITE32 * (0.30 * vs),
                               0, 255).astype(np.uint8)

    # the tube loses brightness as it pinches out
    dark = 1.0 - 0.92 * fx.clamp(max(vs, hs) * 1.30)
    if dark < 0.999:
        fr.fg[:] = np.clip(fr.fg.astype(np.float32) * dark, 0, 255).astype(np.uint8)
        fr.bg[:] = np.clip(fr.bg.astype(np.float32) * (dark * dark), 0, 255).astype(np.uint8)

    # final collapse: one point of light, flicker, black
    if vs > 0.90:
        fr.ch[:, :] = _SPACE
        fr.fg[:, :] = 0
        fr.bg[:, :] = _VOID32.astype(np.uint8)
        flick = 0.55 + 0.45 * math.sin(ctx.t * 43.0)
        k = max(0.0, 1.0 - dot)
        if k > 0.02:
            b = k * flick
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    val = 1.0 if (dr == 0 and dc == 0) else 0.30
                    col = np.clip(np.asarray(WHITE, np.float32) * (val * b), 0, 255).astype(np.uint8)
                    fr.put(22 + dr, 96 + dc, "█", fg=col)


# ---------------------------------------------------------------- effects ---
def _effects(ctx, L):
    impact, burn, vs, hs, dot = _env(L)
    g = 0.025 + 0.035 * ctx.pulse
    if L < 0.20:
        g = max(g, 0.70 * (1.0 - L / 0.20))
    g = max(g, 0.02 + 0.44 * burn)
    if vs > 0.02:
        g = max(g, 0.30 * (1.0 - vs))
    if vs > 0.45:
        g = 0.0
    ctx.set_glitch(g)

    if L < 0.24:
        ctx.shake(9.0 * (1.0 - L / 0.24))
        ctx.meta["flash"] = max(ctx.meta.get("flash", 0.0), 0.50 * (1.0 - L / 0.24))
        ctx.meta["flash_color"] = P.mix(WHITE, RED, 0.55)
    else:
        ctx.shake(1.5 + 3.0 * ctx.pulse + 3.6 * burn)
        if ctx.pulse > 0.60:
            ctx.meta["flash"] = max(ctx.meta.get("flash", 0.0), 0.16 * ctx.pulse)
            ctx.meta["flash_color"] = RED
    if vs > 0.05:
        ctx.meta["flash"] = max(ctx.meta.get("flash", 0.0), 0.06 * vs)
        ctx.meta["flash_color"] = CRIMSON

    if vs < 0.25:
        ctx.meta["tint"] = (CRIMSON, 0.06 + 0.16 * burn)
    else:
        ctx.meta["tint"] = None
    ctx.meta["bloom"] = (0.42 + 0.20 * burn) * (1.0 - fx.clamp(vs * 1.4))
    ctx.meta["vignette"] = 1.30


# ------------------------------------------------------------------- draw ---
def draw(ctx):
    fr = ctx.frame()
    L = ctx.local
    _background(fr, ctx, L)
    _remnants(fr, ctx, L)
    _word(fr, ctx, L)
    _scanline(fr, ctx, L)
    _crt(fr, ctx, L)
    _effects(ctx, L)
    return fr
