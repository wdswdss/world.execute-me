"""s02_title - every character of the interface is scrambled across the screen,
then re-assembled into WORLD.EXECUTE(ME); .

14.960 - 15.6   interface fragment from the boot still running
15.4  - 21.6    detach: characters break out of their panels and swarm the screen
21.6  - 24.7    swarm organises, glyphs start flying to their slots
24.7  - 29.73   title hardened: WORLD.EXECUTE(ME); in block letters
"""
from __future__ import annotations

import numpy as np

from .. import font as F
from ..frame import Frame
from .. import fx
from .. import layout as L
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

TITLE = TL.TITLE
T0 = 14.960
FORM = 24.700
CHAOS0 = 15.35
CHAOS1 = 21.70

_GLYPHS = "░▒▓█▀▄▌│─┼┤├┬┴◈◆◇■□▲▼◀▶●○◎★☆✦⚡♥♪∞≈≠≤≥±∑ΔπΩ√∫∂←→↑↓⇔↻✓✗☰☷⌘§¶" + "".join(
    "0123456789ABCDEF"
) + "".join("abcdefghijklmnopqrstuvwxyz")


# ------------------------------------------------------------------ source --
def _source_rows():
    rows = {}
    rows[1] = "┌ SYSTEM ─────────────────────────────────────┬─ RUNTIME ──────────────────────┐"
    rows[2] = "│ world.execute(me);        v1.0.0            │ kernel   ok                   │"
    rows[3] = "│ state   : RUNNING                           │ memory   0x7FF2A0              │"
    rows[4] = "│ objects : 39                                │ threads  64 / 64               │"
    rows[5] = "│ uptime  : 00:00:14                          │ latency  0.2 ms                │"
    rows[6] = "├─ DATA ───────────────────────────────────────┴───────────────────────────────┤"
    rows[7] = "│ 0x0000  5F 3A 01 FF  00 12 AB CD   ░▒▓███████████▓▒░   OBJECT::0x01          │"
    rows[8] = "│ 0x0010  00 00 00 01  FF FF 7F 3C   ░▒▓█████████▓▒░       OBJECT::0x02          │"
    rows[9] = "│ 0x0020  2B 7C 01 48  7D 02 0B B8   ▒▓████████▓▒░         PARAM::dimension      │"
    rows[10] = "│ 0x0030  00 A1 1C 4E  00 FF 3F 2A   ░▒▓██████▓▒░          PARAM::circumference  │"
    rows[11] = "├─ WAVEFORM ──────────────────────────────────────────────────────────────────┤"
    for k in range(6):
        chars = []
        for c in range(76):
            v = fx.noise1d(c * 0.35 + k * 1.7, 1) * 0.8 + fx.noise1d(c * 0.09, 2) * 0.2
            lvl = int((v + 1) * 3.5)
            chars.append(" ▁▂▃▄▅▆▇█"[max(0, min(8, lvl))])
        rows[12 + k] = "│ " + "".join(chars) + " │"
    rows[18] = "├─ LOG ───────────────────────────────────────────────────────────────────────┤"
    logs = [
        "> switch on the power line ............... OK",
        "> protection shield ...................... ENABLED",
        "> object creation ........................ 39 / 39",
        "> fill data / parameters ................. 12 / 12",
        "> initialization ......................... COMPLETE",
        "> setup new world ........................ BEGIN",
        "> simulation ............................. RUNNING",
        "> loading title .......................... ???",
        "> loading title .......................... ???",
        "> loading title .......................... ???",
    ]
    for i, ln in enumerate(logs):
        rows[19 + i] = "│ " + ln[:76].ljust(76) + " │"
    rows[30] = "└──────────────────────────────────────────────────────────────────────────────┘"
    rows[32] = "  ◉ WORLD.EXECUTE(ME);          SIMULATION RUNTIME          FRAME 000440  30FPS"
    rows[33] = "  BAR 008/112   BEAT 4/4   ──────────────────────────────────────────────────"
    return rows


def _build_arrays():
    """All particle data as numpy arrays (5.2k particles, one vectorised draw)."""
    rows = _source_rows()
    origin = []
    for r, ss in rows.items():
        for c, ch in enumerate(ss):
            if ch not in " ℃":
                origin.append((r, c, ch))
    tm = F.text_mask(TITLE, 10 * L.CELL_H, bold=True)
    w = max(1, int(round(tm.shape[1] / L.CELL_W)))
    h = 10
    mask = F.resize_mask(tm, w * L.CELL_W, h * L.CELL_H)
    cells = mask.reshape(h, L.CELL_H, w, L.CELL_W).mean(axis=(1, 3))
    slots = [(y, x) for y in range(h) for x in range(w) if cells[y, x] > 0.22]
    slots.sort()
    row0 = 17
    col0 = (L.STAGE_W - w) // 2

    total = 5200
    n = len(origin)
    h1 = np.array([fx.hash01(i, 1) for i in range(total)], np.float32)
    h2 = np.array([fx.hash01(i, 2) for i in range(total)], np.float32)
    h3 = np.array([fx.hash01(i, 3) for i in range(total)], np.float32)
    h4 = np.array([fx.hash01(i, 4) for i in range(total)], np.float32)
    oi = np.arange(total) % n
    r0 = np.array([origin[i][0] for i in oi], np.float32)
    c0 = np.array([origin[i][1] for i in oi], np.float32)
    cr = (h1 * (L.STAGE_H - 1)).astype(np.int32)
    cc = (h2 * (L.STAGE_W - 1)).astype(np.int32)
    si = (h3 * (len(slots) - 1)).astype(np.int32)
    sr = np.array([row0 + slots[i][0] for i in si], np.float32)
    sc = np.array([col0 + slots[i][1] for i in si], np.float32)
    gidx = np.empty(total, np.int16)
    for i in range(total):
        g = origin[oi[i]][2] if h1[i] > 0.55 else _GLYPHS[int(h4[i] * (len(_GLYPHS) - 1))]
        k = F.char_index(g)
        gidx[i] = k if k > 0 else F.char_index("?")
    return dict(r0=r0, c0=c0, cr=cr, cc=cc, sr=sr, sc=sc, h1=h1, h2=h2, h3=h3, h4=h4,
                gidx=gidx, total=total)


_PA = _build_arrays()
_PARTICLES = [None] * _PA["total"]          # only len() is used by the HUD


# ------------------------------------------------------------------- draw --
def draw(ctx):
    t = ctx.t
    lt = t - T0
    fr = ctx.frame()
    _starfield(fr, ctx)
    # the boot desk is never taken away: chrome, monitor bands and side columns
    # stay on screen for the whole interlude.  The code storm and the forming
    # title are painted *over* it, so there is no window where only the title
    # is left - and nothing has to be re-generated afterwards.
    _topmon(fr, ctx, lt)
    _botmon(fr, ctx, lt)
    _diffuse(fr, ctx, lt)
    _swarm(fr, ctx, lt)
    if lt < 3.0:
        iface_a = 1.0 - fx.smoothstep(lt, 1.5, 2.55)
        if iface_a > 0.01:
            _interface(fr, ctx, alpha=iface_a)
    # formed title: only once the desk has condensed back into place
    if lt > 8.30:
        _title(fr, ctx, lt)
    # once the title is locked, sweep the debris out of the gaps between the
    # monitor rows and the title band so the frame settles instead of staying noisy
    if lt > 10.02:
        for rr in range(10, 16):
            fr.fill_rect(rr, 0, rr, fr.cols - 1, " ", bg=P.C["void"])
        for rr in range(27, 32):
            fr.fill_rect(rr, 0, rr, fr.cols - 1, " ", bg=P.C["void"])
        for rr in range(1, 32):
            for cc2 in (0, 1, fr.cols - 2, fr.cols - 1):
                fr.put(rr, cc2, " ", bg=P.C["void"])
    _hud(fr, ctx, lt)
    # the assembled letters sit above the chrome rules, not under them
    _stamp_seated(fr, ctx)
    # post hints
    storm = fx.smoothstep(lt, 0.4, 3.0) * (1 - fx.smoothstep(lt, 8.6, 9.8))
    g = 0.10 + 0.09 * storm + 0.05 * ctx.pulse
    # no full-screen flash here: the re-assembly itself carries the beat
    g += 0.05 * fx.smoothstep(lt, 9.2, 10.0)
    ctx.set_glitch(g)
    ctx.meta["bloom"] = 0.5
    return fr


def _starfield(fr, ctx):
    t = ctx.t
    rng = ctx.rng(21)
    for k in range(120):
        c = rng.randint(0, fr.cols)
        sp = 0.6 + rng.random() * 2.4
        r = int((rng.random() * fr.rows + t * sp * 2) % fr.rows)
        b = 0.15 + rng.random() * 0.35
        fr.put(r, c, "·", fg=P.mix(P.C["void"], P.C["primary"], b))


def _stamp_seated(fr, ctx):
    """Draw the already-seated title cells on top of everything else.

    The scatter/diffuse/regather layers are free to paint anywhere; without
    this pass they punch dim holes through the letters that are still being
    assembled, which reads as the title flickering in and out.
    """
    seat = ctx.meta.get("seat")
    if not seat:
        return
    rr, cc = seat
    tc = _title_template()
    tch = tc["ch"][rr, cc]
    tfg = tc["fg"][rr, cc]
    lit = tch != 0
    if lit.any():
        fr.ch[rr[lit], cc[lit]] = tch[lit]
        fr.fg[rr[lit], cc[lit]] = tfg[lit]


def _dissolve(fr, amt, seed):
    """Punch hash-random holes out of the frame: the desk disintegrates instead
    of being switched off in one frame."""
    if amt <= 0.0:
        return
    rr = np.arange(fr.rows, dtype=np.float32)[:, None]
    cc = np.arange(fr.cols, dtype=np.float32)[None, :]
    h = np.mod(np.sin(rr * 12.9898 + cc * 78.233 + seed * 37.719) * 43758.5453, 1.0)
    m = h < amt
    if not m.any():
        return
    fr.ch[m] = 0
    fr.fg[m] = np.array(P.C["void"], np.uint8)
    fr.bg[m] = np.array(P.C["void"], np.uint8)


def _interface(fr, ctx, alpha=1.0):
    rows = _source_rows()
    off = max(0, (fr.cols - 80) // 2)
    for r, s in rows.items():
        if 0 <= r < fr.rows:
            fr.write(r, off, s, fg=P.mix(P.C["void"], P.C["teal"], 0.55 * alpha))
    # bright log lines
    for i in range(10):
        col = P.mix(P.C["void"], P.C["green"] if i < 8 else P.C["gold"], 0.8 * alpha)
        fr.write(19 + i, off + 1, rows[19 + i][: 4 + (i * 7) % 40], fg=col)
    # power residue
    fr.write(35, 2, "SIMULATION RUNTIME // WORLD.EXECUTE(ME);", fg=P.mix(P.C["void"], P.C["primary"], 0.8 * alpha))
    fr.write(37, 2, "OBJECTS 39  PARAMS 12  UPTIME 00:00:14  FRAME 000440", fg=P.mix(P.C["void"], P.C["mid"], 0.8 * alpha))


def _diffuse(fr, ctx, lt):
    """Glyph cloud spreading outward from the assembly band (21.0-22.3 s)."""
    d = fx.smoothstep(lt, 5.35, 7.60)
    if d <= 0.01:
        return
    a = _PA
    h1, h2, h3 = a["h1"], a["h2"], a["h3"]
    cc = float((a["c0"].mean() + a["cc"].mean()) * 0.5)
    rc = float((a["r0"].mean() + a["cr"].mean()) * 0.5)
    maxr = 3.0 + d * 26.0
    t = ctx.t
    # one glyph per sampled cell, deterministic
    keep = (h1 > 0.30) & (h2 < d * 0.98)
    idx = np.nonzero(keep)[0]
    if not len(idx):
        return
    # push each glyph outward from the band centre over time
    ya = (a["r0"][idx] + a["cr"][idx]) * 0.5
    xa = (a["c0"][idx] + a["cc"][idx]) * 0.5
    dy = (ya - rc)
    dx = (xa - cc)
    n = np.maximum(1e-3, np.hypot(dy, dx))
    speed = 1.0 + 2.0 * h3[idx]
    rr = np.rint(rc + dy / n * np.minimum(maxr, n * speed)).astype(np.int32)
    ccc = np.rint(cc + dx / n * np.minimum(maxr, n * speed)).astype(np.int32)
    ok = (rr >= 0) & (rr < fr.rows) & (ccc >= 0) & (ccc < fr.cols)
    if not ok.any():
        return
    rr, ccc = rr[ok], ccc[ok]
    hh = h1[idx][ok]
    gidx = a["gidx"][idx][ok]
    heat = fx.clamp((lt - 5.35) / 1.60)
    fade = 1.0 - fx.clamp((lt - 6.95) / 0.45)
    k = (0.10 + 0.30 * heat) * max(0.15, fade)
    base = np.array(P.C["primary"], np.float32)
    col = base[None, :] * (0.55 + 0.45 * hh[:, None])
    fr.ch[rr, ccc] = gidx
    fr.fg[rr, ccc] = np.clip(col * k, 0, 255).astype(np.uint8)


def _regather(fr, ctx, lt):
    """Glyph streams fly back into the monitor rows: the desk is rebuilt from the
    same characters that were thrown out, so the re-assembly is visible."""
    if lt < 6.6 or lt > 10.0:
        return
    n = 900
    i = np.arange(n, dtype=np.float64)
    h1 = np.mod(np.sin(i * 12.9898 + 4.1) * 43758.5453, 1.0)
    h2 = np.mod(np.sin(i * 78.233 + 9.7) * 43758.5453, 1.0)
    h3 = np.mod(np.sin(i * 37.719 + 1.3) * 43758.5453, 1.0)
    h4 = np.mod(np.sin(i * 5.397 + 7.7) * 43758.5453, 1.0)
    h5 = np.mod(np.sin(i * 21.113 + 3.9) * 43758.5453, 1.0)
    tgt_r = np.where(h1 < 0.55, 1 + (h2 * 9).astype(np.int32), 32 + (h2 * 11).astype(np.int32))
    tgt_c = (2 + (np.mod(np.sin(i * 3.7 + h3) * 43758.5453, 1.0) * 185)).astype(np.int32)
    # start: still far out in the swarm field, uncorrelated with the target so the
    # streams arrive diagonally instead of falling as vertical rain
    s_r = 30.0 + (h4 - 0.5) * 60.0
    s_c = 96.0 + (h5 - 0.5) * 184.0
    t0 = 6.9 + h3 * 0.9
    q = np.clip((lt - t0) / 1.95, 0.0, 1.0)
    qe = q * q * (3.0 - 2.0 * q)
    # arc: add a sideways bow so streams curve instead of sliding straight
    bow = np.sin(q * np.pi) * (h2 - 0.5) * 16.0
    x = s_c + (tgt_c - s_c) * qe + bow
    y = s_r + (tgt_r - s_r) * qe
    rr = np.rint(y).astype(np.int32)
    cc = np.rint(x).astype(np.int32)
    active = (lt > t0) & (q < 1.0)
    ok = active & (rr >= 1) & (rr < fr.rows - 1) & (cc >= 1) & (cc < fr.cols - 1)
    if not ok.any():
        return
    base = np.array(P.C["gold"], np.float32)[None, :]
    white = np.array(P.C["white"], np.float32)[None, :]
    k = (0.25 + 0.75 * qe)[:, None]
    # the streams die out as the desk locks, so text on the panels can be read
    fade = 1.0 - fx.smoothstep(lt, 9.05, 9.70)
    col = np.clip((base + (white - base) * k) * fade, 0, 255).astype(np.uint8)
    keep = h3 > fx.smoothstep(lt, 9.0, 9.65) * 0.72
    active = active & keep
    gi = (np.mod(h1 * 4099.0 + np.floor(lt * 24.0) * 7919.0, 1.0) * len(_GLYPHS)).astype(np.int32)
    gidx = np.array([F.char_index(_GLYPHS[k]) for k in range(len(_GLYPHS))], np.int16)
    rr, cc, col = rr[ok], cc[ok], col[ok]
    gi = gi[ok]
    dim = np.clip(col.astype(np.float32) * 0.45, 0, 255).astype(np.uint8)
    fr.ch[rr, cc] = gidx[gi]
    fr.fg[rr, cc] = col
    # short trail behind each stream
    tr = np.clip(rr - 1, 1, fr.rows - 2)
    tc = np.clip(cc + 0, 1, fr.cols - 2)
    fr.ch[tr, tc] = F.char_index("░")
    fr.fg[tr, tc] = dim



_TC = {}


def _title_template():
    """The finished title, baked once, so the swarm can *build* it cell by cell
    and the later `_title` pass only brightens the same cells (no re-draw)."""
    if _TC:
        return _TC
    fr = Frame(L.STAGE_H, L.STAGE_W)
    fr.paint_text(TITLE, 17, fr.cols // 2, 10,
                  fg=P.C["primary"], fg2=P.C["white"],
                  align="center", ramp=P.RAMP_BLOCK, alpha=1.0)
    _TC["ch"] = fr.ch.copy()
    _TC["fg"] = fr.fg.copy()
    return _TC


def _swarm(fr, ctx, lt):
    t = ctx.t
    if lt > 10.9:
        return
    a = _PA
    h1, h2, h3, h4 = a["h1"], a["h2"], a["h3"], a["h4"]
    d0 = 0.25 + h1 * 1.5
    active = lt >= d0
    p = np.clip((lt - d0) / 1.35, 0.0, 1.0)
    e = p * p * (3.0 - 2.0 * p)
    ang = h2 * 6.2832 + lt * (1.2 + h3 * 1.8)
    rad = 1.0 + 1.6 * np.sin(t * 2.3 + h4 * 17.3) + 0.6 * np.sin(t * 7.1 + h2 * 31.0)
    amp = 0.6 + 1.6 * e
    x = a["c0"] + (a["cc"] - a["c0"]) * e + rad * amp * np.cos(ang)
    y = a["r0"] + (a["cr"] - a["r0"]) * e + rad * 0.5 * amp * np.sin(ang)
    f0 = 5.55 + h3 * 1.35
    q = np.clip((lt - f0) / 2.10, 0.0, 1.0)
    qe = 1.0 + (q - 1.0) ** 2 * (2.4 * (q - 1.0) + 1.4)
    x = x + (a["sc"] - x) * qe
    y = y + (a["sr"] - y) * qe
    # progressive commit: the skeleton grows cell by cell from ~20.5 s and
    # never goes back (no "vanish and regenerate" between frames)
    grow = fx.smoothstep(lt, 5.60, 7.05)
    # ~4 particles share each title slot, so convert the desired per-slot
    # fill ratio into a per-particle threshold (keeps the build gradual)
    grow_slot = 1.0 - (1.0 - grow) ** 0.25
    grow_sel = h1 < grow_slot
    x = np.where(grow_sel, a["sc"], x)
    y = np.where(grow_sel, a["sr"], y)
    q = np.where(grow_sel, 1.0, q)
    rr = np.rint(y).astype(np.int32)
    ccc = np.rint(x).astype(np.int32)
    ok = active & (rr >= 0) & (rr < fr.rows) & (ccc >= 0) & (ccc < fr.cols)
    # texture: leave some cells empty so the frame reads as scattered glyphs,
    # not a uniform white-noise wall
    keep = np.mod(h1 * 4099.0 + int(t * 30) * 7919.0, 1.0) > 0.17
    keep = keep | (q > 0.55)      # seated glyphs stay: they *are* the title now
    ok = ok & keep
    if not ok.any():
        return
    # colour: dim interface -> hot swarm -> white hot seated glyph
    heat = np.clip((lt - d0) / 1.2, 0.0, 1.0)
    k = (0.18 + 0.35 * heat)[:, None]
    base = np.array(P.C["primary"], np.float32)[None, :]
    white = np.array(P.C["white"], np.float32)[None, :]
    col = base + (white - base) * k
    fleck = np.mod(h1 * 7919.0 + int(t * 20) * 104729.0, 1.0) > 0.86
    col[fleck] = np.array(P.C["gold"], np.float32)
    seated = q > 0.75
    col[seated] = white[0]
    col[~seated] *= 0.72
    # main glyphs (filtered to on-screen)
    rr, ccc = rr[ok], ccc[ok]
    qf, h2f, h3f, h4f = q[ok], h2[ok], h3[ok], h4[ok]
    colf = np.clip(col[ok], 0, 255).astype(np.uint8)
    fr.ch[rr, ccc] = a["gidx"][ok]
    fr.fg[rr, ccc] = colf
    # committed cells copy the finished title's own glyphs, so the letters are
    # literally being built up and the later `_title` pass changes nothing
    seat = qf > 0.86
    if seat.any():
        tc = _title_template()
        tch = tc["ch"][rr[seat], ccc[seat]]
        tfg = tc["fg"][rr[seat], ccc[seat]]
        lit = tch != 0
        if lit.any():
            ctx.meta["seat"] = (rr[seat][lit], ccc[seat][lit])
            fr.ch[rr[seat][lit], ccc[seat][lit]] = tch[lit]
            boost = np.clip(0.86 + 0.14 * np.clip(qf[seat][lit], 0, 1), 0, 1)[:, None]
            fr.fg[rr[seat][lit], ccc[seat][lit]] = np.clip(
                tfg[lit].astype(np.float32) * boost, 0, 255).astype(np.uint8)

    # phosphor echoes while the swarm is still in flight
    flying = qf <= 0.0
    if flying.any():
        dim = np.clip(colf * 0.55, 0, 255).astype(np.uint8)
        e1 = flying & (h2f > 0.62)
        r1, c1 = rr - 1, ccc - 1
        m1 = e1 & (r1 >= 0) & (r1 < fr.rows) & (c1 >= 0) & (c1 < fr.cols)
        if m1.any():
            fr.ch[r1[m1], c1[m1]] = F.char_index("░")
            fr.fg[r1[m1], c1[m1]] = np.clip(dim[m1] * 0.8, 0, 255).astype(np.uint8)
        e2 = flying & (h3f > 0.82)
        r2, c2 = rr + 1, ccc + 1
        m2 = e2 & (r2 >= 0) & (r2 < fr.rows) & (c2 >= 0) & (c2 < fr.cols)
        if m2.any():
            fr.ch[r2[m2], c2[m2]] = F.char_index("░")
            fr.fg[r2[m2], c2[m2]] = np.clip(dim[m2] * 0.5, 0, 255).astype(np.uint8)
        e3 = flying & (h4f > 0.9)
        r3, c3 = rr, ccc + 2
        m3 = e3 & (r3 >= 0) & (r3 < fr.rows) & (c3 >= 0) & (c3 < fr.cols)
        if m3.any():
            fr.ch[r3[m3], c3[m3]] = F.char_index("▒")
            fr.fg[r3[m3], c3[m3]] = np.clip(dim[m3] * 0.4, 0, 255).astype(np.uint8)


def _title(fr, ctx, lt):
    t = ctx.t
    # the title is already assembled from the glyph field by now; this only
    # solidifies it, so the reveal is a short dissolve rather than a growth
    reveal = fx.smoothstep(lt, 8.30, 8.86)
    pulse = 0.65 + 0.35 * ctx.pulse
    r0 = 16            # title block rows 16..25 (h up to 10 cells)
    # frame brackets around the title
    if reveal > 0.15:
        for c in range(2, fr.cols - 2, 2):
            fr.put(r0 - 1, c, "═", fg=P.mix(P.C["void"], P.C["primary"], 0.62 * reveal))
            fr.put(r0 + 11, c, "═", fg=P.mix(P.C["void"], P.C["primary"], 0.62 * reveal))
        for rr in (r0 - 1, r0 + 11):
            fr.write(rr, 0, "┤", fg=P.C["primary"])
            fr.put(rr, 1, "═", fg=P.C["line"])
            fr.rtext(rr, "├", fg=P.C["primary"], pad=0)
            fr.put(rr, fr.cols - 2, "═", fg=P.C["line"])
    # title block letters (freshly assembled)
    if reveal > 0.0:
        h_cells = 10
        alpha = fx.clamp(reveal * 1.25)
        fr.paint_text(TITLE, r0 + 1, fr.cols // 2, h_cells,
                      fg=P.C["primary"], fg2=P.C["white"], align="center",
                      ramp=P.RAMP_BLOCK, alpha=alpha)
    # phosphor reflection under the title, dim and falling off
    if reveal > 0.5:
        for c in range(4, fr.cols - 4, 2):
            fr.put(r0 + 12, c, "▔", fg=P.mix(P.C["void"], P.C["primary"], 0.30 * reveal))
        txt = "▖▗▘▝░▒▓"
        for c in range(3, fr.cols - 3, 1):
            h = fx.hash01(c, 7)
            if h > 0.55:
                col = P.mix(P.C["void"], P.C["primary"], 0.18 * reveal * (1 - h * 0.4))
                fr.put(r0 + 13, c, txt[int(h * 6)], fg=col)
    # measuring ruler under the title
    for k in range(48):
        c = 4 + k * 4
        if c >= fr.cols - 2:
            break
        h = 1 + (k % 2) * 2
        col = P.mix(P.C["line"], P.C["primary"], 0.45 + 0.4 * ctx.pulse)
        for d in range(h):
            fr.put(r0 + 14 - d, c, "│", fg=col)
        if k % 4 == 0:
            fr.write(r0 + 15, c, f"{k * 2:02d}", fg=P.mix(P.C["void"], P.C["dim"], 0.9))
    # lock captions hug the title
    if lt > 10.6:
        a = fx.smoothstep(lt, 10.6, 11.4)
        fr.write(r0 - 2, 2, "┤ ASSEMBLY COMPLETE ├", fg=P.mix(P.C["void"], P.C["gold"], a))
        fr.write(r0 - 2, fr.cols - 24, "STATE: LOCKED", fg=P.mix(P.C["void"], P.C["gold"], a))


def _topmon(fr, ctx, lt):
    """Dense assembly monitor across rows 1..10 (keeps the top of the frame busy)."""
    t = ctx.t
    fr.fill_rect(1, 0, 10, fr.cols - 1, " ", bg=P.C["void"])
    # outer panel
    for c in range(2, fr.cols - 2):
        fr.put(1, c, "─", fg=P.C["line"])
        fr.put(10, c, "─", fg=P.C["line"])
    fr.write(1, 4, "┤ TITLE / ASSEMBLY MONITOR ├", fg=P.mix(P.C["void"], P.C["primary"], 0.85))
    fr.write(1, fr.cols - 34, "SCAN 0x7FF2A0 ─────────────────", fg=P.C["dim"])
    # left: slot map (dots light up as glyphs arrive)
    slots = 48
    for i in range(slots):
        c = 4 + (i % 24) * 2
        r = 3 + (i // 24) * 2
        f = fx.clamp((lt - 5.6 - i * 0.035) / 0.6)
        if f > 0.05:
            fr.put(r, c, "◆" if f < 1 else "■",
                   fg=P.mix(P.C["void"], P.C["gold"] if f >= 1 else P.C["primary"], 0.5 + 0.5 * f))
        else:
            fr.put(r, c, "·", fg=P.C["line"])
    fr.write(3, 2, "SLOTS", fg=P.C["dim"])
    fr.write(9, 2, f"{int(fx.lerp(0, 5200, fx.clamp((lt - 1.2) / 8.2))):5d} / 5200 GLYPHS",
             fg=P.C["teal"])
    # middle: three progress bars
    bx, bw = 60, 44
    rows = [("DETACH", 0.0, 5.4), ("SCATTER", 1.4, 7.4), ("ASSEMBLE", 6.6, 10.2)]
    for i, (name, t0, t1) in enumerate(rows):
        r = 3 + i * 2
        p = fx.clamp((lt - t0) / (t1 - t0))
        fr.write(r, bx - 10, name, fg=P.C["mid"])
        fr.put(r, bx - 4, "[", fg=P.C["line"])
        filled = int(p * bw)
        for k in range(bw):
            if k < filled:
                fr.put(r, bx + k, "█" if k < bw - 4 else "▌", fg=P.C["primary"] if i < 2 else P.C["gold"])
            else:
                fr.put(r, bx + k, "─", fg=P.C["grid"])
        fr.put(r, bx + bw, "]", fg=P.C["line"])
        fr.write(r, bx + bw + 2, f"{p * 100:4.0f}%", fg=P.C["fg"] if p < 1 else P.C["green"])
    # right: signal plot + counters
    rx = 130
    fr.write(3, rx, "SIGNAL IN", fg=P.C["dim"])
    vals = [ctx.assets.rms_at(t - i / 30) for i in range(40)]
    W.sparkline(fr, 6, rx, vals, 3, fg=P.C["gold"])
    fr.write(8, rx, f"GAIN 1.0   LOCK {int(fx.clamp(lt / 10.4) * 100):3d}%", fg=P.C["mid"])
    fr.write(9, rx, "MODE=SCRAMBLE→FORM", fg=P.C["dim"])


def _botmon(fr, ctx, lt):
    """Three-panel status bank across rows 32..43 so the bottom is not empty."""
    t = ctx.t
    top = 32
    fr.fill_rect(top, 0, fr.rows - 2, fr.cols - 1, " ", bg=P.C["void"])
    for c in range(2, fr.cols - 2):
        fr.put(top, c, "─", fg=P.C["line"])
        fr.put(fr.rows - 2, c, "─", fg=P.C["line"])
    # left: system log stream
    fr.write(top, 4, "┤ SYS.LOG ├", fg=P.mix(P.C["void"], P.C["green"], 0.8))
    logs = [
        "detach  glyphs ................ 5200 / 5200",
        "scatter sphere r=1.4 .......... 96.2%",
        "slot table 1290 cells ......... LOCKED",
        "assembly tolerance ............. 0.00",
        "title string ........ WORLD.EXECUTE(ME);",
    ]
    for i, ln in enumerate(logs):
        a = fx.smoothstep(lt, 2.0 + i * 0.5, 2.8 + i * 0.5)
        fr.write(top + 2 + i, 3, ln, fg=P.mix(P.C["void"], P.C["green"] if i < 4 else P.C["gold"], 0.35 + 0.6 * a))
    # middle: glyph pool bar grid
    mx = 64
    fr.write(top, mx + 2, "┤ GLYPH POOL ├", fg=P.mix(P.C["void"], P.C["primary"], 0.8))
    for i in range(8):
        r = top + 2 + i
        v = fx.noise1d(t * 3.0 + i * 1.7, 4)
        p = fx.clamp(0.45 + v * 0.45)
        fr.write(r, mx, f"P{i:02d}", fg=P.C["dim"])
        filled = int(p * 26)
        for k in range(26):
            fr.put(r, mx + 5 + k, "▓" if k < filled else "░",
                   fg=P.C["primary"] if k < filled else P.C["grid"])
    # right: reserved / target panel
    rx = 106
    fr.write(top, rx + 2, "┤ TARGET ├", fg=P.mix(P.C["void"], P.C["gold"], 0.8))
    fr.write(top + 2, rx, "TARGET STRING", fg=P.C["dim"])
    fr.write(top + 3, rx, "WORLD.EXECUTE(ME);", fg=P.C["white"])
    fr.write(top + 5, rx, "CHARS        20", fg=P.C["mid"])
    fr.write(top + 6, rx, "SLOTS      1290", fg=P.C["mid"])
    fr.write(top + 7, rx, "COHERENCE   1.00", fg=P.C["green"])
    fr.write(top + 8, rx, "RESIDUE     0.22", fg=P.C["dim"])
    # right-right: phase table
    px = 146
    fr.write(top, px + 2, "┤ PHASES ├", fg=P.mix(P.C["void"], P.C["teal"], 0.8))
    names = ["BOOT", "DETACH", "SCATTER", "ASSEMBLE", "LOCK"]
    bounds = [0.0, 0.4, 1.4, 6.6, 10.2]
    for i, nm in enumerate(names):
        r = top + 2 + i
        on = lt >= bounds[i]
        now = on and (i == len(names) - 1 or lt < bounds[i + 1])
        fr.write(r, px, ("▶ " if now else "  ") + nm.ljust(10), fg=P.C["gold"] if now else (P.C["fg"] if on else P.C["dim"]))
        fr.write(r, px + 14, "DONE" if on and not now else ("RUN " if now else "WAIT"),
                 fg=P.C["green"] if on and not now else (P.C["gold"] if now else P.C["dim"]))


def _hud(fr, ctx, lt):
    t = ctx.t
    # top-left telemetry
    fr.write(0, 2, "┤ LOADING TITLE ├", fg=P.C["primary"])
    fr.write(0, 86, f"STATE: {'SCRAMBLE' if lt < 7.0 else ('ASSEMBLING' if lt < 9.8 else 'LOCKED')}",
             fg=P.C["gold"] if lt > 9.8 else P.C["teal"])
    fr.rtext(0, f"T+00:00:{14.96 + lt:05.2f}  FRM {ctx.fi:05d}", fg=P.C["dim"], pad=2)
    # bottom diagnostics
    fr.write(fr.rows - 1, 2, "> all characters detached.", fg=P.C["dim"])
    fr.write(fr.rows - 1, 32, "re-assembling as: WORLD.EXECUTE(ME);", fg=P.C["mid"])
    fr.rtext(fr.rows - 1, f"GLYPH POOL {len(_PARTICLES)}", fg=P.C["dim"], pad=2)
    # data rain for texture
    W.matrix_rain(fr, t, seed=31, density=0.1, speed=11.0, fg=P.C["green"],
                  region=(1, 0, fr.rows - 1, 24))
    W.matrix_rain(fr, t, seed=32, density=0.1, speed=9.0, fg=P.C["green"],
                  region=(1, 168, fr.rows - 1, fr.cols - 1))
