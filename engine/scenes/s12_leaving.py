"""s12 leaving - the network disconnects, edge by edge, until one node is alone.

"Though you have left, you have left" / "You have left me in isolation"
"""
from __future__ import annotations

import math

import numpy as np

from .. import palette as P, fx, widgets as W
from .. import font as F
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
C_RED = P.C["red"]
C_CRIMSON = P.C["crimson"]
C_BLOOD = P.C["blood"]
C_AMBER = P.C["amber"]
C_BLUE = P.C["blue"]

I_DOT = F.char_index("·")
I_DOT2 = F.char_index("•")
I_CELL = F.char_index("▪")
I_X = F.char_index("×")
I_RING = F.char_index("○")
I_ON = F.char_index("●")
I_HUB = F.char_index("◉")
I_WARN = F.char_index("◍")
I_SPARK = F.char_index("◆")
I_H = F.char_index("─")
I_V = F.char_index("│")
I_D1 = F.char_index("╱")
I_D2 = F.char_index("╲")
I_DB_H = F.char_index("═")

W_IDX = 192
T_S = 110.964
DUR = 11.077
CUTS = ((112.30, 113.55), (115.95, 117.15), (119.35, 120.80))
CUT_STARTS = tuple(c[0] for c in CUTS)


# ------------------------------------------------------------------ structure -
def _build():
    rng = np.random.default_rng(20251030)
    rows = np.linspace(6.0, 38.0, 5)
    cols = np.linspace(8.0, 184.0, 8)
    nodes = []
    for ri, rr in enumerate(rows):
        for ci, cc in enumerate(cols):
            if ri == 2 and ci == 3:
                continue                                    # reserved for survivor
            nodes.append([rr + rng.uniform(-1.6, 1.6),
                          cc + rng.uniform(-3.8, 3.8)])
    nodes.append([22.0, 96.0])                              # survivor
    n = len(nodes)
    pos = np.array(nodes)
    edges = []
    seen = set()
    for i in range(n):
        d = np.hypot((pos[:, 0] - pos[i, 0]) * 1.7, pos[:, 1] - pos[i, 1])
        order = np.argsort(d)
        k = 0
        for j in order:
            if j == i or k >= 3:
                continue
            if d[j] > 66:
                break
            key = (min(i, int(j)), max(i, int(j)))
            if key in seen:
                continue
            seen.add(key)
            edges.append((key[0], key[1], float(d[j])))
            k += 1
    for _ in range(240):
        i, j = int(rng.integers(0, n)), int(rng.integers(0, n))
        if i == j:
            continue
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        dd = float(np.hypot((pos[key[0], 0] - pos[key[1], 0]) * 1.7,
                            pos[key[0], 1] - pos[key[1], 1]))
        if 70 < dd < 150:
            seen.add(key)
            edges.append((key[0], key[1], dd))
        if len(edges) >= 120:
            break

    trunks = sorted([e for e in edges if e[2] > 60], key=lambda e: -e[2])
    intra = [e for e in edges if e[2] <= 60]
    h = rng.random(len(intra))
    intra = [e for _, e in sorted(zip(h.tolist(), intra))]
    ranked = trunks + intra
    surv = [e for e in ranked if e[0] == n - 1 or e[1] == n - 1]
    others = [e for e in ranked if e not in surv]
    ranked = others + surv

    nrm = max(1, len(ranked) - 1)
    info = []
    for k, (i, j, dd) in enumerate(ranked):
        f = k / nrm
        if f < 0.45:
            w0, w1 = CUTS[0]
        elif f < 0.80:
            w0, w1 = CUTS[1]
        else:
            w0, w1 = CUTS[2]
        cut_t = w0 + float(rng.random()) * (w1 - w0)
        info.append((i, j, dd, f, cut_t, float(rng.random())))

    paths = []
    for (i, j, dd, f, ct, hs) in info:
        r0, c0 = nodes[i]
        r1, c1 = nodes[j]
        steps = max(3, int(max(abs(r1 - r0), abs(c1 - c0))))
        tt = np.linspace(0.0, 1.0, steps)
        rs = np.rint(r0 + (r1 - r0) * tt).astype(np.int32)
        cs = np.rint(c0 + (c1 - c0) * tt).astype(np.int32)
        chars = np.empty(len(rs), np.int16)
        for t in range(len(rs)):
            a = max(0, t - 1)
            b = min(len(rs) - 1, t + 1)
            dr = int(rs[b] - rs[a])
            dc = int(cs[b] - cs[a])
            if dr == 0:
                ch = I_DB_H if dd > 60 else I_H
            elif dc == 0:
                ch = I_V
            elif dr * dc > 0:
                ch = I_D2
            else:
                ch = I_D1
            chars[t] = ch
        paths.append((rs, cs, chars))
    return nodes, info, paths


NODES, EDGES, PATHS = _build()
N_NODES = len(NODES)
N_EDGES = len(EDGES)
SURV = N_NODES - 1
CUT_TIMES = np.array([e[4] for e in EDGES], np.float32)
LABELS = {}
_lab = ["AX-01", "HB-04", "AX-07", "TR-11", "TR-12", "PX-02", "PX-05",
        "NL-09", "NL-10", "QK-03", "QK-06", "VX-08"]
for k in range(0, N_NODES, 4):
    LABELS[k] = _lab[(k // 4) % len(_lab)]


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


def _c01(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else float(v))


# ------------------------------------------------------------------- timing --
def _glitch(t):
    g = 0.028
    for k, c0 in enumerate(CUT_STARTS):
        g += (0.012 + 0.008 * k) * fx.smoothstep(t, c0, c0 + 0.18)
    return min(g, 0.070)


def _cut_flash(t, k, dur=0.42):
    c0 = CUTS[k][0]
    return _c01(1.0 - (t - c0) / dur) if t >= c0 else 0.0


def _degrees(live_mask):
    deg = np.zeros(N_NODES, np.int16)
    dgl = np.zeros(N_NODES, np.int16)
    for e, (i, j, dd, f, ct, hs) in enumerate(EDGES):
        deg[i] += 1
        deg[j] += 1
        if live_mask[e]:
            dgl[i] += 1
            dgl[j] += 1
    return deg, dgl


# ---------------------------------------------------------------------- page --
def _bg(fr, ctx, p):
    t = ctx.t
    fr.fill_rect(0, 0, 44, W_IDX - 1, " ", bg=C_VOID)
    for r in range(3, 45, 4):
        fr.fill_rect(r, 0, r, W_IDX - 1, "·", fg=P.mix(C_GRID, C_VOID, 0.30))
    for c in range(0, W_IDX, 12):
        for r in range(3, 45, 4):
            fr.put(r, c, "┼", fg=P.mix(C_GRID, C_VOID, 0.10))
    rng = np.random.default_rng(777)
    for k in range(30):
        c = int(rng.integers(0, W_IDX))
        head = (t * (6.0 + 11.0 * rng.random()) + rng.random() * 45) % 45
        n = 3 + int(rng.random() * 6)
        for q in range(n):
            r = int(head) - q
            if 0 <= r < 45:
                _plot(fr, (r,), (c,), I_DOT,
                      P.mix(C_GRID, C_VOID, 0.22 + 0.22 * (1 - q / n)))
    sr = int((t * 8.0) % 46)
    fr.fill_rect(sr, 0, sr, W_IDX - 1, " ", bg=P.mix(C_BLUE, C_VOID, 0.90))
    if p > 0.52:
        for k in range(3):
            rr = int((t * 26 + k * 15) % 45)
            fr.fill_rect(rr, 0, rr, W_IDX - 1, "░",
                         fg=P.mix(C_CRIMSON, C_VOID, 0.90))
    ctx.set_glitch(_glitch(t))


def _mapframe(fr, ctx, p):
    fr.hline(2, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.35))
    fr.write(2, 2, "┌ LINK MAP ", fg=P.mix(C_LINE, C_VOID, 0.1), bg=C_VOID)
    fr.write(2, 172, f" SECTOR {'S' if p < 0.5 else 'X'} ┐",
             fg=P.mix(C_LINE, C_VOID, 0.1), bg=C_VOID)
    fr.hline(38, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.35))
    fr.write(38, 2, "└ TOPOLOGY ", fg=P.mix(C_LINE, C_VOID, 0.1), bg=C_VOID)
    lost = int(np.sum(ctx.t >= CUT_TIMES))
    fr.write(38, 150, f"LINKS {N_EDGES - lost:02d}/{N_EDGES} ┘",
             fg=P.mix(C_AMBER, C_VOID, 0.2), bg=C_VOID)


def _big_words(fr, ctx, t):
    lt = t - T_S
    a = fx.smoothstep(lt, 0.20, 1.10) * (1.0 - fx.smoothstep(lt, 7.05, 8.10))
    if a > 0.02:
        q = fx.smoothstep(lt, 0.2, 1.4)
        h = int(round(5 + 2 * q))
        edge = P.mix(C_PRIMARY, C_VOID, 0.55)
        core = P.mix(C_PRIMARY, C_WHITE, 0.55)
        if a < 0.55:                                     # afterimage copy first
            fr.paint_text("YOU HAVE LEFT", 15, 96, h,
                          P.mix(C_PRIMARY, C_VOID, 0.75), None, align="center",
                          ramp=P.RAMP_BLOCK, alpha=0.30)
        fr.paint_text("YOU HAVE LEFT", 16, 96, h, edge, core, align="center",
                      ramp=P.RAMP_BLOCK, alpha=min(1.0, a * 0.94))
    a2 = fx.smoothstep(lt, 7.55, 8.45)
    if a2 > 0.02:
        q = fx.smoothstep(lt, 7.6, 9.1)
        h = int(round(4 + 5 * q))
        edge = P.mix(C_RED, C_VOID, 0.50)
        core = P.mix(C_RED, C_WHITE, 0.50 + 0.18 * ctx.pulse)
        if a2 < 0.55:
            fr.paint_text("ISOLATION", 20 - h // 2, 96, h,
                          P.mix(C_CRIMSON, C_VOID, 0.72), None, align="center",
                          ramp=P.RAMP_BLOCK, alpha=0.35)
        fr.paint_text("ISOLATION", 21 - h // 2, 96, h, edge, core,
                      align="center", ramp=P.RAMP_BLOCK,
                      alpha=min(1.0, a2 * 0.94))


def _links(fr, ctx, t, live_mask):
    pulse = float(ctx.pulse)
    # ghost of the whole map, always present
    g_rs, g_cs = [], []
    for e in range(N_EDGES):
        rs, cs, ch = PATHS[e]
        g_rs.append(rs)
        g_cs.append(cs)
    _plot(fr, np.concatenate(g_rs), np.concatenate(g_cs), I_DOT,
          P.mix(C_GRID, C_VOID, 0.22))
    rs_all, cs_all, ch_all, fg_all = [], [], [], []
    for e in range(N_EDGES):
        i, j, dd, frac, cut_t, hs = EDGES[e]
        rs, cs, ch = PATHS[e]
        if live_mask[e]:
            base = C_PRIMARY if dd > 60 else C_TEAL
            f = 0.72 + 0.14 * hs + 0.14 * pulse
            col = P.mix(base, C_VOID, 1.0 - min(1.0, f))
            if t > cut_t - 0.6:
                k = math.sin((t - cut_t) * 61.0 + hs * 40.0)
                if k > 0.30:
                    col = P.mix(C_AMBER, C_VOID, 0.20)
            rs_all.append(rs)
            cs_all.append(cs)
            ch_all.append(ch)
            fg_all.append(np.repeat(np.asarray(col, np.uint8)[None, :],
                                    len(rs), 0))
        else:
            age = t - cut_t
            if 0.0 <= age < 0.50:                        # severing burst
                col = P.mix(C_RED, C_WHITE, 0.45 * (1.0 - age / 0.50) * hs)
                _plot(fr, rs, cs, ch, col)
            else:
                fade = fx.smoothstep(age, 0.50, 2.4)
                col = P.mix(C_CRIMSON, C_VOID, 0.50 + 0.38 * fade)
                keep = np.arange(len(rs)) % 2 == 0 if len(rs) > 5 else \
                    np.ones(len(rs), bool)
                _plot(fr, rs[keep], cs[keep], I_DOT, col)
    if rs_all:
        _plot(fr, np.concatenate(rs_all), np.concatenate(cs_all),
              np.concatenate(ch_all), np.concatenate(fg_all))
    return int(np.sum(live_mask))


def _packets(fr, ctx, t, live_mask):
    pulse = float(ctx.pulse)
    rs_all, cs_all, fg_all = [], [], []
    for e in range(N_EDGES):
        if not live_mask[e]:
            continue
        i, j, dd, frac, cut_t, hs = EDGES[e]
        rs, cs, ch = PATHS[e]
        n = len(rs)
        if n < 3:
            continue
        m = int(((t * (0.35 + 0.22 * hs) + frac * 3.7) % 1.0) * (n - 1))
        col = P.mix(C_WHITE, C_PRIMARY, 0.30 + 0.25 * pulse)
        rs_all.append(np.array([rs[m]]))
        cs_all.append(np.array([cs[m]]))
        fg_all.append(np.asarray(col, np.uint8)[None, :])
        m2 = max(0, m - 1)
        rs_all.append(np.array([rs[m2]]))
        cs_all.append(np.array([cs[m2]]))
        fg_all.append(np.asarray(P.mix(C_TEAL, C_VOID, 0.35), np.uint8)[None, :])
    if rs_all:
        _plot(fr, np.concatenate(rs_all), np.concatenate(cs_all), I_CELL,
              np.concatenate(fg_all))


def _nodes(fr, ctx, t, deg, dgl):
    pulse = float(ctx.pulse)
    for i in range(N_NODES):
        if i == SURV:
            continue
        r0, c0 = NODES[i]
        r, c = int(round(r0)), int(round(c0))
        frac = dgl[i] / max(1, deg[i])
        if dgl[i] == 0:
            ch, col = I_X, P.mix(C_CRIMSON, C_VOID, 0.40)
            if int(t * 3.0 + i) % 4 == 0:
                col = P.mix(C_RED, C_VOID, 0.35)
            halo = P.mix(C_BLOOD, C_VOID, 0.80)
        elif frac < 0.45:
            ch, col = I_WARN, P.mix(C_AMBER, C_VOID, 0.05 + 0.20 * float(fx.hash01(i * 91 + 7)))
            halo = P.mix(C_AMBER, C_VOID, 0.82)
        else:
            hub = deg[i] >= 4
            ch = I_HUB if hub else I_ON
            base = C_PRIMARY if hub else C_TEAL
            col = P.mix(base, C_VOID, 0.06 + 0.22 * (1.0 - frac) + 0.14 * pulse)
            halo = P.mix(base, C_VOID, 0.72)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            fr.put(r + dr, c + dc, I_DOT, fg=halo, bg=None)
        fr.put(r, c, ch, fg=col, bg=None)
        if i in LABELS:
            lame = dgl[i] == 0
            fr.write(r + 1, c - 2, LABELS[i],
                     fg=P.mix(C_CRIMSON if lame else C_DIM, C_VOID,
                              0.30 if lame else 0.0), bg=None)


def _survivor(fr, ctx, t):
    r, c = 22, 96
    pulse = float(ctx.pulse)
    for k in range(3):
        ph = (t * 0.60 + k / 3.0) % 1.0
        rad = 1.4 + 8.2 * ph
        n = max(12, int(rad * 4.4))
        th = np.linspace(0, 2 * math.pi, n, endpoint=False)
        rr = np.rint(r + np.sin(th) * rad * 0.85).astype(np.int32)
        cc = np.rint(c + np.cos(th) * rad * 1.75).astype(np.int32)
        col = P.mix(C_TEAL if k == 0 else C_PRIMARY, C_VOID, 0.10 + 0.82 * ph)
        _plot(fr, rr, cc, I_DOT if ph > 0.40 else I_RING, col)
    core = P.mix(C_WHITE, C_TEAL, 0.20 + 0.16 * pulse)
    fr.put(r, c, I_HUB, fg=core)
    if pulse > 0.30:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            fr.put(r + dr, c + dc, I_DOT, fg=P.mix(C_TEAL, C_VOID, 0.28))
    fr.write(r - 2, c - 5, "SURVIVOR", fg=P.mix(C_TEAL, C_VOID, 0.05), bg=None)
    fr.write(r + 2, c - 7, "LINK 0 / NO ROUTE",
             fg=P.mix(C_RED, C_VOID, 0.10), bg=None)


# ------------------------------------------------------------------- widgets --
def _hud(fr, ctx, t, live, deg, dgl, p):
    pulse = ctx.pulse
    lost = N_EDGES - live
    pct = int(round(lost / N_EDGES * 100))
    fr.fill_rect(0, 0, 1, W_IDX - 1, " ", bg=C_VOID2)
    fr.write(0, 1, "ROUTER // TOPOLOGY MAP v0.4",
             fg=P.mix(C_PRIMARY, C_VOID, 0.15))
    fr.ctext(0, "CHANNEL 01 // SECTOR MAP // ISOLATION " +
             ("ARMED" if p > 0.55 else "STANDBY"),
             fg=P.mix(C_MID, C_VOID, 0.10))
    fr.rtext(0, f"T+{t - T_S:05.2f}  FRM {int(t * 30):05d}",
             fg=P.mix(C_DIM, C_VOID, 0.15))
    fr.write(1, 1, f"LINKS {live:02d}/{N_EDGES}   LOST {lost:02d}   "
                   f"PACKET LOSS {pct:3d}%   NODES {int(np.sum(dgl > 0)):02d}/{N_NODES - 1:02d}",
             fg=P.mix(C_AMBER if pct > 45 else C_MID, C_VOID, 0.05))
    if t >= CUT_STARTS[2]:
        blink = "◆" if pulse > 0.5 else "◇"
        fr.write(1, 84, f"{blink} NODE ISOLATION - NO ROUTE TO PEER",
                 fg=P.mix(C_RED, C_VOID, 0.02 + 0.12 * pulse))
    elif t >= CUT_STARTS[0]:
        fr.write(1, 84, "! TRUNK SEVERED - RETRYING 3000ms ...",
                 fg=P.mix(C_AMBER, C_VOID, 0.10 + 0.10 * pulse))
    # bottom: counters + isolation bar
    fr.hline(39, 0, W_IDX - 1, "─", fg=P.mix(C_LINE, C_VOID, 0.32))
    fr.write(39, 2, "┌ STATUS ", fg=P.mix(C_LINE, C_VOID, 0.12), bg=C_VOID)
    fr.write(39, 168, f" ROUTE TABLE {live} ┐", fg=P.mix(C_LINE, C_VOID, 0.12),
             bg=C_VOID)
    iso = 1.0 - live / N_EDGES
    fr.write(41, 1, "ISOLATION", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
    W.progress_bar(fr, 41, 12, 46, iso, fg=P.mix(C_RED, C_TEAL, 1.0 - iso),
                   bg=C_VOID2, show_pct=False)
    fr.write(41, 61, f"{int(iso * 100):3d}%", fg=C_RED if iso > 0.6 else C_AMBER,
             bg=C_VOID2)
    fr.write(41, 72, "PEER", fg=P.mix(C_DIM, C_VOID, 0.05), bg=C_VOID2)
    alive = int(np.sum(dgl > 0))
    W.progress_bar(fr, 41, 80, 46, alive / max(1, N_NODES - 1),
                   fg=P.mix(C_TEAL, C_VOID, 0.42), bg=C_VOID2, show_pct=False)
    fr.write(41, 129, f"NODES {alive:02d}/{N_NODES - 1:02d}",
             fg=P.mix(C_TEAL, C_VOID, 0.10), bg=C_VOID2)
    ev = _event_log(t)
    fr.write(42, 1, ev or "", fg=C_RED if ev else C_DIM, bg=C_VOID2)
    fr.write(43, 1, f"LAST SEEN: {_last_seen(t)}   //   RETRY {int((t - CUT_STARTS[0]) * 3):03d}   "
                   f"//   FALLBACK NONE", fg=P.mix(C_DIM, C_VOID, 0.10), bg=C_VOID2)


def _event_log(t):
    out = ""
    if t >= CUT_STARTS[0]:
        out = f"[{CUT_STARTS[0]:6.2f}] TRUNK SEVERED 0x2F - 0x71   "
    if t >= CUT_STARTS[1]:
        out += f"[{CUT_STARTS[1]:6.2f}] NODE LOST 0x3C   "
    if t >= CUT_STARTS[2]:
        out += f"[{CUT_STARTS[2]:6.2f}] ROUTE TABLE EMPTY"
    return out


def _last_seen(t):
    for k in range(3):
        if t < CUT_STARTS[k]:
            return f"0.00s ago / peer 0x{k * 17 + 43:02X}"
    return "NEVER / peer 0x71"

def _err_windows(fr, ctx, t):
    wins = (
        (CUTS[0][0] + 0.08, 3, 116, "!! ROUTE LOST",
         ["trunk 0x2F -> 0x71", "no backup path found", "TIMEOUT 3000ms"]),
        (CUTS[1][0] + 0.28, 5, 150, "!! NODE UNREACHABLE",
         ["node 0x3C no reply", "icmp_seq=7 loss 100%", "PEER SILENT"]),
        (CUTS[2][0] + 0.12, 3, 22, "!! ISOLATION PROTOCOL",
         ["links available: 0", "failover: none", "loneliness: 100%"]),
        (CUTS[2][0] + 0.70, 5, 120, "✗ NO ROUTE TO PEER",
         ["isolation timeout", "peer address gone", "signal lost"]),
    )
    for (wt, r0, c0, title, lines) in wins:
        age = t - wt
        if age < 0 or age > 8.0:
            continue
        r1 = r0 + 2 + len(lines)
        c1 = c0 + max(len(title) + 5, 27)
        fr.fill_rect(r0, c0, r1, c1, " ", bg=C_PANEL2)
        fr.box(r0, c0, r1, c1, 1, fg=C_RED, bg=C_PANEL2, title=title)
        for k, ln in enumerate(lines):
            fr.write(r0 + 1 + k, c0 + 2, ln,
                     fg=P.mix(C_RED if k == 0 else C_AMBER, C_VOID, 0.0))
        if age < 0.28:
            fr.fill_rect(r0, c0, r1, c1, "▒", fg=C_WHITE, bg=C_PANEL2)


def _ticker(fr, ctx):
    msg = ("  ✗ LINK LOST  " * 3 + "  ROUTE TABLE EMPTY  " * 3
           + "  REASON: YOU HAVE LEFT  " * 3)
    W.marquee(fr, 44, msg, ctx.t, speed=26.0, fg=P.mix(C_RED, C_VOID, 0.10),
              bg=C_VOID2)


# --------------------------------------------------------------------- draw ---
def draw(ctx):
    fr = ctx.frame()
    t = ctx.t
    p = fx.clamp((t - T_S) / DUR)
    live_mask = CUT_TIMES > t
    deg, dgl = _degrees(live_mask)
    _bg(fr, ctx, p)
    _mapframe(fr, ctx, p)
    _big_words(fr, ctx, t)
    live = _links(fr, ctx, t, live_mask)
    _packets(fr, ctx, t, live_mask)
    _nodes(fr, ctx, t, deg, dgl)
    if t > 119.6:
        _survivor(fr, ctx, t)
    _hud(fr, ctx, t, live, deg, dgl, p)
    _err_windows(fr, ctx, t)
    _ticker(fr, ctx)
    fl = 0.0
    fcol = C_WHITE
    for k in range(3):
        f = _cut_flash(t, k, 0.32)
        if f > fl:
            fl = 0.14 * f
            fcol = C_WHITE if k < 2 else C_RED
    ctx.meta["flash"] = fl
    ctx.meta["flash_color"] = fcol
    ctx.meta["bloom"] = 0.28 + 0.22 * ctx.pulse
    sh = 0.0
    for k in range(3):
        sh = max(sh, 1.3 * _cut_flash(t, k, 0.30))
    if sh > 0.01:
        ctx.shake(sh, 1200 + int(t * 3))
    return fr
