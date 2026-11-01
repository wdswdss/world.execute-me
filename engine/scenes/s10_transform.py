"""s10_transform - four 2-bar transformation segments, dense full-screen motion.

88.810  Switch my gender to F to M
92.502  and then do whatever from AM to PM
96.194  Oh, switch my role to S to M
99.887  So we can enter the trance, the trance

Hero devices: a real glyph-mask morph (F->M, S->M), a sunrise->night sky with a
clock, swapping role badges with chains, and a hypnotic spiral tunnel.  Beat
synced: flash/glitch/shake on downbeats, big keywords paint on the beat.
"""
from __future__ import annotations

import math

import numpy as np

from .. import art
from .. import font as F
from .. import fx
from .. import layout as L
from .. import palette as P
from .. import widgets as W

PANEL = P.C["panel"]
PANEL2 = P.C["panel2"]
VOID = P.C["void"]
VOID2 = P.C["void2"]
LINE = P.C["line"]
WHITE = P.C["white"]
DIM = P.C["dim"]

SEG_T0 = (88.810, 92.502, 96.194, 99.887)
SEG_T1 = (92.502, 96.194, 99.887, 103.580)

SEGS = (
    {
        "key": "GENDER", "index": "01", "id": "0x6E01", "accent": "primary",
        "hot": "magenta", "word": "F → M", "sub": "SWITCH MY GENDER  //  F TO M",
        "log": ("> registry.patch gender", "> old: F   new: M",
                "> pronoun.delta: -1", "> form.sync: OK"),
    },
    {
        "key": "CLOCK", "index": "02", "id": "0x6E02", "accent": "gold",
        "hot": "orange", "word": "AM → PM", "sub": "DAY CYCLE REWRITE  //  AM TO PM",
        "log": ("> clock.mode: FWD", "> sky.gradient: TURNING",
                "> sun: SETTING", "> moon: RISING"),
    },
    {
        "key": "ROLE", "index": "03", "id": "0x6E03", "accent": "red",
        "hot": "violet", "word": "S → M", "sub": "ROLE SWAP  //  SUBJECT TO MASTER",
        "log": ("> role.s: SUBJECT", "> role.m: MASTER",
                "> permissions: FLIPPED", "> chain: RELEASED"),
    },
    {
        "key": "TRANCE", "index": "04", "id": "0x6E04", "accent": "violet",
        "hot": "magenta", "word": "TRANCE", "sub": "ENTER THE TRANCE  //  10 9 8 7",
        "log": ("> induction: START", "> focus: 10 Hz", "> ego: DISSOLVING",
                "> trance.depth: DEEP"),
    },
)


# ------------------------------------------------------------------ helpers --
def _mk(text, h):
    """Cached glyph mask at a fixed cell height -> float32 array."""
    key = (text, h)
    m = _MK.get(key)
    if m is None:
        tm = F.text_mask(text, int(h * L.CELL_H), bold=True)
        m = tm
        if len(_MK) > 40:
            _MK.clear()
        _MK[key] = m
    return m


_MK = {}


_GM = {}


def _glyph_pairs(a, b, w, h, n=430):
    """Cell pairs: source cells of glyph *a* -> target cells of glyph *b*."""
    key = (a, b, w, h)
    got = _GM.get(key)
    if got is not None:
        return got
    ma = F.resize_mask(F.text_mask(a, int(h * L.CELL_H), bold=True), w * L.CELL_W, h * L.CELL_H)
    mb = F.resize_mask(F.text_mask(b, int(h * L.CELL_H), bold=True), w * L.CELL_W, h * L.CELL_H)
    ca = ma.reshape(h, L.CELL_H, w, L.CELL_W).mean(axis=(1, 3))
    cb = mb.reshape(h, L.CELL_H, w, L.CELL_W).mean(axis=(1, 3))
    pa = [(r, c) for r in range(h) for c in range(w) if ca[r, c] > 0.20]
    pb = [(r, c) for r in range(h) for c in range(w) if cb[r, c] > 0.20]
    def thin(pl):
        if len(pl) <= n:
            return pl
        idx = np.linspace(0, len(pl) - 1, n).astype(np.int32)
        return [pl[i] for i in idx]
    pa, pb = thin(pa), thin(pb)
    m = min(len(pa), len(pb))
    got = list(zip(pa[:m], pb[:m]))
    _GM[key] = got
    return got


_GM_GLYPHS = "F M # ▒ ░ 1 0 = + * ▓".split()


def _glyph_morph(fr, p, t, c0, r0, w, h, fg_from, fg_to, n=430):
    """The letter F made of code glyphs that sweep into M (each glyph flips F->M)."""
    pairs = _glyph_pairs("F", "M", w, h, n)
    for i, (src, dst) in enumerate(pairs):
        # dissolve left-to-right so the letterform stays readable while it morphs
        d = (src[1] / float(max(1, w - 1))) * 0.42 + ((i * 0.6180339887) % 1.0) * 0.10
        q = fx.clamp((p - d) / max(1e-3, 1.0 - d * 0.5))
        q = fx.ease_inout(q)
        rr = r0 + src[0] + (dst[0] - src[0]) * q
        cc = c0 + src[1] + (dst[1] - src[1]) * q
        rr += math.sin(q * math.pi) * (((i % 5) - 2) * 0.22)
        if q < 0.5:
            ch = "F"
            col = P.mix(fg_from, WHITE, 0.10 + 0.25 * q)
        else:
            ch = "M"
            col = P.mix(fg_to, WHITE, 0.18 + 0.22 * (1.0 - q))
        fr.put(int(round(rr)), int(round(cc)), ch, fg=col)


def _fm_bar(fr, r, c, w, p, t):
    """Progress bar whose cells literally turn from F into M."""
    fr.write(r - 1, c - 8, "F", fg=P.C["primary"])
    fr.write(r - 1, c + w + 6, "M", fg=P.C["magenta"])
    fr.write(r - 1, c + w // 2 - 11, "GENDER.SWITCH PROGRESS", fg=P.mix(P.C["primary"], VOID, 0.45))
    head = int(w * fx.clamp(p))
    for i in range(w):
        if i < head:
            fr.put(r, c + i, "M", fg=P.mix(P.C["magenta"], WHITE, 0.20 + 0.25 * (i / max(1, w))))
        else:
            fr.put(r, c + i, "F", fg=P.mix(P.C["primary"], VOID, 0.62))
    for i in range(w):
        fr.put(r + 1, c + i, "▔" if i < head else "▁",
               fg=P.mix(P.C["magenta"] if i < head else P.C["primary"], VOID, 0.55))
    if head < w:
        fr.put(r, c + head, "▏", fg=P.C["white"])
    fr.write(r + 1, c + w // 2 - 7, f"{int(p * 100):3d}%  F→M", fg=P.mix(P.C["magenta"], WHITE, 0.35))
    if p >= 0.999:
        fr.write(r + 1, c + w // 2 - 7, "M  100%  LOCKED", fg=P.C["white"])


def _morph(a, b, w, h, p):
    """Blend two glyph masks so the letterform itself turns into the other."""
    ma = _mk(a, h)
    mb = _mk(b, h)
    A = F.resize_mask(ma, w * L.CELL_W, h * L.CELL_H)
    B = F.resize_mask(mb, w * L.CELL_W, h * L.CELL_H)
    return A * (1.0 - p) + B * p, np.abs(A - B)


def _text(fr, text, r0, c0, h, fg, fg2=WHITE, bg=None, gain=2.6,
          align="center", ramp=None, max_cols=None, thin=0, hard=None):
    """Crisp big text: text_mask -> paint_mask with gain (paint_text is too soft)."""
    tm = F.text_mask(text, int(h * L.CELL_H), bold=False)
    if thin:
        tm = F.erode_mask(tm, int(thin))
    w = max(1, int(round(tm.shape[1] / L.CELL_W)))
    if max_cols and w > max_cols:
        h = max(1, int(round(h * max_cols / w)))
        tm = F.text_mask(text, int(h * L.CELL_H), bold=True)
        w = max(1, int(round(tm.shape[1] / L.CELL_W)))
    if align == "center":
        c0 = int(round(c0 - w / 2))
    fr.paint_mask(tm, c0, r0, w, h, ramp=ramp or P.RAMP_BLOCK,
                  fg=fg, fg2=fg2, bg=bg, gain=gain, hard=hard)
    return w


def _box(fr, r0, c0, r1, c1, title, accent, bg=PANEL2):
    fr.fill_rect(r0, c0, r1, c1, " ", bg=bg)
    fr.box(r0, c0, r1, c1, 1, fg=P.mix(accent, VOID, 0.5), bg=bg)
    if title:
        fr.write(r0, c0 + 2, f"┤ {title} ├", fg=accent, bg=bg)


def _bar(fr, r, c, w, frac, color, bg=PANEL2):
    W.progress_bar(fr, r, c, w, frac, fg=color, bg=bg, show_pct=False)


def _stat(fr, r0, c0, c1, specs, bg=PANEL2):
    for i, (label, frac, val, colname) in enumerate(specs):
        r = r0 + i * 2
        col = P.C[colname]
        fr.write(r, c0, label, fg=DIM, bg=bg)
        _bar(fr, r, c0 + 7, 18, frac, col, bg=bg)
        fr.write(r, c1 - 7, val, fg=col, bg=bg)


def _sweep(fr, t, color, r0=2, r1=35, speed=15.0):
    y = r0 + int((t * speed) % max(1, r1 - r0))
    for c in range(0, fr.cols, 2):
        if fr.get(y, c) in (" ", "·", "─"):
            fr.put(y, c, "─", fg=P.mix(color, VOID, 0.55))


def _moteflow(fr, t, n, seed, src, dst, color, spread=6):
    for k in range(n):
        p = ((t * (0.7 + fx.hash01(k, seed) * 0.9) + fx.hash01(k, seed, 1)) % 1.0)
        e = fx.ease_in(p)
        x = int(fx.lerp(src[0] + (fx.hash01(k, seed, 2) - 0.5) * spread * 2,
                        dst[0] + (fx.hash01(k, seed, 3) - 0.5) * spread * 2, e))
        y = int(fx.lerp(src[1] + (fx.hash01(k, seed, 4) - 0.5) * spread,
                        dst[1] + (fx.hash01(k, seed, 5) - 0.5) * spread, e))
        if fr.inb(y, x):
            ch = "●" if p > 0.8 else ("*" if p > 0.5 else "·")
            fr.put(y, x, ch, fg=P.mix(color, WHITE, 0.5 * (1 - p)))


# ------------------------------------------------------------------ chrome --
def _top(fr, ctx, si, lt, seg):
    t = ctx.t
    accent = P.C[seg["accent"]]
    fr.fill_rect(0, 0, 0, fr.cols - 1, " ", bg=VOID2)
    fr.write(0, 2, "TRANSFORM.DAEMON", fg=P.C["primary"], bg=VOID2)
    fr.write(0, 19, "v2.0", fg=DIM, bg=VOID2)
    for i, s in enumerate(SEGS):
        c = 28 + i * 24
        active = i == si
        fg = P.C["gold"] if active else DIM
        fr.write(0, c - 2, "▶" if active else " ", fg=fg, bg=VOID2)
        fr.write(0, c, s["index"] + " " + s["key"], fg=fg, bg=VOID2)
    fr.write(0, 148, f"LINE {(ctx.line_i if ctx.line_i is not None else 0):02d}/24", fg=DIM, bg=VOID2)
    if int(t * 2) % 2 == 0:
        fr.write(0, 174, "REC", fg=P.C["red"], bg=VOID2)
    fr.put(0, 178, "●", fg=P.C["red"], bg=VOID2)
    # rule + segment progress
    fr.hline(1, 0, 124, "─", fg=P.mix(LINE, VOID, 0.25))
    for c in range(4, 125, 12):
        fr.put(1, c, "┬", fg=P.mix(accent, VOID, 0.55))
    fr.write(1, 130, "SEG", fg=DIM, bg=VOID2)
    _bar(fr, 1, 134, 52, fx.clamp(lt / 3.692), accent, bg=VOID2)
    # program line
    fr.fill_rect(2, 0, 2, fr.cols - 1, " ", bg=VOID)
    pre = "> mutate("
    fr.write(2, 2, pre, fg=DIM)
    fr.write(2, 2 + len(pre), seg["key"], fg=accent)
    fr.write(2, 2 + len(pre) + len(seg["key"]), ")", fg=DIM)
    fr.write(2, 30, ":: " + seg["sub"], fg=P.mix(accent, P.C["fg"], 0.45))
    W.typing(fr, 2, 126, "IDENTITY IS A CONFIG FILE", lt, start=0.5, cps=48,
             fg=P.mix(accent, DIM, 0.5))
    for c in range(0, fr.cols, 8):
        if fr.get(3, c) == " ":
            fr.put(3, c, "·", fg=P.mix(LINE, VOID, 0.5))
    fr.put(3, 0, "┌", fg=P.mix(LINE, VOID, 0.3))
    fr.put(3, fr.cols - 1, "┐", fg=P.mix(LINE, VOID, 0.3))


def _bottom(fr, ctx, si, lt, seg):
    t = ctx.t
    accent = P.C[seg["accent"]]
    pop = fx.ease_out_back(fx.clamp(lt / 0.34))
    h = int(round(5 + 2 * fx.clamp(pop)))
    r0 = 41 - h
    _text(fr, seg["word"], r0, 96, h, fg=P.mix(accent, VOID, 0.15),
          fg2=WHITE, bg=VOID, gain=2.4, max_cols=150)
    fr.hline(43, 1, fr.cols - 2, "═", fg=P.mix(accent, VOID, 0.28))
    fr.put(43, 0, "╠", fg=P.mix(accent, VOID, 0.5))
    fr.put(43, fr.cols - 1, "╣", fg=P.mix(accent, VOID, 0.5))
    cap = f">> {seg['word']}  ::  {seg['sub']}"
    fr.write(42, max(2, 96 - len(cap) // 2), cap, fg=P.mix(accent, P.C["fg"], 0.5))
    fr.fill_rect(44, 0, 44, fr.cols - 1, " ", bg=VOID2)
    W.marquee(fr, 44, "   " + seg["sub"] + "   ", t, speed=26.0,
              fg=P.mix(accent, VOID, 0.4), bg=VOID2, gap=8)
    fr.fill_rect(44, 0, 44, 28, " ", bg=VOID2)
    fr.write(44, 1, f"ID {seg['id']}", fg=accent, bg=VOID2)
    fr.write(44, 12, f"SEG {seg['index']}/04", fg=DIM, bg=VOID2)
    fr.write(44, 24, f"t+{lt:05.2f}", fg=DIM, bg=VOID2)
    fr.fill_rect(44, 148, 44, fr.cols - 1, " ", bg=VOID2)
    fr.write(44, 150, f"FRAME {ctx.fi:05d}", fg=DIM, bg=VOID2)
    W.dots_progress(fr, 44, 166, 6, int(t * 3) % 6, fg=accent)
    fr.write(44, 180, "LOOP ∞", fg=DIM, bg=VOID2)


def _bg(fr, ctx, si, seg):
    t = ctx.t
    accent = P.C[seg["accent"]]
    for r in range(4, fr.rows - 2, 3):
        for c in range(0, fr.cols, 5):
            if fr.get(r, c) == " " and fx.hash01(r, c, si) > 0.4:
                fr.put(r, c, "·", fg=P.mix(VOID, LINE, 0.35 + 0.2 * fx.hash01(c, r)))
    _sweep(fr, t, accent)
    # edge code columns
    W.data_column(fr, 4, 1, 28, t, seed=si * 7 + 1, speed=7.0,
                  fg=P.mix(accent, VOID, 0.72))
    W.data_column(fr, 4, 190, 28, t, seed=si * 7 + 2, speed=8.0,
                  fg=P.mix(accent, VOID, 0.72))
    for (r, c, ch) in ((3, 0, "╔"), (3, fr.cols - 1, "╗"),
                       (35, 0, "╚"), (35, fr.cols - 1, "╝")):
        fr.put(r, c, ch, fg=P.mix(accent, VOID, 0.4))
    fr.hline(35, 0, fr.cols - 1, "─", fg=P.mix(LINE, VOID, 0.3))
    for c in range(0, fr.cols, 6):
        fr.put(35, c, "┴", fg=P.mix(accent, VOID, 0.45))


def _boundary(fr, ctx, si, lt):
    dur = SEG_T1[si] - SEG_T0[si]
    accent = P.C[SEGS[si]["accent"]]
    if lt < 0.26:
        p = lt / 0.26
        mode = si % 3
        if mode == 0:      # horizontal bars wipe
            for r in range(fr.rows):
                a = fx.clamp(1.0 - p * 1.4 - abs(r - 18) * 0.02)
                if a > 0.1:
                    for c in range(0, fr.cols, 2):
                        fr.put(r, c, "▔" if r % 2 else "═",
                               fg=P.mix(accent, WHITE, a * 0.8))
        elif mode == 1:    # vertical scan bands
            band = int(p * (fr.cols + 30)) - 15
            for c in range(max(0, band), min(fr.cols, band + 3)):
                for r in range(fr.rows):
                    fr.put(r, c, "█", fg=P.mix(accent, WHITE, 0.5 * (1 - p)))
        else:              # pop rings
            for k in range(80):
                a = k / 80 * 2 * math.pi
                rr = 2 + p * 26
                x = int(96 + math.cos(a) * rr * 1.7)
                y = int(18 + math.sin(a) * rr * 0.8)
                if fr.inb(y, x):
                    fr.put(y, x, "*", fg=P.mix(accent, WHITE, 0.7 * (1 - p)))
        ctx.set_glitch(0.55 * (1.0 - p))
        ctx.meta["flash"] = 0.26 * (1.0 - p)
        ctx.meta["flash_color"] = accent
        ctx.shake(4)
    elif lt > dur - 0.18:
        p = (lt - (dur - 0.18)) / 0.18
        ctx.set_glitch(0.28 + 0.5 * p)
        ctx.meta["flash"] = 0.2 * p
        ctx.meta["flash_color"] = accent


# --------------------------------------------------------- seg 1  gender F->M --
def _seg_gender(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["primary"]
    hot = P.C["magenta"]
    pulse = ctx.pulse
    p = fx.smoothstep(lt, 0.30, 2.55)
    p = fx.ease_inout(p)

    # hero: the letterform literally morphs, plus an energy rim on the diff
    blend, diff = _morph("F", "M", 30, 16, p)
    c0 = 96 - 15
    fr.paint_mask(blend, c0, 6, 30, 16, ramp=P.RAMP_BLOCK,
                  fg=P.mix(accent, VOID, 0.72), fg2=P.mix(WHITE, VOID, 0.6),
                  gain=1.4, alpha=0.20, min_v=0.12)
    _glyph_morph(fr, p, t, c0, 6, 30, 16,
                 P.mix(accent, WHITE, 0.15), P.mix(hot, WHITE, 0.35))
    # glyph id tag + morph progress
    fr.write(4, 84, "GLYPH MORPH", fg=P.mix(accent, VOID, 0.2))
    fr.write(4, 112, f"{(1 - p):.2f}F", fg=accent)
    fr.write(4, 120, f"{p:.2f}M", fg=hot)
    _moteflow(fr, t, 26, 11, (78, 14), (114, 14), hot, spread=8)
    # energy arcs around the glyph
    for k in range(48):
        a = k / 48 * 2 * math.pi + t * 0.8
        rr = 17 + 2.5 * math.sin(t * 3 + k * 0.6)
        x = int(96 + math.cos(a) * rr * 0.95)
        y = int(14 + math.sin(a) * rr * 0.55)
        if fr.inb(y, x):
            fr.put(y, x, "·" if k % 3 else "✦",
                   fg=P.mix(accent, WHITE, 0.2 + 0.3 * pulse))

    # left panel: identity form
    _box(fr, 5, 2, 27, 44, "IDENTITY FORM", accent)
    fr.write(7, 5, "handle  : user_7f3a", fg=DIM, bg=PANEL2)
    fr.write(8, 5, "pronoun : " + ("she/they" if p < 0.5 else "he/they"),
             fg=P.mix(accent, WHITE, 0.3), bg=PANEL2)
    fr.write(10, 5, "GENDER FIELD", fg=DIM, bg=PANEL2)
    fr.write(11, 5, "[ F ]", fg=accent if p < 0.5 else P.mix(accent, VOID, 0.6),
             bg=PANEL2)
    fr.write(11, 33, "[ M ]", fg=hot if p >= 0.5 else P.mix(hot, VOID, 0.6),
             bg=PANEL2)
    W.progress_bar(fr, 12, 5, 34, p, fg=hot, bg=PANEL2, show_pct=False)
    fr.put(12, 5 + int(34 * p), "▲", fg=WHITE, bg=PANEL2)
    _stat(fr, 15, 5, 43, (
        ("FEM   ", fx.clamp(1.0 - p), f"{int((1 - p) * 100):3d}%", "primary"),
        ("MASC  ", fx.clamp(p), f"{int(p * 100):3d}%", "magenta"),
        ("BIND  ", fx.clamp(0.4 + 0.6 * pulse), "SYNC", "gold"),
        ("VOICE ", fx.clamp(0.3 + 0.7 * p), "SHIFT", "green"),
        ("SOUL  ", 1.0, "SAME", "white"),
    ))
    fr.write(25, 5, "FORM HASH", fg=DIM, bg=PANEL2)
    W.hex_dump(fr, 26, 16, 1, 24, t, seed=4, fg=P.mix(accent, VOID, 0.35))

    # right panel: registry log + slider readout
    _box(fr, 5, 148, 27, 190, "REGISTRY", hot)
    for i, ln in enumerate(SEGS[0]["log"]):
        W.typing(fr, 7 + i * 2, 151, ln, lt, start=0.25 + i * 0.5, cps=58,
                 fg=P.mix(hot, WHITE, 0.25), cursor=(i == 3))
    fr.write(16, 151, "gender.value", fg=DIM, bg=PANEL2)
    fr.write(16, 168, f"{p:5.3f}", fg=hot, bg=PANEL2)
    fr.write(18, 151, "slider", fg=DIM, bg=PANEL2)
    _bar(fr, 19, 151, 30, p, hot, bg=PANEL2)
    fr.write(21, 151, "LOCK", fg=DIM, bg=PANEL2)
    fr.write(21, 158, "F" if p < 0.5 else "M", fg=WHITE, bg=PANEL2)
    fr.write(22, 151, "REBOOT REQUIRED", fg=P.mix(P.C["red"], VOID, 0.2), bg=PANEL2)
    fr.write(24, 151, "delta", fg=DIM, bg=PANEL2)
    fr.write(24, 166, f"{int(p * 472):3d} ms", fg=accent, bg=PANEL2)

    # F -> M letter progress bar (cells themselves turn into M)
    _fm_bar(fr, 28, 40, 113, p, t)
    # candidate form row: three little ids flipping on a scan
    fr.write(23, 60, "FORM CANDIDATES", fg=DIM)
    for k, (lab, ok) in enumerate((("F", p < 0.5), ("M", p >= 0.5), ("X", False))):
        c0 = 78 + k * 14
        col = (accent if k == 0 else hot) if ok else P.mix(LINE, VOID, 0.4)
        fr.write(24, c0, "┌───┐", fg=col)
        fr.write(25, c0, "│ " + lab + " │", fg=col)
        fr.write(26, c0, "└───┘", fg=col)
        if ok:
            fr.put(23, c0 + 2, "▶", fg=col)
    # integrity + log ticker
    fr.write(31, 62, "MORPH INTEGRITY", fg=DIM)
    _bar(fr, 31, 78, 18, 0.35 + 0.6 * pulse, accent)
    fr.write(31, 100, f"{int((0.35 + 0.6 * pulse) * 100):3d}%", fg=accent)
    fr.write(32, 62, "> patch.applied   host=body   form=M", fg=P.mix(accent, VOID, 0.15))
    fr.write(33, 62, "> checksum ", fg=DIM)
    W.hex_dump(fr, 33, 74, 1, 18, t, seed=9, fg=P.mix(accent, VOID, 0.35))


# ------------------------------------------------------------ seg 2  AM->PM --
def _sky(dayp, u):
    """Sky colour for height u in [0,1] (0 = zenith) at day progress dayp."""
    top = P.mix(P.dark("blue", 0.55), P.dark("violet", 0.7), dayp)
    mid = P.mix(P.dark("primary", 0.5), P.dark("magenta", 0.55), dayp)
    hor = P.mix(P.C["gold"], P.C["orange"], 0.4)
    hor = P.mix(hor, P.dark("crimson", 0.35), dayp)
    col = P.mix(top, mid, fx.clamp(u * 1.6))
    return P.mix(col, hor, fx.clamp((u - 0.55) / 0.45) * 0.85)


def _seg_clock(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["gold"]
    hot = P.C["orange"]
    pulse = ctx.pulse
    dayp = fx.smoothstep(lt, 0.25, 3.35)

    # ---- sky: a real dawn -> night ramp (rows 4..20) ----
    day_top = P.mix(P.C["blue"], VOID, 0.30)
    day_mid = P.mix(P.C["primary"], VOID, 0.20)
    day_hor = P.mix(P.C["gold"], P.C["orange"], 0.40)
    ngt_top = P.mix(P.C["violet"], VOID, 0.55)
    ngt_mid = P.mix(P.C["magenta"], VOID, 0.45)
    ngt_hor = P.mix(P.C["crimson"], VOID, 0.25)
    top = P.mix(day_top, ngt_top, dayp)
    mid = P.mix(day_mid, ngt_mid, dayp)
    hor = P.mix(day_hor, ngt_hor, dayp)
    for r in range(4, 21):
        u = (r - 4) / 16.0
        col = P.mix(top, mid, fx.clamp(u * 1.9))
        col = P.mix(col, hor, fx.clamp((u - 0.45) / 0.55) * 0.95)
        fr.fill_rect(r, 0, r, fr.cols - 1, " ", bg=col)
    # stars
    ns = int(80 * dayp)
    for k in range(ns):
        x = int(fx.hash01(k, 1) * fr.cols)
        y = 4 + int(fx.hash01(k, 2) * 12)
        if fr.inb(y, x):
            tw = 0.5 + 0.5 * math.sin(t * 4 + k)
            fr.put(y, x, "✦" if k % 7 == 0 else "·",
                   fg=P.mix(WHITE, P.dark("violet", 0.3), 1.0 - 0.55 * tw))
    # clouds / gradient bands
    for k in range(7):
        y = 6 + int(fx.hash01(k, 5) * 9)
        x0 = int((t * (2.2 + k) + k * 29) % 210) - 10
        wl = 12 + int(fx.hash01(k, 6) * 18)
        for c in range(max(0, x0), min(fr.cols, x0 + wl)):
            if fr.get(y, c) in (" ", "·", "✦"):
                fr.put(y, c, "▔", fg=P.mix(hor, WHITE, 0.25 + 0.2 * (c % 3 == 0)))
    # sun -> moon along an arc
    sx = int(fx.lerp(40, 152, dayp))
    sy = int(17 - 12 * math.sin(math.pi * (0.06 + dayp * 0.88)))
    circ = art.get("circle", w=160, h=110)
    sm = F.resize_mask(circ, 20, 11)
    if dayp < 0.62:
        for k in range(16):
            a = k / 16 * 2 * math.pi + t * 0.45
            for d in (6, 8, 10):
                x = int(sx + math.cos(a) * d * 1.45)
                y = int(sy + math.sin(a) * d * 0.9)
                if fr.inb(y, x):
                    fr.put(y, x, "─" if abs(math.cos(a)) > 0.6 else "·",
                           fg=P.mix(accent, WHITE, 0.2 + 0.15 * d))
        for k in range(26):
            a = k / 26 * 2 * math.pi
            x = int(sx + math.cos(a) * 7)
            y = int(sy + math.sin(a) * 3.6)
            if fr.inb(y, x):
                fr.put(y, x, "·", fg=P.mix(accent, WHITE, 0.55))
        fr.paint_mask(F.resize_mask(circ, 11, 6), sx - 5, sy - 3, 11, 6,
                      ramp=P.RAMP_BLOCK, fg=P.dark("gold", 0.35),
                      fg2=P.mix(P.C["gold"], WHITE, 0.55), gain=1.15)
    else:
        m = min(1.0, (dayp - 0.62) / 0.28)
        sm2 = F.resize_mask(circ, 16, 10)
        fr.paint_mask(sm2, sx - 8, sy - 5, 16, 10, ramp=P.RAMP_HI,
                      fg=P.C["white"], fg2=P.C["fg"], gain=2.4)
        sk = P.mix(mid, hor, fx.clamp((sy - 4) / 16.0))
        fr.paint_mask(sm2, sx - 8 + int(4 + 3 * m), sy - 6, 16, 10,
                      ramp=P.RAMP_HI, fg=sk, fg2=sk, gain=2.6, min_v=0.06)
        for k in range(10):
            x = int(sx + 14 + 8 * fx.hash01(k, 9))
            y = int(sy - 6 + 12 * fx.hash01(k, 10))
            if fr.inb(y, x):
                fr.put(y, x, "✦", fg=P.mix(WHITE, P.C["primary"], 0.5))

    # ---- horizon: hills + city, then water reflection ----
    fr.hline(20, 0, fr.cols - 1, "▀", fg=P.mix(hor, WHITE, 0.30))
    for k in range(64):
        x = k * 3 + int(fx.hash01(k, 3) * 2)
        hh = 1 + int(fx.hash01(k, 4) * 3)
        for d in range(hh):
            r = 19 - d
            if fr.inb(r, x):
                for c in range(x, min(fr.cols, x + 2)):
                    fr.put(r, c, "▓" if d == 0 else "▒",
                           fg=P.mix(VOID2, P.mix(hor, VOID, 0.5), 0.35 + 0.12 * d))
    for r in range(21, 25):
        u = (r - 21) / 3.0
        fr.fill_rect(r, 0, r, fr.cols - 1, " ", bg=P.mix(P.dark("blue", 0.6), VOID, 0.25))
        for c in range(0, fr.cols, 2):
            w = math.sin(c * 0.31 + t * (2.6 + u) + u * 3)
            if w > 0.2:
                fr.put(r, c, "≈", fg=P.mix(hor, VOID, 0.30 + 0.35 * u))
        for c in range(0, fr.cols, 6):
            if abs(c - sx) < 12 + r:
                fr.put(r, c, "▔", fg=P.mix(accent, VOID, 0.25 + 0.3 * u))

    # ---- clock face (centre-left of sky) ----
    cx, cy, rx, ry = 96, 13, 14, 7
    for k in range(180):
        a = k / 180 * 2 * math.pi
        x = int(cx + math.cos(a) * rx)
        y = int(cy + math.sin(a) * ry)
        if not fr.inb(y, x):
            continue
        if abs(math.cos(a)) > 0.70:
            ch = "│"
        elif abs(math.sin(a)) > 0.70:
            ch = "─"
        elif math.sin(a) * math.cos(a) > 0:
            ch = "╲"
        else:
            ch = "╱"
        fr.put(y, x, ch, fg=P.mix(accent, WHITE, 0.45))
    for k in range(120):
        a = k / 120 * 2 * math.pi
        x = int(cx + math.cos(a) * (rx - 2.5))
        y = int(cy + math.sin(a) * (ry - 1.5))
        if fr.inb(y, x) and fr.get(y, x) == " ":
            fr.put(y, x, "·", fg=P.mix(accent, VOID, 0.3))
    for k in range(12):
        a = k / 12 * 2 * math.pi - math.pi / 2
        if k % 3 == 0:
            for d in range(-1, 2):
                x = int(cx + math.cos(a) * (rx - 2 - abs(d)) + math.cos(a + 1.57) * d)
                y = int(cy + math.sin(a) * (ry - 1 - abs(d)) + math.sin(a + 1.57) * d * 0.5)
                if fr.inb(y, x):
                    fr.put(y, x, "█", fg=P.mix(accent, WHITE, 0.5))
        else:
            x = int(cx + math.cos(a) * (rx - 1))
            y = int(cy + math.sin(a) * (ry - 0.6))
            if fr.inb(y, x):
                fr.put(y, x, "▪", fg=P.mix(accent, WHITE, 0.15))
    for (lab, ox, oy) in (("12", 0, -6), ("3", 11, 0), ("6", 0, 5), ("9", -12, 0)):
        fr.write(cy + oy, cx + ox - 1, lab, fg=P.mix(accent, WHITE, 0.55))
    frac = (lt / dur)
    hh_ang = frac * math.pi * 2.0 - math.pi / 2
    mm_ang = frac * math.pi * 2.0 * 12 - math.pi / 2
    ss_ang = frac * math.pi * 2.0 * 60 - math.pi / 2
    for ang, ln, col, thick in ((hh_ang, 6, WHITE, 2), (mm_ang, 11, accent, 2)):
        for d in range(1, ln):
            x = int(cx + math.cos(ang) * d)
            y = int(cy + math.sin(ang) * d * 0.55)
            for off in range(thick):
                if fr.inb(y, x + off):
                    fr.put(y, x + off, "█", fg=P.mix(col, WHITE, 0.25))
    for d in range(1, 13):
        x = int(cx + math.cos(ss_ang) * d)
        y = int(cy + math.sin(ss_ang) * d * 0.55)
        if fr.inb(y, x):
            fr.put(y, x, "┃", fg=P.mix(P.C["red"], WHITE, 0.35))
    for k in range(40):
        a = k / 40 * 2 * math.pi + t * 2
        x = int(cx + math.cos(a) * 3)
        y = int(cy + math.sin(a) * 2)
        if fr.inb(y, x):
            fr.put(y, x, "·", fg=P.mix(accent, WHITE, 0.5))
    fr.put(cy, cx, "◉", fg=WHITE)
    fr.write(cy - 8, cx - 6, "CLOCK.C", fg=P.mix(accent, WHITE, 0.3))

    # ---- AM / PM status plates (sky top corners) ----
    for side, (lab, val) in enumerate((("AM", 1.0 - dayp), ("PM", dayp))):
        c0 = 4 if side == 0 else 166
        on = (side == 0) == (dayp < 0.5)
        fill_c = P.mix(accent, WHITE, 0.25) if on else P.mix(accent, VOID, 0.5)
        fr.fill_rect(4, c0, 10, c0 + 22, " ", bg=VOID2)
        fr.box(4, c0, 10, c0 + 22, 1, fg=fill_c, bg=VOID2)
        _text(fr, lab, 5, c0 + 11, 5, fg=P.mix(fill_c, VOID, 0.25),
              fg2=fill_c, bg=VOID2, gain=2.8, max_cols=16)
        fr.write(11, c0, f"{lab} {val * 100:3.0f}%   ", fg=fill_c)
        _bar(fr, 12, c0, 22, val, fill_c)
    # racing timestamps in the sky gaps
    for c0 in (30, 148):
        for k in range(7):
            ph = (t * (6.0 + 0.35 * k) + k * 3.1) % 16
            r = 4 + int(ph)
            hh2 = (7 + int(ph * 1.1)) % 24
            mm2 = int((t * 40 + k * 13) % 60)
            ss2 = int((t * 260 + k * 7) % 60)
            if fr.inb(r, c0):
                fr.write(r, c0, f"{hh2:02d}:{mm2:02d}:{ss2:02d}",
                         fg=P.mix(hor, VOID, 0.25 + 0.45 * (ph / 16.0)))

    # ---- big time readout + AM->PM meter (rows 26..33) ----
    hh = (6 + dayp * 15.0) % 24
    mm = int((lt * 97 + 11) % 60)
    ss = int((lt * 1403 + 7) % 60)
    clock = f"{int(hh):02d}:{mm:02d}:{ss:02d}"
    fr.write(26, 60, "LOCAL TIME", fg=P.mix(accent, VOID, 0.25))
    _text(fr, clock, 27, 96, 4, fg=P.mix(accent, VOID, 0.15), fg2=WHITE,
          bg=VOID, gain=2.6, max_cols=44)
    fr.write(31, 62, "AM" if hh < 12 else "PM", fg=WHITE)
    fr.write(31, 66, "→", fg=P.mix(accent, VOID, 0.2))
    fr.write(31, 68, "PM", fg=P.mix(accent, VOID, 0.35))
    n = 56
    for k in range(n):
        c = 74 + k
        on = k / n <= dayp
        fr.put(31, c, "━" if on else "─",
               fg=P.mix(accent, WHITE, 0.55) if on else P.mix(LINE, VOID, 0.4))
    fr.put(30, 74 + int(n * dayp), "▲", fg=WHITE)
    fr.write(32, 74, f"CYCLE {dayp * 100:3.0f}%", fg=P.mix(accent, WHITE, 0.25))

    # ---- side program panels ----
    _box(fr, 25, 2, 33, 40, "CLOCK SUBSYSTEM", accent)
    fr.write(27, 5, f"hour   : {int(hh):02d}  (delta +1)", fg=DIM, bg=PANEL2)
    fr.write(28, 5, f"minute : {mm:02d}  (slew 0.7)", fg=DIM, bg=PANEL2)
    fr.write(29, 5, f"second : {ss:02d}  (drift 0ms)", fg=DIM, bg=PANEL2)
    fr.write(30, 5, "tz     : UTC+08", fg=DIM, bg=PANEL2)
    fr.write(31, 5, "ntp    : SYNCED", fg=P.mix(P.C["green"], WHITE, 0.2), bg=PANEL2)
    _bar(fr, 32, 5, 30, dayp, accent, bg=PANEL2)

    _box(fr, 25, 152, 33, 190, "SKY SIM", hot)
    fr.write(27, 155, f"sun.az : {40 + 112 * dayp:6.1f}", fg=DIM, bg=PANEL2)
    fr.write(28, 155, f"sun.el : {12 * math.sin(math.pi * dayp):5.1f}", fg=DIM, bg=PANEL2)
    fr.write(29, 155, f"moon   : {max(0.0, (dayp - 0.62) * 2.6):.2f}", fg=DIM, bg=PANEL2)
    fr.write(30, 155, "stars  : " + str(int(80 * dayp)), fg=DIM, bg=PANEL2)
    fr.write(31, 155, "gradient: " + ("NIGHT" if dayp > 0.6 else "DAY"),
             fg=P.mix(hot, WHITE, 0.25), bg=PANEL2)
    fr.write(32, 155, "next   : PM 23:59", fg=P.mix(hot, VOID, 0.1), bg=PANEL2)


# ------------------------------------------------------------- seg 3  S->M --
def _badge(fr, r0, c0, letter, label, color, bg=PANEL2, big=6):
    fr.fill_rect(r0, c0, r0 + 8, c0 + 20, " ", bg=bg)
    fr.box(r0, c0, r0 + 8, c0 + 20, 2, fg=P.mix(color, WHITE, 0.3), bg=bg)
    _text(fr, letter, r0 + 1, c0 + 10, big, fg=P.mix(color, VOID, 0.2),
          fg2=WHITE, bg=bg, gain=2.5, max_cols=16)
    fr.write(r0 + 8, c0 + 2, label, fg=P.mix(color, VOID, 0.15), bg=bg)


def _seg_role(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["red"]
    hot = P.C["violet"]
    pulse = ctx.pulse
    p = fx.ease_inout(fx.smoothstep(lt, 0.9, 2.5))
    xa = int(fx.lerp(46, 122, p))
    xb = int(fx.lerp(122, 46, p))

    # ghost trails of the swapping badges
    for k in (3, 2, 1):
        q = fx.clamp(p - k * 0.055)
        ga = int(fx.lerp(46, 122, q))
        gb = int(fx.lerp(122, 46, q))
        colg = P.mix(accent, VOID, 0.75)
        fr.write(8, ga + 8, "S", fg=colg)
        fr.write(8, gb + 8, "M", fg=P.mix(hot, VOID, 0.75))
    _badge(fr, 7, xa, "S", "SUBJECT", accent)
    _badge(fr, 7, xb, "M", "MASTER", hot)
    # big role letters behind
    fr.paint_text("S", 9, 96, 7, fg=P.mix(accent, VOID, 0.55), fg2=VOID,
                  align="center", alpha=0.5)
    fr.paint_text("M", 9, 96, 7, fg=P.mix(hot, VOID, 0.55), fg2=VOID,
                  align="center", alpha=0.5)

    # chain between the badges, breaking in the middle as they pass
    chain_r = 17
    gap = int(abs(p - 0.5) * 26)
    for c in range(xa + 21, max(xa + 22, xb - 1)):
        if abs(c - 96) < max(2, 3 - gap):
            continue
        ch = "═" if c % 4 else "╦"
        if abs(c - 96) < gap + 3 and p > 0.2 and p < 0.8:
            continue
        fr.put(chain_r, c, ch, fg=P.mix(accent, VOID, 0.35 + 0.2 * math.sin(c * 0.7 + t * 6)))
    for side in (-1, 1):
        cx2 = 96 + side * (gap + 3)
        if fr.inb(chain_r, cx2):
            fr.put(chain_r, cx2, "╳", fg=P.mix(accent, WHITE, 0.3))
    # cuffs + collar shapes
    fr.write(20, 74, "╭───╮   ╭───╮", fg=P.mix(accent, WHITE, 0.25))
    fr.write(21, 74, "│ ◯ │───│ ◯ │", fg=P.mix(accent, WHITE, 0.3))
    fr.write(22, 74, "╰───╯   ╰───╯", fg=P.mix(accent, WHITE, 0.25))
    for k in range(9):
        x = 66 + k * 7
        fr.put(24, x, "○" if k % 2 else "─", fg=P.mix(hot, VOID, 0.35))
        fr.put(25, x, "│" if k % 2 else " ", fg=P.mix(hot, VOID, 0.5))
    fr.write(24, 78, "RELEASED" if p > 0.5 else "BOUND", fg=P.mix(hot, WHITE, 0.3))

    # permissions panels
    _box(fr, 5, 2, 27, 44, "PERMISSIONS // S", accent)
    perms = (("filesystem", "read"), ("network", "off"), ("root", "DENIED"),
             ("memory", "r/o"), ("love", "granted"), ("agency", "BOUND"))
    for i, (name, val) in enumerate(perms):
        r = 7 + i * 2
        flipped = p > (0.12 + i * 0.12)
        good = flipped
        col = P.C["green"] if good else P.C["red"]
        txt = ("GRANTED" if good else "REVOKED")
        fr.write(r, 5, f"{name:<10}", fg=DIM, bg=PANEL2)
        _bar(fr, r, 16, 12, (0.9 if good else 0.25), col, bg=PANEL2)
        fr.write(r, 30, txt, fg=col if good else P.mix(col, VOID, 0.2), bg=PANEL2)
    fr.write(21, 5, "OWNER", fg=DIM, bg=PANEL2)
    fr.write(21, 12, "SELF" if p > 0.5 else "OTHER",
             fg=P.mix(hot, WHITE, 0.3), bg=PANEL2)
    W.hex_dump(fr, 23, 5, 2, 34, t, seed=6, fg=P.mix(accent, VOID, 0.4))

    _box(fr, 5, 148, 27, 190, "PERMISSIONS // M", hot)
    perms2 = (("filesystem", "root"), ("network", "on"), ("root", "GRANTED"),
              ("memory", "r/w"), ("love", "granted"), ("agency", "FREE"))
    for i, (name, val) in enumerate(perms2):
        r = 7 + i * 2
        got = p > (0.12 + i * 0.12)
        col = P.C["green"] if got else P.C["red"]
        txt = "GRANTED" if got else "REVOKED"
        fr.write(r, 151, f"{name:<10}", fg=DIM, bg=PANEL2)
        _bar(fr, r, 162, 12, (0.95 if got else 0.2), col, bg=PANEL2)
        fr.write(r, 176, txt, fg=col if got else P.mix(col, VOID, 0.2), bg=PANEL2)
    fr.write(21, 151, "CHAIN", fg=DIM, bg=PANEL2)
    fr.write(21, 158, "SNAPPED" if p > 0.5 else "---",
             fg=P.mix(hot, WHITE, 0.3), bg=PANEL2)
    for i, ln in enumerate(SEGS[2]["log"]):
        W.typing(fr, 23 + i, 151, ln, lt, start=0.3 + i * 0.55, cps=52,
                 fg=P.mix(hot, WHITE, 0.2), cursor=(i == 3))

    # swap meter
    fr.write(28, 66, "ROLE SWAP", fg=DIM)
    fr.hline(29, 66, 126, "═", fg=P.mix(accent, VOID, 0.4))
    fr.put(29, 66, "S", fg=accent)
    fr.put(29, 126, "M", fg=hot)
    fr.put(29, 66 + int(60 * p), "▲", fg=WHITE)
    fr.write(30, 86, f"{p * 100:3.0f}%  " + ("SUBJECT" if p < 0.5 else "MASTER"),
             fg=P.mix(hot, WHITE, 0.3))
    if pulse > 0.55:
        for k in range(12):
            a = k / 12 * 2 * math.pi + t
            x = int(96 + math.cos(a) * 30)
            y = int(17 + math.sin(a) * 5)
            if fr.inb(y, x):
                fr.put(y, x, "✦", fg=P.mix(accent, WHITE, 0.6))
    # swap telemetry strip
    fr.write(31, 54, "ROLE TABLE", fg=DIM)
    fr.write(31, 66, "S: SUBJECT  →  M: MASTER", fg=P.mix(accent, VOID, 0.1))
    fr.write(32, 54, "bound", fg=DIM)
    _bar(fr, 32, 60, 14, 1.0 - p, accent)
    fr.write(32, 76, "freed", fg=DIM)
    _bar(fr, 32, 83, 14, p, hot)
    fr.write(32, 100, f"keys.rotate {int(lt * 9) % 64:02d}", fg=P.mix(hot, VOID, 0.1))
    for k in range(3):
        W.typing(fr, 33, 54 + 0, ("", "", "")[0] + "> handover: subject=" + ("S" if p < 0.5 else "M") + " master=" + ("M" if p < 0.5 else "S"), lt, start=0.6, cps=30, fg=P.mix(accent, VOID, 0.2))
        break


# ------------------------------------------------------------- seg 4 trance --
def _seg_trance(fr, ctx, lt, dur, seg):
    t = ctx.t
    accent = P.C["violet"]
    hot = P.C["magenta"]
    pulse = ctx.pulse
    cx, cy = 96, 15

    # tunnel: zooming rectangles
    for i in range(10):
        s = ((t * 0.42 + i / 10.0) % 1.0)
        e = fx.ease_out(s)
        hw = int(4 + e * 52)
        hh = int(1 + e * 15)
        col = P.mix(accent, WHITE, 0.55 * s)
        r0, r1 = cy - hh, cy + hh
        c0, c1 = cx - hw, cx + hw
        if r0 >= 4 and r1 <= 34 and c0 >= 2 and c1 <= 189:
            fr.hline(r0, c0, c1, "─", fg=P.mix(col, VOID, 0.65))
            fr.hline(r1, c0, c1, "─", fg=P.mix(col, VOID, 0.65))
            fr.vline(c0, r0, r1, "│", fg=P.mix(col, VOID, 0.7))
            fr.vline(c1, r0, r1, "│", fg=P.mix(col, VOID, 0.7))
    # hypnotic spiral
    n = 540
    for k in range(n):
        ang = k * 0.135 + t * 2.4
        rad = 0.5 + k * 0.034 * (1.0 + 0.12 * math.sin(t * 1.7))
        x = int(cx + math.cos(ang) * rad * 1.85)
        y = int(cy + math.sin(ang) * rad * 0.92)
        if not fr.inb(y, x):
            continue
        u = k / n
        ch = "░▒▓█@"[min(4, int(u * 5 + 0.5))]
        fr.put(y, x, ch, fg=P.mix(P.mix(accent, WHITE, 0.5 - u * 0.5),
                                  VOID, 0.15 + 0.4 * u))
    # concentric counter-rotating rings
    for i in range(7):
        rx = 5 + i * 4.2
        ry = rx * 0.5
        spin = t * (0.9 if i % 2 else -0.9)
        for k in range(90):
            a = k / 90 * 2 * math.pi + spin
            if (k + i) % 5 == 0:
                continue
            x = int(cx + math.cos(a) * rx)
            y = int(cy + math.sin(a) * ry)
            if fr.inb(y, x):
                fr.put(y, x, "○" if i % 3 == 0 else ("·" if i % 3 == 1 else "◉"),
                       fg=P.mix(accent, WHITE, 0.35 - i * 0.02))
    # eyes at the eye of the spiral
    iris = 3.0 + 1.6 * pulse
    for side in (-1, 1):
        ex = cx + side * 13
        for k in range(64):
            a = k / 64 * 2 * math.pi
            x = int(ex + math.cos(a) * 9)
            y = int(cy + math.sin(a) * 4)
            if fr.inb(y, x):
                fr.put(y, x, "─" if abs(math.sin(a)) < 0.3 else "·",
                       fg=P.mix(WHITE, accent, 0.4))
        for j in range(3):
            rr = iris + j * 1.4
            for k in range(26):
                a = k / 26 * 2 * math.pi + t * (2.0 + j)
                x = int(ex + math.cos(a) * rr)
                y = int(cy + math.sin(a) * rr * 0.55)
                if fr.inb(y, x):
                    fr.put(y, x, "●" if j == 0 else "○",
                           fg=P.mix(hot, WHITE, 0.6 - j * 0.2))
        # pupil
        fr.fill_rect(cy - 1, ex - 1, cy + 1, ex + 1, " ", bg=VOID)
        if fr.inb(cy, ex):
            fr.put(cy, ex, "◉", fg=WHITE)
    # warp rays
    for k in range(16):
        a = k / 16 * 2 * math.pi + t * 0.25
        for d in range(12, 46, 2):
            x = int(cx + math.cos(a) * d * 1.8)
            y = int(cy + math.sin(a) * d * 0.9)
            if fr.inb(y, x) and fr.get(y, x) == " ":
                fr.put(y, x, "·", fg=P.mix(accent, VOID, 0.55))
    # pulsing wave rings on the beat
    for p2 in (0.0, 0.33, 0.66):
        q = (ctx.beat_p + p2) % 1.0
        rr = int(6 + q * 34)
        col = P.mix(hot, VOID, q)
        for k in range(80):
            a = k / 80 * 2 * math.pi
            x = int(cx + math.cos(a) * rr * 1.7)
            y = int(cy + math.sin(a) * rr * 0.8)
            if fr.inb(y, x):
                fr.put(y, x, "─" if abs(math.cos(a)) > 0.7 else "·", fg=col)

    # induction readouts
    _box(fr, 5, 2, 20, 40, "INDUCTION", accent)
    fr.write(7, 5, "depth  : " + format(fx.clamp(lt / dur), ".3f"), fg=DIM, bg=PANEL2)
    fr.write(8, 5, "state  : " + ("DEEP" if lt > 1.6 else "FALLING"),
             fg=P.mix(hot, WHITE, 0.3), bg=PANEL2)
    fr.write(9, 5, "focus  : 10 Hz", fg=DIM, bg=PANEL2)
    fr.write(11, 5, "COUNT", fg=DIM, bg=PANEL2)
    fr.write(11, 12, f"{max(0, 10 - int(lt * 2.7)):2d}", fg=WHITE, bg=PANEL2)
    _stat(fr, 13, 5, 39, (
        ("ALPHA ", fx.clamp(0.4 + 0.6 * pulse), "LOW", "violet"),
        ("THETA ", fx.clamp(0.3 + lt / dur), "HIGH", "magenta"),
        ("DELTA ", fx.clamp(0.2 + 0.4 * math.sin(t)), "---", "primary"),
    ))
    _box(fr, 5, 152, 20, 190, "EGO", hot)
    fr.write(7, 155, "dissolve : " + ("YES" if lt > 1.2 else "no"), fg=DIM, bg=PANEL2)
    fr.write(8, 155, "boundary : " + ("FADING" if lt > 0.8 else "firm"),
             fg=P.mix(hot, WHITE, 0.3), bg=PANEL2)
    fr.write(10, 155, "suggestion", fg=DIM, bg=PANEL2)
    for i in range(4):
        W.typing(fr, 11 + i, 155, ("enter", "the", "trance", "the trance")[i],
                 lt, start=0.4 + i * 0.35, cps=16, fg=P.mix(hot, WHITE, 0.35),
                 cursor=False)
    fr.write(17, 155, "10  9  8  7  6  5", fg=P.mix(accent, VOID, 0.3), bg=PANEL2)
    # flashing caption rows
    txt = "ENTER THE TRANCE  //  THE TRANCE  //  ENTER THE TRANCE"
    W.marquee(fr, 30, txt, t, speed=40.0, fg=P.mix(hot, VOID, 0.25), bg=VOID, gap=6)
    W.marquee(fr, 31, txt[::-1], -t, speed=34.0,
              fg=P.mix(accent, VOID, 0.3), bg=VOID, gap=6)
    if pulse > 0.7:
        for k in range(18):
            a = k / 18 * 2 * math.pi + t * 2
            x = int(cx + math.cos(a) * 54)
            y = int(cy + math.sin(a) * 13)
            if fr.inb(y, x):
                fr.put(y, x, "✦", fg=P.mix(hot, WHITE, pulse))


# -------------------------------------------------------------------- draw --
def draw(ctx):
    t = ctx.t
    fr = ctx.frame()
    si = 0
    for k in (3, 2, 1, 0):
        if t >= SEG_T0[k]:
            si = k
            break
    seg = SEGS[si]
    lt = t - SEG_T0[si]
    dur = SEG_T1[si] - SEG_T0[si]
    accent = P.C[seg["accent"]]
    ctx.meta["bloom"] = 0.50
    ctx.meta["tint"] = (P.mix(accent, WHITE, 0.35), 0.05)
    ctx.meta["scan"] = 0.32
    ctx.meta["vignette"] = 1.0

    _bg(fr, ctx, si, seg)
    _top(fr, ctx, si, lt, seg)
    if si == 0:
        _seg_gender(fr, ctx, lt, dur, seg)
    elif si == 1:
        _seg_clock(fr, ctx, lt, dur, seg)
    elif si == 2:
        _seg_role(fr, ctx, lt, dur, seg)
    else:
        _seg_trance(fr, ctx, lt, dur, seg)
    _bottom(fr, ctx, si, lt, seg)
    _boundary(fr, ctx, si, lt)
    return fr
