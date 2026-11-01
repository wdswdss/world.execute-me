"""s14 heartfix — instrumental: the heart is rebuilt, its defects found and repaired.

133.110 – 147.880.  Synthetic heart, one hole that should not exist and three
local dents; each defect is detected (red), patched (gold) and verified, then the
complete heart pulses on the beat.  "REPAIR COMPLETE".
"""
from __future__ import annotations

import math

import numpy as np

from .. import palette as P, fx, widgets as W
from .. import font as F
from .. import art as A
from ..assets import BEAT, T0

C_VOID = P.C["void"]
C_VOID2 = P.C["void2"]
C_PANEL = P.C["panel"]
C_PANEL2 = P.C["panel2"]
C_GRID = P.C["grid"]
C_LINE = P.C["line"]
C_DIM = P.C["dim"]
C_MID = P.C["mid"]
C_FG = P.C["fg"]
C_WHITE = P.C["white"]
C_PRIMARY = P.C["primary"]
C_TEAL = P.C["teal"]
C_GOLD = P.C["gold"]
C_AMBER = P.C["amber"]
C_ORANGE = P.C["orange"]
C_RED = P.C["red"]
C_CRIMSON = P.C["crimson"]
C_MAGENTA = P.C["magenta"]
C_BLUE = P.C["blue"]

I_DOT = F.char_index("·")
I_DOT2 = F.char_index("•")
I_CELL = F.char_index("▪")
I_X = F.char_index("×")
I_RING = F.char_index("○")
I_ON = F.char_index("●")
I_HUB = F.char_index("◉")
I_SPARK = F.char_index("◆")
I_H = F.char_index("─")
I_V = F.char_index("│")
I_HALF = F.char_index("▄")
I_UP = F.char_index("▀")
I_BLOCK = F.char_index("█")
I_LOW = F.char_index("░")
I_MID = F.char_index("▒")
I_HI = F.char_index("▓")
I_CHECK = F.char_index("✓")
I_CROSS = F.char_index("×")
I_BLANK = F.char_index(" ")

W_IDX = 192
T_S = 133.110
DUR = 14.770

# heart cell grid
HW, HH = 46, 27
R0, C0 = 10, 96 - HW // 2
MASK_W, MASK_H = HW * 10, HH * 18

# defect convention shared with the other heart scenes
HOLE = ((0.50, 0.46, 0.105),)
DENT1 = (0.26, 0.30, 0.075)
DENT2 = (0.73, 0.32, 0.070)
DENT3 = (0.50, 0.74, 0.065)
DENTS = (DENT1, DENT2, DENT3)

# MASKS[n] = heart with n defects repaired (0 = all defects present)
# heart_fill() already returns a solid classic heart silhouette with a natural
# cleft and apex; only saturate the antialiased edge.
def _heart_mask(w_px, h_px, **kw):
    return A.heart_fill(w_px, h_px, **kw)


_RAW_MASKS = [
    _heart_mask(MASK_W, MASK_H, holes=HOLE, dents=DENTS),
    _heart_mask(MASK_W, MASK_H, holes=(), dents=DENTS),
    _heart_mask(MASK_W, MASK_H, holes=(), dents=(DENT2, DENT3)),
    _heart_mask(MASK_W, MASK_H, holes=(), dents=(DENT3,)),
    _heart_mask(MASK_W, MASK_H, holes=(), dents=()),
]
MASKS = [np.clip((m - 0.30) * 4.0, 0.0, 1.0).astype(np.float32) for m in _RAW_MASKS]

DEFECTS = [
    {"id": "HOLE#001", "kind": "hole", "fx": 0.50, "fy": 0.46, "fr": 0.105,
     "note": "a hole that should not exist"},
    {"id": "DENT#001", "kind": "dent", "fx": 0.26, "fy": 0.30, "fr": 0.075,
     "note": "local concave deformation / left lobe"},
    {"id": "DENT#002", "kind": "dent", "fx": 0.73, "fy": 0.32, "fr": 0.070,
     "note": "local concave deformation / right lobe"},
    {"id": "DENT#003", "kind": "dent", "fx": 0.50, "fy": 0.74, "fr": 0.065,
     "note": "local concave deformation / apex"},
]
for d in DEFECTS:
    d["col"] = int(round(C0 + d["fx"] * HW))
    d["row"] = int(round(R0 + d["fy"] * HH))
    d["rad"] = max(1.6, d["fr"] * HW)

# detection / repair schedule (local seconds)
T_FIND = [2.20, 3.05, 3.90, 4.75]
T_PATCH = [5.35, 6.75, 8.15, 9.55]
PATCH_DUR = 0.95
T_DONE = [T_PATCH[k] + PATCH_DUR for k in range(4)]
T_ASSEMBLE = 0.25
T_ASSEMBLE_END = 2.15
T_COMPLETE = 10.90

Y = np.arange(MASK_H, dtype=np.float32)[:, None] + 0.5


def _c01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else float(v))


def _plot(fr, rs, cs, ch, fg, mask=None):
    rs = np.asarray(rs, np.int32)
    cs = np.asarray(cs, np.int32)
    rcl = np.clip(rs, 0, fr.rows - 1)
    ccl = np.clip(cs, 0, fr.cols - 1)
    good = (rs == rcl) & (cs == ccl)
    if mask is not None:
        good &= np.asarray(mask, bool)
    if not good.any():
        return
    fr.ch[rcl[good], ccl[good]] = ch
    if np.ndim(fg) == 1:
        fr.fg[rcl[good], ccl[good]] = np.asarray(fg, np.uint8)
    else:
        fr.fg[rcl[good], ccl[good]] = np.asarray(fg, np.uint8)[good]


# ------------------------------------------------------------------- timing ---
def _defect_state(k, t):
    """0 hidden, 1 found, 2 patching, 3 fixed."""
    lt = t - T_S
    if lt >= T_DONE[k]:
        return 3
    if lt >= T_PATCH[k]:
        return 2
    if lt >= T_FIND[k]:
        return 1
    return 0


def _repaired_count(t):
    return sum(1 for k in range(4) if t - T_S >= T_DONE[k])


def _patch_frac(k, t):
    lt = t - T_S
    if lt < T_PATCH[k]:
        return 0.0
    return _c01((lt - T_PATCH[k]) / PATCH_DUR)


def _mask_now(t):
    lt = t - T_S
    n = 0
    for k in range(4):
        if lt >= T_DONE[k]:
            n += 1
    return MASKS[n], n


def _glitch(t):
    lt = t - T_S
    g = 0.012 + 0.020 * fx.smoothstep(lt, 0.0, 0.7) * \
        (1.0 - fx.smoothstep(lt, 2.2, 3.0))
    for k in range(4):
        g += 0.020 * max(0.0, 1.0 - (lt - T_FIND[k]) / 0.30) if lt >= T_FIND[k] else 0.0
        g += 0.016 * max(0.0, 1.0 - (lt - T_DONE[k]) / 0.35) if lt >= T_DONE[k] else 0.0
    return min(g, 0.075)


# ---------------------------------------------------------------------- page --
def _bg(fr, ctx, lt, pulse):
    t = ctx.t
    fr.fill_rect(0, 0, 44, W_IDX - 1, " ", bg=C_VOID)
    # surgical grid
    for r in range(2, 45, 3):
        fr.fill_rect(r, 0, r, W_IDX - 1, "·", fg=P.mix(C_GRID, C_VOID, 0.34))
    for c in range(0, W_IDX, 14):
        for r in range(2, 45, 3):
            fr.put(r, c, "┼", fg=P.mix(C_GRID, C_VOID, 0.10))
    # side data columns (left of the heart)
    rng = np.random.default_rng(4242)
    for k in range(26):
        c = int(rng.integers(1, 66)) if k % 2 else int(rng.integers(126, 191))
        head = (t * (7.0 + 15.0 * rng.random()) + rng.random() * 42) % 45
        for q in range(3 + int(rng.random() * 4)):
            r = int(head) - q
            if 2 <= r < 45:
                fr.put(r, c, I_DOT, fg=P.mix(C_GRID, C_VOID, 0.18 + 0.20 * q * 0.25))
    # scan sweep band (single row)
    sr = int((t * 9.0) % 48)
    fr.fill_rect(sr, 0, sr, W_IDX - 1, " ", bg=P.mix(C_GOLD, C_VOID, 0.90))
    # corner telemetry columns
    for k, c in enumerate((2, 18, 34, 50, 146, 162, 178)):
        col = P.mix(C_GOLD if k % 2 == 0 else C_TEAL, C_VOID, 0.55)
        for r in range(3, 45):
            if (r * 7 + k * 13 + int(t * 12)) % 11 == 0:
                fr.put(r, c, "│", fg=col)
    ctx.set_glitch(_glitch(t))


def _frame_lines(fr, ctx, lt):
    fr.hline(2, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.38))
    fr.write(2, 1, "┌ CARDIAC REBUILD BAY // UNIT 0x0F ",
             fg=P.mix(C_LINE, C_VOID, 0.10), bg=C_VOID)
    done = _repaired_count(ctx.t)
    fr.write(2, 158, f" REPAIRED {done}/4 ┐",
             fg=P.mix(C_GOLD if done == 4 else C_AMBER, C_VOID, 0.15), bg=C_VOID)
    fr.hline(39, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.38))


# ------------------------------------------------------------------- widgets --
def _hud(fr, ctx, lt, pulse):
    t = ctx.t
    done = _repaired_count(t)
    phase = "ASSEMBLY" if lt < T_ASSEMBLE_END else (
        "SCAN" if lt < T_PATCH[0] else ("REPAIR" if lt < T_COMPLETE else "COMPLETE"))
    col = C_BLUE if phase == "ASSEMBLY" else (C_AMBER if phase == "SCAN" else
                                              (C_GOLD if phase == "REPAIR" else C_WHITE))
    fr.write(0, 1, "HEART REBUILD // PROCEDURE 0x0F", fg=P.mix(col, C_VOID, 0.15))
    fr.ctext(0, f"// {phase} // CARDIAC MESH SYNTHESIS //",
             fg=P.mix(col, C_VOID, 0.05))
    fr.rtext(0, f"T+{lt:05.2f}  FRM {int(t * 30):05d}",
             fg=P.mix(C_DIM, C_VOID, 0.15))
    integ = min(100.0, 34.0 + 16.5 * done + (6.0 if lt > T_COMPLETE else 0.0))
    fr.write(1, 1, f"MESH NODES 41207/41207   INTEGRITY {integ:5.1f}%   "
                   f"BEAT {int((t - T0) / BEAT) % 1000:03d}",
             fg=P.mix(C_GOLD, C_VOID, 0.10))
    if lt >= T_COMPLETE:
        fr.write(1, 116, "◆ REPAIR COMPLETE // VITALS STABLE",
                 fg=P.mix(C_TEAL, C_VOID, 0.05 + 0.10 * pulse))
    elif lt >= T_PATCH[0]:
        k = min(3, max(0, int((lt - T_PATCH[0]) // 1.4)))
        fr.write(1, 116, f"PATCHING {DEFECTS[k]['id']} …",
                 fg=P.mix(C_AMBER, C_VOID, 0.10 + 0.10 * pulse))
    elif lt >= T_FIND[0]:
        fr.write(1, 116, "! DEFECTS DETECTED — SCHEDULING PATCH…",
                 fg=P.mix(C_RED, C_VOID, 0.10 + 0.10 * pulse))
    else:
        fr.write(1, 116, "MATERIALISING MESH // SCAN ARM ARMED",
                 fg=P.mix(C_BLUE, C_VOID, 0.20))


def _queue(fr, ctx, lt):
    r0, c0, r1, c1 = 3, 127, 13, 190
    fr.fill_rect(r0, c0, r1, c1, " ", bg=C_PANEL)
    fr.box(r0, c0, r1, c1, 1, fg=P.mix(C_LINE, C_VOID, 0.10), bg=C_PANEL,
           title="REPAIR QUEUE // DEFECTS")
    for k, d in enumerate(DEFECTS):
        r = r0 + 1 + k * 2
        st = _defect_state(k, ctx.t)
        if st == 0:
            name, scol = "WAITING", P.mix(C_DIM, C_VOID, 0.05)
        elif st == 1:
            name, scol = "FOUND", P.mix(C_RED, C_VOID, 0.0)
        elif st == 2:
            name, scol = "PATCHING", P.mix(C_AMBER, C_VOID, 0.0)
        else:
            name, scol = "FIXED ✓", P.mix(C_TEAL, C_VOID, 0.0)
        fr.write(r, c0 + 2, d["id"], fg=P.mix(C_GOLD, C_VOID, 0.05), bg=C_PANEL)
        fr.write(r, c0 + 13, name, fg=scol, bg=C_PANEL)
        bar = 0.0
        if st == 3:
            bar = 1.0
        elif st == 2:
            bar = _patch_frac(k, ctx.t)
        W.progress_bar(fr, r, c0 + 26, 26, bar,
                       fg=P.mix(C_GOLD if st < 3 else C_TEAL, C_VOID, 0.10),
                       bg=C_PANEL, show_pct=False)
        fr.write(r, c0 + 54, f"{int(bar * 100):3d}%", fg=scol, bg=C_PANEL)
        if st == 1 and r + 1 <= r1:
            fr.write(r + 1, c0 + 2, d["note"][:44],
                     fg=P.mix(C_DIM, C_VOID, 0.0), bg=C_PANEL)
        elif st >= 2 and r + 1 <= r1:
            fr.write(r + 1, c0 + 2, "  " + ("pressing edge into mesh" if st == 2
                                            else "surface verified / no void"),
                     fg=P.mix(C_TEAL if st == 3 else C_AMBER, C_VOID, 0.30),
                     bg=C_PANEL)
    if lt >= T_COMPLETE:
        fr.fill_rect(r1 - 1, c0 + 1, r1 - 1, c1 - 1, " ", bg=C_PANEL)
        fr.write(r1 - 1, c0 + 3, "✓ ALL DEFECTS REPAIRED — HEART RESTORED",
                 fg=P.mix(C_TEAL, C_VOID, 0.0), bg=C_PANEL)


def _steps(fr, ctx, lt):
    r0, c0, r1, c1 = 3, 1, 13, 55
    fr.fill_rect(r0, c0, r1, c1, " ", bg=C_PANEL)
    fr.box(r0, c0, r1, c1, 1, fg=P.mix(C_LINE, C_VOID, 0.10), bg=C_PANEL,
           title="PROCEDURE LOG")
    done = _repaired_count(ctx.t)
    steps = [
        ("01 ASSEMBLE MESH", lt >= T_ASSEMBLE_END),
        ("02 SCAN SURFACE", lt >= T_FIND[3]),
        ("03 SEAL HOLE #001", lt >= T_DONE[0]),
        (f"04 PRESS DENTS  {done if done > 1 else 0}/3", lt >= T_DONE[3]),
    ]
    for k, (s, ok) in enumerate(steps):
        r = r0 + 1 + k
        mark = "✓" if ok else ("▶" if not ok and k == _cur_step(lt) else "·")
        col = C_TEAL if ok else (C_AMBER if mark == "▶" else C_DIM)
        fr.write(r, c0 + 2, f"[{mark}] {s}", fg=P.mix(col, C_VOID, 0.0), bg=C_PANEL)
    # scan log
    r5 = r0 + 6
    fr.write(r5, c0 + 2, "SCAN LOG", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_PANEL)
    lines = []
    for k, d in enumerate(DEFECTS):
        st = _defect_state(k, ctx.t)
        if st >= 1:
            lines.append((f"{d['id']} {d['kind'].upper()} at "
                          f"[{d['col']:02d},{d['row']:02d}]",
                          C_RED if st == 1 else (C_AMBER if st == 2 else C_TEAL)))
    if lt < T_FIND[0]:
        lines.append(("scanning 0x00E1… no defects yet", C_DIM))
    for k, (ln, col) in enumerate(lines[-3:]):
        fr.write(r5 + 1 + k, c0 + 2, ln[:50], fg=P.mix(col, C_VOID, 0.05), bg=C_PANEL)


def _cur_step(lt):
    if lt < T_ASSEMBLE_END:
        return 0
    if lt < T_FIND[3]:
        return 1
    if lt < T_DONE[0]:
        return 2
    return 3


def _heart(fr, ctx, lt, pulse):
    mask, nrep = _mask_now(ctx.t)
    t = ctx.t
    # assembly gate sweeps upward
    if lt < T_ASSEMBLE_END:
        a = _c01((lt - T_ASSEMBLE) / (T_ASSEMBLE_END - T_ASSEMBLE))
        gate_row = (1.0 - a) * (MASK_H + 40)
        gate = np.clip((gate_row - Y) / 26.0, 0.0, 1.0)
        m = mask * gate
        alpha = 0.30 + 0.70 * a
        # construction dust
        prng = np.random.default_rng(ctx.fi * 31 + 5)
        for k in range(90):
            ang = prng.random() * 2 * math.pi
            rad0 = 26.0 + 120.0 * prng.random()
            sp = 0.5 + 0.7 * prng.random()
            p = _c01((lt - T_ASSEMBLE) / 1.5 * sp)
            rad = rad0 * (1.0 - p) + 2.0
            rr = int(round(R0 + HH * 0.5 + math.sin(ang) * rad * 0.5))
            cc = int(round(96 + math.cos(ang) * rad))
            if 0 <= rr < 45 and 0 <= cc < W_IDX:
                fr.put(rr, cc, I_DOT if p < 0.55 else I_CELL,
                       fg=P.mix(C_GOLD, C_VOID, 0.30 + 0.45 * p), bg=None)
        sweep_r = int(R0 + HH - gate_row / 18.0)
        if 0 <= sweep_r < 45:
            fr.fill_rect(sweep_r, C0 - 2, sweep_r, C0 + HW + 1, "─",
                         fg=P.mix(C_GOLD, C_WHITE, 0.30))
    else:
        m = mask
        alpha = 1.0

    cells = m.reshape(HH, 18, HW, 10).mean(axis=(1, 3))
    if lt < T_ASSEMBLE_END:
        cells = cells * alpha
    v = np.clip(cells, 0.0, 1.0)
    ramp = np.array([F.char_index(c) for c in " ░▒▓█"], np.int16)
    idx = np.clip((v * 4.0 + 0.5).astype(np.int16), 0, 4)
    ch = ramp[idx]
    any_ = v > 0.02
    repair_glow = 1.0 if lt >= T_COMPLETE else 0.0
    base_col = np.asarray(P.mix(C_GOLD, C_VOID, 0.42), np.float32)
    rim_col = np.asarray(P.mix(C_AMBER, C_WHITE, 0.25 + 0.25 * pulse), np.float32)
    hot_col = np.asarray(P.mix(C_GOLD, C_WHITE,
                               0.30 + 0.20 * pulse + 0.25 * repair_glow), np.float32)
    ve = np.clip(v * 1.35, 0.0, 1.0)[..., None]
    col = base_col[None, None, :] * (1.0 - ve) + rim_col[None, None, :] * ve
    col = col * (1.0 - v[..., None]) + hot_col[None, None, :] * v[..., None]
    rr, cc = np.nonzero(any_)
    cols_u8 = np.clip(col[rr, cc], 0, 255).astype(np.uint8)
    _plot(fr, rr + R0, cc + C0, ch[rr, cc], cols_u8)

    if lt < T_ASSEMBLE_END:
        return
    # defect markers
    for k, d in enumerate(DEFECTS):
        st = _defect_state(k, ctx.t)
        r, c, rad = d["row"], d["col"], d["rad"]
        if st == 3:
            if lt - T_DONE[k] < 0.45:
                ph = (lt - T_DONE[k]) / 0.45
                th = np.linspace(0, 2 * math.pi, 26)
                rr2 = np.rint(r + np.sin(th) * rad * (1.0 + 1.6 * ph)).astype(np.int32)
                cc2 = np.rint(c + np.cos(th) * rad * 1.9 * (1.0 + 1.6 * ph)).astype(np.int32)
                _plot(fr, rr2, cc2, I_DOT,
                      P.mix(C_WHITE, C_TEAL, 0.30 + 0.40 * ph))
            continue
        if st == 0:
            continue
        blink = 0.55 + 0.45 * (1.0 if pulse > 0.35 else 0.0)
        if st == 1:
            # red scan marker: ring + crosshair + tag
            th = np.linspace(0, 2 * math.pi, 30)
            rr2 = np.rint(r + np.sin(th) * rad * 0.95).astype(np.int32)
            cc2 = np.rint(c + np.cos(th) * rad * 1.85).astype(np.int32)
            _plot(fr, rr2, cc2, I_RING, P.mix(C_RED, C_VOID, 0.05 + 0.25 * blink))
            fr.hline(r, max(0, c - 7), min(W_IDX - 1, c + 7), "─",
                     fg=P.mix(C_RED, C_VOID, 0.35), bg=None)
            fr.vline(max(0, r - 4), min(44, r + 4), c, "│",
                     fg=P.mix(C_RED, C_VOID, 0.35), bg=None)
            fr.write(r - 1, c + 2, f"!{k + 1}", fg=P.mix(C_RED, C_WHITE, 0.25),
                     bg=None)
            fr.write(max(0, r - 5), max(0, c - 4), d["id"],
                     fg=P.mix(C_RED, C_WHITE, 0.10), bg=None)
        else:
            # patch: growing gold disc + sparks
            f = _patch_frac(k, ctx.t)
            rr2, cc2 = [], []
            rad_c = rad * (0.5 + 1.7 * f)
            for dy in range(-6, 7):
                for dx in range(-11, 12):
                    if (dy / max(0.1, rad_c * 0.9)) ** 2 + (dx / max(0.1, rad_c * 1.8)) ** 2 <= 1.0:
                        rr2.append(r + dy)
                        cc2.append(c + dx)
            if rr2:
                _plot(fr, np.array(rr2), np.array(cc2), I_BLOCK,
                      P.mix(C_GOLD, C_WHITE, 0.30 + 0.35 * f))
            if f > 0.15:
                prng = np.random.default_rng(ctx.fi * 17 + k)
                for q in range(10):
                    ang = prng.random() * 2 * math.pi
                    rad_s = rad * (1.0 + 1.4 * prng.random()) * (0.6 + 1.4 * f)
                    rr3 = int(round(r + math.sin(ang) * rad_s * 0.7))
                    cc3 = int(round(c + math.cos(ang) * rad_s * 1.5))
                    fr.put(rr3, cc3, I_SPARK,
                           fg=P.mix(C_GOLD, C_WHITE, 0.40), bg=None)
            fr.write(r - 1, c + 2, f"PATCH {int(f * 100):02d}%",
                     fg=P.mix(C_AMBER, C_WHITE, 0.20), bg=C_VOID)

    # beat rings / complete heart
    if lt >= T_COMPLETE:
        for k in range(3):
            ph = ((lt - T_COMPLETE) * 0.55 + k / 3.0) % 1.0
            rad = 12.0 + 32.0 * ph
            th = np.linspace(0, 2 * math.pi, 48)
            rr2 = np.rint(R0 + HH * 0.5 + np.sin(th) * rad * 0.85).astype(np.int32)
            cc2 = np.rint(96 + np.cos(th) * rad * 1.75).astype(np.int32)
            _plot(fr, rr2, cc2, I_DOT,
                  P.mix(C_GOLD if k % 2 == 0 else C_TEAL, C_VOID,
                        0.05 + 0.85 * ph))
        # dimension brackets around the whole heart
        for (rr, cc) in ((R0 - 1, C0 - 3), (R0 - 1, C0 + HW + 2),
                         (R0 + HH + 1, C0 - 3), (R0 + HH + 1, C0 + HW + 2)):
            fr.put(rr, cc, "┼", fg=P.mix(C_GOLD, C_VOID, 0.55), bg=None)
        fr.write(R0 - 1, C0 - 1, "LV // RV // MESH 0x0F",
                 fg=P.mix(C_GOLD, C_VOID, 0.62), bg=None)
        fr.write(R0 + HH + 1, C0 + 2, "HEART // 100% // STABLE // 130 BPM",
                 fg=P.mix(C_TEAL, C_VOID, 0.28), bg=None)


def _scan_beam(fr, ctx, lt):
    if not (T_ASSEMBLE_END <= lt < T_PATCH[0] + 0.4):
        return
    a = _c01((lt - T_ASSEMBLE_END) / 1.6)
    r = int(R0 + HH * a)
    fr.fill_rect(r, C0 - 2, r, C0 + HW + 1, "─",
                 fg=P.mix(C_WHITE, C_GOLD, 0.25 + 0.35 * ctx.pulse))
    fr.write(r, max(0, C0 - 6), "SCAN", fg=P.mix(C_WHITE, C_GOLD, 0.40), bg=None)


def _complete_words(fr, ctx, lt, pulse):
    a = fx.smoothstep(lt, T_COMPLETE, T_COMPLETE + 0.55)
    if a <= 0.02:
        return
    h = int(round(3 + 3 * fx.smoothstep(lt, T_COMPLETE, T_COMPLETE + 0.9)))
    col = P.mix(C_GOLD, C_WHITE, 0.28 + 0.22 * pulse)
    fr.paint_text("REPAIR COMPLETE", 32, 96, h, col,
                  P.mix(C_WHITE, C_GOLD, 0.42), align="center",
                  ramp=P.RAMP_BLOCK, alpha=min(0.95, 0.50 + 0.45 * a))


def _bottom(fr, ctx, lt, pulse):
    t = ctx.t
    fr.hline(40, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.30))
    asm = _c01((lt - T_ASSEMBLE) / (T_ASSEMBLE_END - T_ASSEMBLE)) if lt < T_ASSEMBLE_END else 1.0
    done = _repaired_count(t)
    rep = done / 4.0
    if any(_defect_state(k, t) == 2 for k in range(4)):
        kk = next(k for k in range(4) if _defect_state(k, t) == 2)
        rep = (kk + _patch_frac(kk, t)) / 4.0
    integ = _c01(34.0 / 100.0 + 0.165 * done + (0.06 if lt > T_COMPLETE else 0.0))
    fr.write(41, 1, "ASSEMBLY", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
    W.progress_bar(fr, 41, 11, 30, min(1.0, asm) if lt > T_ASSEMBLE else 0.0,
                   fg=P.mix(C_BLUE, C_VOID, 0.15), bg=C_VOID2, show_pct=False)
    fr.write(41, 44, "REPAIR", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
    W.progress_bar(fr, 41, 52, 30, rep, fg=P.mix(C_GOLD, C_VOID, 0.15),
                   bg=C_VOID2, show_pct=False)
    fr.write(41, 85, "INTEGRITY", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
    W.progress_bar(fr, 41, 96, 30, integ, fg=P.mix(C_TEAL, C_VOID, 0.15),
                   bg=C_VOID2, show_pct=False)
    fr.write(41, 129, f"STATUS {phase_name(lt)}",
             fg=P.mix(C_GOLD if lt > T_COMPLETE else C_AMBER, C_VOID, 0.05),
             bg=C_VOID2)
    if lt >= T_COMPLETE:
        fr.fill_rect(42, 1, 42, W_IDX - 2, " ", bg=P.mix(C_GOLD, C_VOID, 0.88))
        fr.write(42, 2, "  HEART RESTORED  //  NO DEFECTS REMAIN  //  "
                        "4096 NODES RE-SEATED  //  PULSE SYNCHRONISED  //  "
                        "REPAIR COMPLETE  ",
                 fg=P.mix(C_VOID, C_WHITE, 0.55))
    else:
        fr.write(42, 1, "MANUAL PATCH SEQUENCE // "
                        + (f"{DEFECTS[_cur_step(lt) - 1]['id']} "
                           f"({DEFECTS[_cur_step(lt) - 1]['note'][:26]})"
                           if _cur_step(lt) in (2, 3) else "waiting for scan"),
                 fg=P.mix(C_DIM, C_VOID, 0.10), bg=C_VOID2)
    msg = ("  REPAIR PROCEDURE 0x0F  //  HOLE#001: A HOLE THAT SHOULD NOT EXIST  //  "
           "DENT#001-003: LOCAL CONCAVE DEFORMATIONS  //  SEALING  //  PRESSING  //  "
           "VERIFYING  //  HEART RESTORED  ")
    W.marquee(fr, 44, msg, t, speed=30.0, fg=P.mix(C_GOLD, C_VOID, 0.05),
              bg=C_VOID2)


def phase_name(lt):
    if lt < T_ASSEMBLE_END:
        return "ASSEMBLING"
    if lt < T_FIND[3]:
        return "SCANNING"
    if lt < T_DONE[3]:
        return "PATCHING"
    if lt < T_COMPLETE:
        return "VERIFYING"
    return "COMPLETE"


# --------------------------------------------------------------------- draw ---
# ----------------------------------------------------------------- ambient --
def _ambient(fr, ctx, lt, pulse):
    """Scan field around the heart: mesh, rings, spokes, rulers, dust."""
    t = ctx.t
    cx, cy = 96.0, 23.0
    # faint mesh grid over the whole stage
    mesh = P.mix(C_GOLD, C_VOID, 0.80)
    for r in range(3, 43, 2):
        for c in range(3 + (r % 4), 190, 4):
            if (r + c) % 3 == 0:
                fr.put(r, c, I_DOT, fg=mesh)
    # concentric rings
    for k in range(4):
        R = 15.0 + k * 8.5 + 2.2 * math.sin(t * 1.7 + k * 1.3)
        a = 0.30 + 0.18 * (k % 2) + 0.25 * pulse
        col = P.mix(C_GOLD, C_VOID, max(0.0, 0.62 - 0.10 * k - 0.18 * (1 - a)))
        for d in range(0, 72):
            ang = d / 72.0 * 2.0 * math.pi
            x = int(round(cx + math.cos(ang) * R * 2.05))
            y = int(round(cy + math.sin(ang) * R * 0.62))
            if 1 <= x <= 190 and 1 <= y <= 43:
                fr.put(y, x, I_DOT if (d + k) % 3 else I_CELL, fg=col)
    # radial spokes
    for j in range(16):
        ang = j / 16.0 * 2.0 * math.pi + t * 0.10
        for q in range(8, 40, 2):
            x = int(round(cx + math.cos(ang) * q * 2.05))
            y = int(round(cy + math.sin(ang) * q * 0.62))
            if 1 <= x <= 190 and 1 <= y <= 43 and (q + j) % 4:
                fr.put(y, x, I_H if j % 2 else I_DOT,
                       fg=P.mix(C_GOLD, C_VOID, 0.62))
    # edge rulers + corner ticks
    edge = P.mix(C_GOLD, C_VOID, 0.55)
    for c in range(2, 191):
        if c % 6 == 0:
            fr.put(2, c, I_H, fg=edge)
            fr.put(43, c, I_H, fg=edge)
        if c % 30 == 0:
            fr.put(3, c, "|", fg=P.mix(C_GOLD, C_VOID, 0.70))
    for r in range(3, 43):
        if r % 6 == 0:
            fr.put(r, 2, I_V, fg=edge)
            fr.put(r, 190, I_V, fg=edge)
    # vertical scale bars left / right
    for k in range(18):
        r = 4 + k * 2
        h = int(1 + 2 * abs(math.sin(t * 2.2 + k * 0.55)))
        for q in range(h):
            fr.put(r - q, 5, "█", fg=P.mix(C_GOLD, C_VOID, 0.55))
            fr.put(r - q, 187, "█", fg=P.mix(C_TEAL, C_VOID, 0.60))
    # drifting dust
    for k in range(80):
        x = 3 + int((k * 37 + t * (6.0 + (k % 5) * 3.0)) % 186)
        y = 3 + int((k * 11 + t * (1.5 + (k % 7) * 0.6)) % 39)
        fr.put(y, x, I_DOT, fg=P.mix(C_GOLD, C_VOID, 0.72))


def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    lt = t - T_S
    pulse = float(ctx.pulse)
    _bg(fr, ctx, lt, pulse)
    _ambient(fr, ctx, lt, pulse)
    _frame_lines(fr, ctx, lt)
    _heart(fr, ctx, lt, pulse)
    _scan_beam(fr, ctx, lt)
    _steps(fr, ctx, lt)
    _queue(fr, ctx, lt)
    _complete_words(fr, ctx, lt, pulse)
    _hud(fr, ctx, lt, pulse)
    _bottom(fr, ctx, lt, pulse)
    fl = 0.0
    fcol = C_WHITE
    for k in range(4):
        if lt >= T_FIND[k] and lt < T_FIND[k] + 0.16:
            fl = max(fl, 0.10)
            fcol = C_RED
        if lt >= T_DONE[k] and lt < T_DONE[k] + 0.20:
            fl = max(fl, 0.10)
            fcol = C_GOLD
    if lt >= T_COMPLETE and lt < T_COMPLETE + 0.30:
        fl = max(fl, 0.20)
        fcol = C_GOLD
    ctx.meta["flash"] = fl
    ctx.meta["flash_color"] = fcol
    ctx.meta["bloom"] = 0.28 + 0.20 * pulse + (0.22 if lt > T_COMPLETE else 0.0)
    ctx.meta["tint"] = None
    sh = 0.0
    for k in range(4):
        if lt >= T_DONE[k]:
            sh = max(sh, 0.8 * max(0.0, 1.0 - (lt - T_DONE[k]) / 0.30))
    if lt >= T_COMPLETE:
        sh = max(sh, 0.9 * max(0.0, 1.0 - (lt - T_COMPLETE) / 0.5))
    if sh > 0.01:
        ctx.shake(sh, 900 + int(t * 7))
    return fr
