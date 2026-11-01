"""s21_endtext - the machine goes quiet.

206.960 - 211.905 (tail)

Nothing but the sentence, typed into the dark after the music has stopped,
and a cursor that keeps looping because the process has no exit.
No Chinese on stage; the chrome owns the subtitle strip.
"""
from __future__ import annotations

import math

import numpy as np

from .. import font as F
from .. import fx
from .. import palette as P
from .. import layout as LAYOUT
from .. import timeline as TL

ROWS, COLS = 45, 192

T0, T1 = 206.960, LAYOUT.DURATION
LINE = TL.END_TEXT_EN                      # "PROCESS ENDED. THE LOOP REMAINS."
COLLAPSE_END = 4 * 0.461538                 # exactly 4 beats of collapse
TYPE_START = T0 + COLLAPSE_END + 0.038
CPS = 13.5
TEXT_ROW = 21
TEXT_COL = 96 - len(LINE) // 2              # 80

VOID = P.C["void"]
PANEL = P.C["panel"]
LINE_C = P.C["line"]
DIM = P.C["dim"]
FG = P.C["fg"]
WHITE = P.C["white"]
TEAL = P.C["teal"]
RED = P.C["red"]

_VOID32 = np.asarray(VOID, np.float32)
_ROWIDX = np.arange(ROWS)

_DOT = F.char_index("·")
_SPACE = F.char_index(" ")
_HAIR = F.char_index("─")

# fixed faint noise field: positions, phases
_NRNG = np.random.default_rng(1729)
_NPOS = _NRNG.random((ROWS, COLS))
_NPHASE = _NRNG.random((ROWS, COLS)) * 6.283
_NMASK = _NPOS > 0.9845
_NMASK[19:24, TEXT_COL - 6:TEXT_COL + len(LINE) + 6] = False

_DONE_T = TYPE_START + len(LINE) / CPS     # 210.55 completion time


# ---------------------------------------------------------------- helpers --
def _since(t):
    return t - T0


def _typed(t):
    n = int(max(0.0, (t - TYPE_START) * CPS))
    return min(len(LINE), n)


# ------------------------------------------------------------------- draw ---
def draw(ctx):
    t = ctx.t
    L = t - T0
    fr = ctx.frame()

    if L >= COLLAPSE_END:
        ctx.meta["clean"] = True
    if L < COLLAPSE_END:
        _collapse(fr, ctx, L)
        _fade(fr, ctx.meta, 0.0)
        ctx.meta["glitch"] = 0.0
        return fr

    _dark(fr)
    _noise(fr, ctx)
    _band(fr, L)
    _carry_dot(fr, L)
    _sentence(fr, ctx, L)
    _fade(fr, ctx.meta, L)
    return fr


_CODE_LINES = (
    "loop.execute(me)  rc=0  pid=0x00E99  target=100.000000  no exit condition",
    "world.simulate(cycle=1)  state=RUNNING  heartbeat=130  loop=0x1  frame=06357",
    "for(int i=0;i<INF;i++){ love(i); execute(i); }  // never returns",
    "if(human==NULL){ loop(); } else { loop(); }  stack overflow / love not computable",
    "cmp tgt,0x64  jne loop  ; ld x0,heart  beq x0,zero,forever  b loop",
    "print('PROCESS ENDED.'); print('THE LOOP REMAINS.'); while(1){}",
    "kernel: 0x00E99  mem=0x7FF2A0  threads=4  locks=0  uptime=00:03:26.96",
    "do { you = mine; mine = you; } while (you != mine);  // unreachable",
)


def _code_grid():
    grid = np.full((ROWS, COLS), 0, np.uint8)
    for r in range(ROWS):
        line = _CODE_LINES[r % len(_CODE_LINES)]
        for c in range(COLS):
            ch = line[(c + r * 7) % len(line)]
            if ch != " ":
                grid[r, c] = F.char_index(ch)
    return grid


_CG = _code_grid()


def _collapse(fr, ctx, L):
    """The whole screen (stage + chrome) folds into a single line."""
    from engine import layout as LAYOUT
    from engine import sceneapi as _SA
    from engine.sceneapi import Ctx as _Ctx
    from engine.scenes import s20_redexec as _S20
    k = fx.clamp(L / 1.05)
    ease = k * k * (3 - 2 * k)
    scale = max(0.012, 1.0 - 0.988 * ease)
    # paint the previous scene, so the fold carries real content
    try:
        prev = _S20.draw(_Ctx(T0 - 0.55))
        fr.ch[:, :] = prev.ch
        fr.fg[:, :] = prev.fg
        fr.bg[:, :] = prev.bg
    except Exception:
        pass
    # code current running through the frame before it folds
    scroll = int(ctx.t * 90.0)
    a = 0.85 * (1.0 - fx.smoothstep(L, 0.75, 1.15))
    rows = fr.rows
    cols = fr.cols
    for r in range(rows):
        row = _CG[(r + 3) % len(_CG)]
        for c in range(cols):
            if (c + scroll + r * 11) % 23:
                continue
            g = int(row[(c + scroll + r * 11) % len(row)])
            if not g:
                continue
            fr.ch[r, c] = g
            fr.fg[r, c] = P.mix(VOID, WHITE, a * 0.45)
    if L > 0.92:
        w = 1.0 - fx.smoothstep(L, 0.94, 1.22)
        line_row = int(round(rows / 2.0))
        if 0 <= line_row < rows:
            fr.ch[line_row, :] = _HAIR
            fr.fg[line_row, :] = P.mix(VOID, WHITE, 0.22 + 0.70 * w)
            for c in range(0, cols, 12):
                fr.put(line_row, c, "┬", fg=P.mix(VOID, WHITE, 0.55 * w))
    ctx.meta["collapse"] = scale
    ctx.meta["glitch"] = 0.0
    ctx.meta["bloom"] = 0.50
    ctx.meta["grain"] = 0.8

# ------------------------------------------------------------------ layer 0 -
def _dark(fr):
    rr = np.exp(-((_ROWIDX - 21.0) / 16.0) ** 2).astype(np.float32)
    halo = np.asarray(P.mix(VOID, LINE_C, 0.30), np.float32)
    rgb = _VOID32[None, None, :] + halo[None, None, :] * (rr[:, None, None] * 0.10)
    fr.bg[:, :] = np.clip(rgb, 0, 255).astype(np.uint8)


def _noise(fr, ctx):
    t = ctx.t
    fi = ctx.fi
    idx = np.nonzero(_NMASK)
    if len(idx[0]):
        ph = _NPHASE[idx]
        tw = 0.5 + 0.5 * np.sin(fi * 0.42 + ph * 6.0 + np.arange(len(ph)) * 0.7)
        lvl = 0.10 + 0.42 * tw
        col = np.asarray(P.mix(VOID, LINE_C, 0.55), np.float32)[None, :] * lvl[:, None]
        fr.ch[idx] = _DOT
        fr.fg[idx] = np.clip(col, 0, 255).astype(np.uint8)
    sy = int((t * 2.2) % (ROWS + 10)) - 5
    if 0 <= sy < ROWS:
        seg = fr.bg[sy].astype(np.float32)
        fr.bg[sy] = np.clip(seg + np.asarray(P.mix(VOID, LINE_C, 0.55), np.float32)[None, :] * 0.10,
                            0, 255).astype(np.uint8)


def _band(fr, L):
    k = fx.smoothstep(L, 0.0, 0.42)
    if k <= 0.01:
        return
    r0, r1 = TEXT_ROW - 1, TEXT_ROW + 1
    c0 = TEXT_COL - 3
    c1 = TEXT_COL + len(LINE) + 3
    bgc = np.asarray(P.mix(VOID, P.mix(VOID, PANEL, 0.85), k), np.float32)
    fr.bg[r0:r1 + 1, c0:c1 + 1] = np.clip(bgc, 0, 255).astype(np.uint8)
    hair = np.asarray(P.mix(VOID, LINE_C, 0.42 * k), np.float32).astype(np.uint8)
    fr.ch[r0, c0:c1 + 1] = _HAIR
    fr.fg[r0, c0:c1 + 1] = hair
    fr.ch[r1, c0:c1 + 1] = _HAIR
    fr.fg[r1, c0:c1 + 1] = hair
    for rr in (r0, r1):
        fr.ch[rr, c0] = _SPACE
        fr.ch[rr, c1] = _SPACE


def _carry_dot(fr, L):
    k = 1.0 - fx.smoothstep(L, 0.0, 0.45)
    if k <= 0.01:
        return
    fr.put(22, 96, "▌", fg=P.mix(VOID, WHITE, 0.55 * k))
    fr.put(22, 95, "▪", fg=P.mix(VOID, RED, 0.30 * k))
    fr.put(22, 97, "▪", fg=P.mix(VOID, RED, 0.30 * k))


def _sentence(fr, ctx, L):
    t = ctx.t
    n = _typed(t)
    done = n >= len(LINE)
    el = t - _DONE_T if done else -1.0
    base = P.mix(VOID, FG, 0.68)
    if done:
        settle = 1.0 - fx.smoothstep(el, 0.0, 0.75)
        if settle > 0.01:
            base = P.mix(base, WHITE, 0.55 * settle)
    if L > 3.75:
        k = fx.clamp(1.0 - fx.smoothstep(L, 3.75, 4.90) * 0.55)
        base = P.mix(VOID, base, k)
    if n:
        fr.write(TEXT_ROW, TEXT_COL, LINE[:n], fg=base)
        if not done:
            fr.put(TEXT_ROW, TEXT_COL + n - 1, LINE[n - 1],
                   fg=P.mix(WHITE, TEAL, 0.25))
        elif 0.0 <= el < 0.80:
            sc = TEXT_COL + min(len(LINE) - 1, int(el / 0.80 * len(LINE)))
            fr.put(TEXT_ROW, sc, LINE[sc - TEXT_COL],
                   fg=P.mix(base, WHITE, 0.85 * (1.0 - el / 0.80)))
    ccol = TEXT_COL + n
    if not done:
        if n == 0:
            on = math.sin(t * 5.2) > 0.0
            fr.put(TEXT_ROW, ccol, "▌",
                   fg=P.mix(WHITE, VOID, 0.10) if on else P.mix(VOID, WHITE, 0.16))
        else:
            fr.put(TEXT_ROW, ccol, "▌", fg=WHITE)
    else:
        if el < 0.95:
            ph = (el * 2.1) % 1.0
            lit = ph < 0.62
            fr.put(TEXT_ROW, ccol + 1, "▌" if lit else " ",
                   fg=P.mix(WHITE, VOID, 0.15) if lit else P.mix(VOID, WHITE, 0.3))
        else:
            _loop_icon(fr, TEXT_ROW, ccol + 2, t, el - 0.95)
    if n:
        fr.write(TEXT_ROW + 1, TEXT_COL + 1, LINE[:n],
                 fg=P.mix(VOID, P.mix(FG, VOID, 0.65), 0.40))


def _loop_icon(fr, r, c, t, e):
    frames = ("⟳", "↻", "↺", "↻")
    ch = frames[int(t * 6.0) % len(frames)]
    k = fx.clamp(1.0 - e / 1.6)
    fr.put(r, c, ch, fg=P.mix(VOID, TEAL, 0.35 + 0.50 * k))
    if math.sin(t * 3.4) > 0.55:
        fr.put(r, c + 1, "·", fg=P.mix(VOID, TEAL, 0.30))


def _fade(fr, meta, L):
    _end = T1 - T0
    k = 1.0 - fx.smoothstep(L, _end - 0.85, _end - 0.22)
    if k < 0.999:
        fr.fg[:, :] = (fr.fg.astype(np.float32) * k).astype(np.uint8)
        fr.bg[:, :] = (fr.bg.astype(np.float32) * k).astype(np.uint8)
    meta["grain"] = 0.25 + 0.75 * k
    meta["vignette"] = 1.0 + 0.5 * (1.0 - k)
    meta["bloom"] = 0.12
    meta["glitch"] = 0.0
