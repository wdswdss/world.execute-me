"""s15_count - EXECUTION x4 build-up, then the multilingual count main frame.

147.880 / 151.572 / 155.264   "Execution, execution, execution, execution" x3
  -> one EXECUTION stamp every two beats: 12 stamped receipts fill the stage,
     the hero word growing from 5 to 9 cells tall as the total climbs.
158.957  count line becomes THE MAIN FRAME: EIN / DOS / TROIS / NE / FEM / LIU
  each huge on its own beat with language + index UI, previous numbers flying
  into the bottom strip.
161.727  "execution" slams the whole counting frame flat.

Shared drawing helpers live here (rule / edges / panel / big / dense_bg) and
are reused by the other scene-D modules.
"""
from __future__ import annotations

import math

import numpy as np

from .. import fx
from .. import font as F
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

T0, T1 = 147.880, 162.650
STAMP_STEP = 0.9230769
N_STAMPS = 12
COUNT_T0 = TL.COUNT_WORDS[0][3]      # 158.957
EXEC_SLAM = TL.COUNT_EXECUTION       # 161.727
FULL_WORD_STAMPS = (0, 5, 11)         # only these keep the full-screen EXECUTION

LANGS = ["DE", "ES", "FR", "KO", "PT", "ZH"]
LANG_NAMES = ["GERMAN", "SPANISH", "FRENCH", "KOREAN", "PORTUGUESE", "CHINESE"]
NUM_COLS = [P.C["primary"], P.C["teal"], P.C["gold"], P.C["magenta"],
            P.C["violet"], P.C["green"]]
LINE_ACCENT = [P.C["primary"], P.C["gold"], P.C["crimson"]]

CARD_W = 30
CARD_H = 8


def mix(a, b, f):
    """Fast tuple colour mix (P.mix is numpy-backed; too slow inside loops)."""
    f = 0.0 if f < 0.0 else (1.0 if f > 1.0 else f)
    return (int(a[0] + (b[0] - a[0]) * f),
            int(a[1] + (b[1] - a[1]) * f),
            int(a[2] + (b[2] - a[2]) * f))


# ===========================================================================
# shared helpers (also imported by s16/s17/s18)
# ===========================================================================
def heart_fill(w_px, h_px, holes=(), dents=()):
    """Delegates to engine.art so every heart in the MV shares one silhouette."""
    from engine import art as _A
    return _A.heart_fill(w_px, h_px, holes=holes, dents=dents)

def rule(fr, r, fg=None, step=12, ch="─"):
    """Full-width rule with junction ticks every `step` cols."""
    fg = fg or P.C["line"]
    for c in range(fr.cols):
        fr.put(r, c, "┼" if c % step == 0 else ch, fg=fg)


def edges(fr, fg=None):
    """Corner brackets; drawn under the status rows (call AFTER content)."""
    fg = fg or P.C["line"]
    d = mix(P.C["void"], fg, 0.55)
    for (r, c, dr, dc, corner) in (
            (0, 0, 1, 1, "┌"), (0, fr.cols - 1, 1, -1, "┐"),
            (fr.rows - 1, 0, -1, 1, "└"), (fr.rows - 1, fr.cols - 1, -1, -1, "┘")):
        fr.put(r, c, corner, fg=d)
        for k in range(1, 5):
            fr.put(r, c + dc * k, "─", fg=d)
            fr.put(r + dr * k, c, "│", fg=d)


def panel(fr, r0, c0, r1, c1, title=None, fg=None, bg=None, style=1, fill=True):
    """Panel background + border (+ optional title). Small text goes on top."""
    fg = fg or P.C["line"]
    bg = bg or P.C["void"]
    if fill:
        fr.fill_rect(r0, c0, r1, c1, " ", bg=bg)
    fr.box(r0, c0, r1, c1, style, fg=fg, bg=bg)
    if title:
        fr.write(r0, c0 + 2, f"┤ {title} ├", fg=P.C["primary"])
        fr.write(r0, c0 + 2, "┤", fg=fg)
    return fr


def big(fr, text, r0, c0, h, fg, fg2=None, align="center", echo=0,
        echo_fg=None, alpha=1.0):
    """paint_text with CRT after-images; echoes always keep a dark fg2."""
    fg2 = fg2 if fg2 is not None else P.C["white"]
    if echo:
        ec = echo_fg or P.dark(fg, 0.6)
        fr.paint_text(text, r0 - echo, c0 - echo * 2, h, fg=ec, fg2=ec,
                      align=align, alpha=alpha)
        fr.paint_text(text, r0 + echo, c0 + echo * 2, h,
                      fg=P.dark(ec, 0.5), fg2=P.dark(ec, 0.5),
                      align=align, alpha=alpha)
    return fr.paint_text(text, r0, c0, h, fg=fg, fg2=fg2, align=align,
                         alpha=alpha)


def dense_bg(fr, ctx, seed=41, fg=None, hot=0.0, base=None):
    """Layer-0 background: base tint, dot lattice, scrolling data, sweep."""
    t = ctx.t
    fg = fg or P.C["cyan2"]
    if base is None:
        base = mix(P.C["void"], P.C["blood"], 0.02 + 0.10 * hot)
    fr.fill_rect(0, 0, fr.rows - 1, fr.cols - 1, " ", bg=base)
    for r in range(1, fr.rows, 3):
        for c in range((r & 1) * 2, fr.cols, 4):
            fr.put(r, c, "·", fg=mix(P.C["void"], P.C["line"], 0.5))
    for j, c in enumerate(range(1, 27, 5)):
        W.data_column(fr, 0, c, fr.rows, t, seed=seed + j,
                      speed=2.6 + j * 0.9, fg=mix(P.C["void"], fg, 0.55))
    for j, c in enumerate(range(fr.cols - 26, fr.cols - 1, 5)):
        W.data_column(fr, 0, c, fr.rows, t, seed=seed + 40 + j,
                      speed=3.2 - j * 0.35, fg=mix(P.C["void"], fg, 0.45))
    W.matrix_rain(fr, t, seed=seed + 7, density=0.14, speed=5.5,
                  fg=mix(P.C["void"], fg, 0.7),
                  region=(0, 30, fr.rows - 1, fr.cols - 31))
    for off, sp in ((0.0, 11.0), (24.0, 7.0)):
        sy = int((t * sp + off) % (fr.rows + 16)) - 8
        if 0 <= sy < fr.rows:
            for c in range(fr.cols):
                if fr.get(sy, c) in (" ", "·"):
                    fr.put(sy, c, "─", fg=mix(P.C["void"], fg, 0.45))


# ===========================================================================
# main entry
# ===========================================================================
def draw(ctx):
    fr = ctx.frame()
    if ctx.t < COUNT_T0:
        _build_phase(fr, ctx)
    else:
        _count_phase(fr, ctx)
    _bottom_status(fr, ctx)
    edges(fr, P.C["line"] if ctx.t < COUNT_T0 else P.C["teal"])
    return fr


def _bottom_status(fr, ctx):
    t = ctx.t
    accent = P.C["teal"] if t >= COUNT_T0 else P.C["crimson"]
    fr.write(44, 7, "┤ STAGE 45x192 ├", fg=accent)
    fr.write(44, 24, "ASCII // BOX-DRAWING ONLY", fg=P.C["dim"])
    fr.write(44, 52, f"SCENE COUNT  {T0:.3f} - {T1:.3f}", fg=P.C["mid"])
    fr.write(44, 84, f"FRAME {t:9.3f}", fg=P.C["fg"])
    fr.write(44, 106, f"BEAT {ctx.beat_i:03d}.{int(ctx.beat_p * 100):02d}", fg=accent)
    fr.write(44, 126, f"BAR {ctx.bar_i:03d}.{int(ctx.bar_p * 100):02d}", fg=P.C["mid"])
    fr.write(44, 146, "NEXT: ONLY EXECUTION", fg=P.C["red"])
    fr.rtext(44, f"RC=0  RMS={ctx.rms:4.2f}  Z={ctx.local:6.2f}",
             fg=P.C["dim"], pad=6)


# ===========================================================================
# phase A - twelve EXECUTION stamps
# ===========================================================================
def _card_row(k):
    return 2 if k < 6 else 36


def _card_col(k):
    return 2 + (k if k < 6 else k - 6) * 31


def _build_phase(fr, ctx):
    t = ctx.t
    k = int((t - T0) / STAMP_STEP)
    k = max(0, min(N_STAMPS - 1, k))
    age = t - (T0 + k * STAMP_STEP)
    esc = k / float(N_STAMPS - 1)
    dense_bg(fr, ctx, seed=41, fg=P.C["cyan2"], hot=0.15 + 0.85 * esc)
    _status_top(fr, ctx, k, esc)
    _hero(fr, ctx, k, age, esc)
    for kk in range(N_STAMPS):
        _card(fr, kk, k, age)
    _impact_row(fr, ctx, k, esc)
    _ladder(fr, ctx, k, esc)
    _lines_meter(fr, ctx, k, esc)
    _log_strip(fr, ctx, k)
    # per-stamp impact
    if age < 0.18:
        amp = 1.0 - fx.clamp(age / 0.18)
        ctx.set_glitch((0.05 + 0.16 * esc) * amp)
        ctx.meta["flash"] = 0.18 * amp * (0.35 + 0.65 * esc)
        ctx.meta["flash_color"] = P.C["crimson"] if esc > 0.5 else P.C["white"]
        ctx.shake(2 + 4 * esc)
    else:
        ctx.set_glitch(0.02 + 0.05 * esc)
    ctx.meta["bloom"] = 0.30 + 0.12 * esc


def _status_top(fr, ctx, k, esc):
    line_i, stamp_i = k // 4, k % 4
    accent = LINE_ACCENT[min(2, line_i)]
    fr.write(0, 7, "┤ EXECUTION SEQUENCE ├", fg=P.C["primary"])
    fr.write(0, 30, "// BRIDGE SOLO // STAMP LOOP", fg=P.C["dim"])
    fr.write(0, 60, f"LINE {line_i + 1}/3", fg=accent)
    fr.write(0, 72, f"STAMP {stamp_i + 1}/4", fg=P.C["fg"])
    fr.write(0, 86, f"TOTAL {k + 1:02d}/{N_STAMPS}", fg=P.C["white"])
    fr.write(0, 105, "MODE: EXECUTE", fg=P.C["red"])
    fr.write(0, 123, f"T {ctx.t:8.3f}", fg=P.C["dim"])
    fr.rtext(0, "rc=0  SIG=OK  PRIO=MAX", fg=P.C["dim"], pad=6)
    rule(fr, 1, fg=mix(P.C["void"], P.C["line"], 0.8), step=12)


def _hero(fr, ctx, k, age, esc):
    t = ctx.t
    line_i, stamp_i = k // 4, k % 4
    base_h = 5 + int(round(esc * 4))          # 5 -> 9 over the build-up
    p = fx.clamp(age / 0.14)
    h = min(10, base_h + int(round(2 * (1.0 - fx.ease_out(p)))))
    r0 = 12
    br0, br1 = r0 - 1, r0 + base_h + 1
    accent = LINE_ACCENT[min(2, line_i)]
    fr.fill_rect(br0, 2, br1, 189, " ",
                 bg=mix(P.C["void"], P.C["blood"], 0.10 + 0.18 * esc))
    fr.hline(br0, 2, 189, "═", fg=mix(P.C["void"], accent, 0.55))
    fr.hline(br1, 2, 189, "═", fg=mix(P.C["void"], accent, 0.55))
    # left: stamp counter
    fr.write(br0 + 1, 4, "STAMP", fg=P.C["dim"])
    fr.write(br0 + 1, 13, f"#{k + 1:02d}", fg=accent)
    txt = f"{k + 1:02d}"
    tm = F.erode_mask(F.text_mask(txt, 8 * 18, bold=False), 1)
    ww = max(1, int(round(tm.shape[1] / 10.0)))
    hh = max(1, int(round(tm.shape[0] / 18.0)))
    x0 = 22 - ww // 2
    plate = mix(P.C["void"], P.C["blood"], 0.10 + 0.18 * esc)
    fr.paint_mask(tm, x0, r0, ww, hh,
                  ramp=P.RAMP_BLOCK, fg=accent,
                  fg2=mix(accent, P.C["white"], 0.45),
                  bg=plate, gain=3.0, min_v=0.06, hard=0.46)
    # carve digit counters so 0/6/8/9 never fuse into solid blocks
    for di, ch in enumerate(txt):
        if ch not in "04689":
            continue
        dcx = x0 + int((di + 0.5) * ww / max(1, len(txt)))
        for dy in ((2, 5) if hh >= 8 else ((2, 4) if hh >= 6 else (2,))):
            if fr.inb(r0 + dy, dcx):
                fr.put(r0 + dy, dcx, " ", bg=plate)
    fr.write(br1 - 1, 4, f"/ {N_STAMPS:02d}", fg=P.C["dim"])
    fr.write(br1 - 1, 12, f"ESC {esc * 100:5.1f}%", fg=P.C["gold"])
    # histogram of the 12 stamps
    for i in range(N_STAMPS):
        bh = 2 + int(round(i * 0.55))
        c = 36 + i * 2
        on = i <= k
        col = LINE_ACCENT[min(2, i // 4)] if on else P.C["grid"]
        for j in range(bh):
            fr.put(br1 - 1 - j, c, "█" if on else "░",
                   fg=col if i != k else P.C["white"])
    fr.write(br0 + 1, 36, "HISTORY", fg=P.C["dim"])
    # hero word: keep the full-screen shout for three stamps only, so the
    # remaining nine read as quiet machine stamps instead of a chorus of logos.
    cy = 96
    if k in FULL_WORD_STAMPS:
        fr.paint_text("EXECUTION", r0 + 1, cy + 1, h,
                      fg=mix(P.C["void"], P.C["crimson"], 0.55),
                      fg2=mix(P.C["void"], P.C["crimson"], 0.55), align="center",
                      thin=0, hard=0.50)
        fr.paint_text("EXECUTION", r0, cy, h,
                      fg=P.C["white"], fg2=mix(P.C["white"], P.C["crimson"], 0.35),
                      align="center", thin=0, hard=0.50)
    else:
        # compact receipt line: small letters + a machine rule, so the band
        # still reads as a running stamp instead of an empty hole
        hh = min(3, max(2, h // 3))
        fr.paint_text("EXEC", r0, cy - hh // 2, hh,
                      fg=mix(accent, P.C["white"], 0.55),
                      fg2=mix(accent, P.C["white"], 0.25), align="center",
                      thin=0, hard=0.46)
        rw = r0 + hh + 1
        fr.hline(rw, 58, 84, "─", fg=mix(P.C["void"], accent, 0.55))
        fr.hline(rw, 102, 122, "─", fg=mix(P.C["void"], accent, 0.55))
        fr.write(rw, 86, f"STAMP {k + 1:02d}/{N_STAMPS:02d}", fg=mix(accent, P.C["white"], 0.35))
        fr.write(rw, 124, "OK", fg=mix(P.C["void"], accent, 0.85))
        sweep = 58 + int((t * 26.0) % 70)
        if fr.inb(rw - 1, sweep):
            fr.put(rw - 1, sweep, "▁", fg=P.C["white"])
    # right: animated equalizer bars
    for i in range(11):
        c = 134 + i
        v = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 5.0 + i * 0.7)) * (0.4 + 0.6 * esc)
        bh = max(1, int(round((br1 - br0 - 2) * v)))
        for j in range(bh):
            fr.put(br1 - 1 - j, c, "▏▎▍▌"[(i + j) % 4], fg=mix(P.C["teal"], accent, v))
    fr.write(br0 + 1, 146, "LINE", fg=P.C["dim"])
    for i in range(3):
        fr.put(br0 + 1, 152 + i * 2, "■" if i < line_i else ("▒" if i == line_i else "□"),
               fg=accent if i <= line_i else P.C["grid"])
    fr.write(br0 + 2, 146, "STAMP", fg=P.C["dim"])
    for i in range(4):
        fr.put(br0 + 2, 152 + i * 2, "■" if i < stamp_i else ("▒" if i == stamp_i else "□"),
               fg=P.C["white"] if i == stamp_i else (accent if i < stamp_i else P.C["grid"]))
    fr.write(br0 + 3, 146, "SCREEN", fg=P.C["dim"])
    for i in range(8):
        on = (int(t * 9) + i) % 8 != 0
        fr.put(br0 + 3, 153 + i, "█" if on else "░", fg=mix(accent, P.C["void"], 0.2))
    fr.write(br0 + 4, 146, "YIELD", fg=P.C["dim"])
    fr.write(br0 + 4, 152, f"{100 * esc:5.1f}%", fg=P.C["gold"])
    # status under the slab
    fr.write(br1 + 1, 4, f"exec --target=ALL  stamp={k + 1:02d}  rc=0  "
                         f"pid={1000 + k * 17}  line={line_i + 1}", fg=P.C["fg"])


def _card(fr, kk, cur_k, age):
    r0, c0 = _card_row(kk), _card_col(kk)
    r1, c1 = r0 + CARD_H - 1, c0 + CARD_W - 1
    line_i, stamp_i = kk // 4, kk % 4
    accent = LINE_ACCENT[min(2, line_i)]
    active = kk <= cur_k
    flash = (kk == cur_k) and age < 0.26
    if not active:
        fr.fill_rect(r0, c0, r1, c1, " ", bg=mix(P.C["void"], P.C["blood"], 0.03))
        fr.box(r0, c0, r1, c1, 1, fg=mix(P.C["void"], P.C["line"], 0.75))
        fr.write(r0, c0 + 2, f" EXEC #{kk + 1:02d} ", fg=P.C["grid"])
        fr.write(r0 + 3, c0 + 9, "WAIT", fg=mix(P.C["void"], P.C["line"], 1.0))
        for rr in range(r0 + 2, r1):
            for cc in range(c0 + 3, c1 - 1, 4):
                fr.put(rr, cc, "·", fg=mix(P.C["void"], P.C["line"], 0.5))
        return
    bg = mix(P.C["void"], accent, 0.16 if flash else 0.05)
    fr.fill_rect(r0, c0, r1, c1, " ", bg=bg)
    fr.box(r0, c0, r1, c1, 2 if flash else 1,
           fg=P.C["white"] if flash else accent)
    fr.write(r0, c0 + 2, f" EXEC #{kk + 1:02d} ",
             fg=P.C["white"] if flash else accent)
    fr.write(r0, c1 - 5, " OK " if not flash else " OK ", fg=P.C["green"])
    # inner stamp box
    sr0, sr1 = r0 + 1, r0 + 3
    sc0, sc1 = c0 + 3, c1 - 3
    fr.box(sr0, sc0, sr1, sc1, 1,
           fg=P.C["white"] if flash else mix(accent, P.C["void"], 0.15),
           bg=None if not flash else None)
    fr.write(sr0 + 1, sc0 + 3, "EXECUTION",
             fg=P.C["white"] if flash else accent)
    fr.write(r0 + 4, c0 + 3, f"SEQ 0x{kk * 7 + 3:02X}  L{line_i + 1} S{stamp_i + 1}",
             fg=P.C["mid"])
    fr.write(r0 + 5, c0 + 3, f"rc=0   t={T0 + kk * STAMP_STEP:8.3f}", fg=P.C["dim"])
    # yield bar
    fr.write(r0 + 6, c0 + 3, "██████████████████████", fg=mix(accent, P.C["void"], 0.1))
    fr.write(r0 + 6, c1 - 4, "100%", fg=P.C["green"])


def _impact_row(fr, ctx, k, esc):
    r = 10
    fr.write(r, 4, "IMPACT", fg=P.C["dim"])
    for c in range(12, 150, 2):
        v = 0.5 + 0.5 * math.sin(ctx.t * 14.0 + c * 0.31) * math.cos(ctx.t * 3.1 + c * 0.07)
        v = v * (0.4 + 0.6 * esc)
        ch = "▁▂▃▄▅▆▇█"[min(7, int(v * 7.99))]
        fr.write(r, c, ch + " ", fg=mix(P.C["void"], P.C["crimson"], 0.3 + 0.7 * v))
    fr.write(r, 154, f"PEAK {int(60 + 40 * esc)}dB", fg=P.C["red"])
    fr.write(r, 170, f"{(k + 1) / N_STAMPS * 100:5.1f}%", fg=P.C["gold"])
    rule(fr, 11, fg=mix(P.C["void"], P.C["line"], 0.5), step=24)


def _ladder(fr, ctx, k, esc):
    r = 24
    fr.write(r, 4, "STAMP LADDER", fg=P.C["dim"])
    for i in range(N_STAMPS):
        c = 20 + i * 13
        on = i <= k
        thr = LINE_ACCENT[min(2, i // 4)]
        col = P.C["white"] if i == k else (thr if on else P.C["grid"])
        fr.write(r, c, "█" if on else "░", fg=col)
        fr.write(r, c + 2, f"{i + 1:02d}", fg=P.C["mid"] if on else P.C["grid"])
    fr.write(r, 178, "HI" if esc > 0.6 else ("MID" if esc > 0.3 else "LO"),
             fg=P.C["red"] if esc > 0.6 else P.C["gold"])
    W.progress_bar(fr, 25, 4, 74, (k + 1) / N_STAMPS, fg=P.C["crimson"],
                   show_pct=False, color_by=lambda f: mix(P.C["gold"], P.C["red"], f))
    fr.write(25, 82, "EXECUTION DENSITY", fg=P.C["dim"])
    fr.write(25, 102, f"{(k + 1) / N_STAMPS * 100:5.1f}%", fg=P.C["white"])
    fr.write(25, 116, "SYNC", fg=P.C["dim"])
    for i in range(8):
        fr.write(25, 122 + i, "█" if (int(ctx.t * 12) + i) % 3 else "░", fg=P.C["teal"])


def _lines_meter(fr, ctx, k, esc):
    for i in range(3):
        r = 26 + i
        done = fx.clamp((k - i * 4 + 1) / 4.0)
        fr.write(r, 4, f"L{i + 1} EXECUTION x4",
                 fg=LINE_ACCENT[i] if done > 0 else P.C["dim"])
        W.progress_bar(fr, r, 22, 44, done, fg=LINE_ACCENT[i], show_pct=False)
        fr.write(r, 68, f"{int(done * 4)}/4", fg=P.C["fg"] if done >= 1 else P.C["dim"])
        fr.write(r, 73, "COMPLETE" if done >= 1 else ("RUNNING" if done > 0 else "QUEUED"),
                 fg=P.C["green"] if done >= 1 else (P.C["gold"] if done > 0 else P.C["grid"]))
    # right stats block
    fr.write(26, 100, "SYSTEM", fg=P.C["primary"])
    for i, (nm, v) in enumerate((("CPU", 0.55 + 0.4 * esc),
                                 ("PWR", 0.62 + 0.3 * esc),
                                 ("MEM", 0.40 + 0.5 * esc))):
        fr.write(27 + i, 100, nm, fg=P.C["dim"])
        W.segmented_bar(fr, 27 + i, 105, 20, v, cells=10, fg=P.C["gold"])
        fr.write(27 + i, 128, f"{v * 100:3.0f}%", fg=P.C["mid"])
    fr.write(30, 100, "ERR", fg=P.C["dim"])
    fr.write(30, 105, "0", fg=P.C["green"])
    fr.write(30, 110, "PROC", fg=P.C["dim"])
    fr.write(30, 116, f"{(100 + 90 * esc) * 3:.0f}", fg=P.C["fg"])
    fr.write(30, 128, "LOAD", fg=P.C["dim"])
    fr.write(30, 134, f"{0.40 + 0.55 * esc:4.2f}", fg=P.C["teal"])
    fr.write(26, 146, "TARGET", fg=P.C["dim"])
    fr.write(26, 154, "ALL", fg=P.C["red"])
    fr.write(27, 146, "SCOPE", fg=P.C["dim"])
    fr.write(27, 154, "GLOBAL", fg=P.C["fg"])
    fr.write(28, 146, "STAMPS", fg=P.C["dim"])
    fr.write(28, 154, f"{k + 1:02d}", fg=P.C["white"])
    fr.write(28, 160, f"REMAIN {N_STAMPS - k - 1:02d}", fg=P.C["mid"])
    fr.write(29, 146, "MODE", fg=P.C["dim"])
    fr.write(29, 154, "FORCE", fg=P.C["crimson"])
    fr.write(29, 146, "T-MINUS", fg=P.C["dim"])
    fr.write(29, 155, f"{(T0 + N_STAMPS * STAMP_STEP - ctx.t):5.2f}s", fg=P.C["gold"])


def _log_strip(fr, ctx, k):
    t = ctx.t
    fr.write(31, 4, "EXEC LOG", fg=P.C["dim"])
    logs = [
        f"> exec --target=ALL --mode=FORCE --stamp={k + 1:02d} --t={t:8.3f}",
        f"> write EXECUTION @ line {(k // 4) + 1} stamp {(k % 4) + 1}_  ... OK",
        f"> rc=0  elapsed=0.0{k % 9}s  out={{stamp_ok:{k + 1}, fail:0}}",
    ]
    for i, s in enumerate(logs):
        fr.write(32 + i, 4, s, fg=P.C["mid"] if i < 2 else P.C["fg"])
    W.hex_dump(fr, 31, 128, 4, 62, t, seed=9,
               fg=mix(P.C["void"], P.C["mid"], 0.6), step=0.4)
    rule(fr, 35, fg=mix(P.C["void"], P.C["line"], 0.8), step=16)


# ===========================================================================
# phase B - the multilingual counting main frame
# ===========================================================================
def _count_phase(fr, ctx):
    t = ctx.t
    words = TL.COUNT_WORDS
    idx = -1
    for i, wd in enumerate(words):
        if t >= wd[3]:
            idx = i
    if idx < 0:
        idx = 0
    post = t >= EXEC_SLAM
    dense_bg(fr, ctx, seed=51, fg=P.C["teal"], hot=0.5 + 0.3 * (idx + 1) / 6.0)
    if post:
        _post_top(fr, ctx)
        _execution_slam(fr, ctx)
        _post_bottom(fr, ctx)
        _num_strip(fr, ctx, 5, post)
        return
    _count_top(fr, ctx, idx)
    _count_wave(fr, ctx)
    _count_ticker(fr, ctx, idx)
    _count_progress(fr, ctx, idx)
    _hero_word(fr, ctx, idx, t - words[idx][3])
    if idx > 0:
        _flying_prev(fr, ctx, idx - 1, fx.clamp((t - words[idx][3]) / 0.20))
    _lang_panels(fr, ctx, idx)
    _count_note(fr, ctx, idx)
    _lang_chips(fr, ctx, idx, post)
    _num_strip(fr, ctx, idx, post)
    # beat impact
    age = t - words[idx][3]
    if age < 0.16:
        amp = 1.0 - fx.clamp(age / 0.16)
        ctx.set_glitch(0.16 * amp)
        ctx.meta["flash"] = 0.20 * amp
        ctx.meta["flash_color"] = NUM_COLS[idx]
        ctx.shake(3)
    ctx.meta["bloom"] = 0.28
    ctx.meta["vignette"] = 0.9


def _count_top(fr, ctx, idx):
    fr.write(0, 7, "┤ MULTILINGUAL COUNT ├", fg=P.C["teal"])
    fr.write(0, 30, "// BASE-6 COUNTER // LANG ROTATION", fg=P.C["dim"])
    fr.write(0, 65, f"SEQ {idx + 1:02d}/06", fg=P.C["white"])
    fr.write(0, 79, f"LANG {LANGS[idx]}", fg=NUM_COLS[idx])
    fr.write(0, 90, "SYNC: BEAT-LOCK", fg=P.C["green"])
    fr.write(0, 110, f"T {ctx.t:8.3f}", fg=P.C["dim"])
    fr.rtext(0, "RCV 06/06  LOSS 0.00  MODE=COUNT", fg=P.C["dim"], pad=6)
    rule(fr, 1, fg=mix(P.C["void"], P.C["teal"], 0.5), step=8)


def _count_wave(fr, ctx):
    fr.fill_rect(2, 2, 5, 189, " ", bg=mix(P.C["void"], P.C["teal"], 0.02))
    W.ecg_trace(fr, 2, 4, 184, 4, ctx.t, fg=mix(P.C["void"], P.C["teal"], 0.8),
                fg_peak=P.C["primary"], bpm=130, amp=0.85, label=False,
                bg=None)
    fr.write(2, 6, "VOCAL", fg=P.C["teal"])
    _synth_panel(fr, ctx)

    fr.write(4, 6, "LIVE", fg=P.C["green"])
    fr.write(2, 160, "13.0k", fg=P.C["teal"])
    fr.write(4, 160, "ANALOG", fg=P.C["dim"])


def _count_ticker(fr, ctx, idx):
    words = TL.COUNT_WORDS
    r = 6
    fr.write(r, 4, "◆ NOW", fg=P.C["white"])
    fr.write(r, 11, f"{words[idx][0]:<6}", fg=NUM_COLS[idx])
    fr.write(r, 19, f"{LANGS[idx]} #{idx + 1:02d}/06", fg=P.C["fg"])
    fr.write(r, 34, f"{words[idx][3]:8.3f}", fg=P.C["gold"])
    if idx < 5:
        nxt = words[idx + 1]
        fr.write(r, 46, f"> NEXT {nxt[0]:<6} {LANGS[idx + 1]} {nxt[3]:8.3f}",
                 fg=P.C["mid"])
    else:
        fr.write(r, 46, "> NEXT EXECUTION  161.727", fg=P.C["red"])
    # 6 beat ticks
    for i in range(6):
        c = 100 + i * 6
        on = i <= idx
        fr.write(r, c, "◆" if i == idx else ("◇" if on else "·"),
                 fg=P.C["white"] if i == idx else (NUM_COLS[i] if on else P.C["grid"]))
    fr.write(r, 140, "PREV", fg=P.C["dim"])
    if idx > 0:
        fr.write(r, 145, f"{words[idx - 1][0]} {words[idx - 1][3]:8.3f}", fg=P.C["mid"])
    else:
        fr.write(r, 145, "--  silent", fg=P.C["grid"])
    fr.write(r, 168, "ERR 0", fg=P.C["green"])
    # marquee of the whole count line
    W.marquee(fr, 7, " EIN / DOS / TROIS / NE / FEM / LIU / EXECUTION / "
                     "EIN / DOS / TROIS / NE / FEM / LIU / ", ctx.t,
              speed=14.0, fg=mix(P.C["void"], P.C["teal"], 0.9), gap=6)
    rule(fr, 8, fg=mix(P.C["void"], P.C["teal"], 0.35), step=28)


def _count_progress(fr, ctx, idx):
    r = 9
    fr.write(r, 2, "COUNT", fg=P.C["dim"])
    for i in range(6):
        c = 10 + i * 30
        w = 28
        done = i < idx
        cur = i == idx
        fr.write(r, c, f"{i + 1:02d} {LANGS[i]}", fg=P.C["white"] if cur else
                 (NUM_COLS[i] if done else P.C["grid"]))
        fr.write(r, c + 8, TL.COUNT_WORDS[i][0], fg=P.C["fg"] if (done or cur) else P.C["grid"])
        if cur:
            fr.write(r, c + 16, "LIVE", fg=P.C["gold"])
        elif done:
            fr.write(r, c + 16, " OK ", fg=P.C["green"])
        else:
            fr.write(r, c + 16, "WAIT", fg=P.C["grid"])


def _hero_word(fr, ctx, i, age):
    word = TL.COUNT_WORDS[i][0]
    col = NUM_COLS[i]
    punch = 1.0 - fx.ease_out(fx.clamp(age / 0.11))
    h = 12 + int(round(2 * punch))
    fr.fill_rect(10, 50, 23, 141, " ", bg=mix(P.C["void"], P.C["blood"], 0.05))
    fr.hline(10, 50, 141, "─", fg=mix(P.C["void"], col, 0.5))
    fr.hline(23, 50, 141, "─", fg=mix(P.C["void"], col, 0.5))
    fr.write(10, 52, f" ┤ NUMBER {i + 1:02d} ├", fg=col)
    fr.write(10, 116, f"┤ {LANG_NAMES[i]} ├", fg=P.C["mid"])
    fr.write(11, 52, f" {h} H-CELLS  W/ {word}", fg=P.C["dim"])
    fr.write(11, 118, f"{LANGS[i]} // {len(word)} SYL", fg=P.C["dim"])
    fr.paint_text(word, 12, 96, h, fg=mix(col, P.C["white"], 0.55),
                  fg2=P.C["white"], align="center")
    fr.write(22, 52, f"CONF {0.90 + 0.09 * fx.hash01(i, 3):.4f}", fg=P.C["green"])
    fr.write(22, 118, "SYNTH.OK  LAT 3ms", fg=P.C["teal"])
    # language code, huge, left
    panel(fr, 12, 4, 21, 46, "LANG", fg=mix(P.C["void"], col, 0.65),
          bg=mix(P.C["void"], col, 0.04))
    fr.paint_text(LANGS[i], 13, 25, 6, fg=col, fg2=mix(col, P.C["white"], 0.6),
                  align="center")
    fr.write(20, 8, LANG_NAMES[i], fg=P.C["mid"])
    fr.write(20, 26, f"{i + 1:02d}/06", fg=P.C["fg"])
    # index, huge, right
    panel(fr, 12, 146, 21, 189, "INDEX", fg=mix(P.C["void"], col, 0.65),
          bg=mix(P.C["void"], col, 0.04))
    fr.paint_text(f"{i + 1:02d}", 13, 165, 7, fg=col, fg2=mix(col, P.C["white"], 0.6),
                  align="center")
    fr.paint_text("/06", 20, 186, 2, fg=P.C["dim"], fg2=P.C["mid"], align="right")
    fr.write(20, 149, "SYNC", fg=P.C["dim"])
    for k2 in range(6):
        fr.write(20, 154 + k2, "█" if k2 <= i else "░",
                 fg=NUM_COLS[k2] if k2 <= i else P.C["grid"])


def _count_note(fr, ctx, idx):
    """Row 24 band: what is locked, what comes next, how long until the slam."""
    r = 24
    fr.fill_rect(r, 2, r, 189, " ", bg=mix(P.C["void"], P.C["teal"], 0.02))
    fr.hline(r, 2, 189, "─", fg=mix(P.C["void"], P.C["teal"], 0.45))
    fr.write(r, 4, "◆", fg=P.C["white"])
    fr.write(r, 6, f"NUMBER {idx + 1:02d}/06 LOCKED", fg=P.C["white"])
    fr.write(r, 26, f"WORD {TL.COUNT_WORDS[idx][0]}", fg=NUM_COLS[idx])
    fr.write(r, 40, f"ONSET {TL.COUNT_WORDS[idx][3]:8.3f}", fg=P.C["mid"])
    nxt = TL.COUNT_WORDS[idx + 1] if idx < 5 else None
    if nxt:
        fr.write(r, 58, f"NEXT {nxt[0]} ({LANGS[idx + 1]}) in "
                        f"{nxt[3] - ctx.t:5.2f}s", fg=P.C["gold"])
    else:
        fr.write(r, 58, f"EXECUTION in {EXEC_SLAM - ctx.t:5.2f}s", fg=P.C["red"])
    fr.write(r, 100, "COUNTING RULES", fg=P.C["dim"])
    fr.write(r, 116, "1 WORD / 1 BEAT / 6 LANGUAGES", fg=P.C["fg"])
    fr.write(r, 148, "TOTAL", fg=P.C["dim"])
    fr.write(r, 154, f"{idx + 1:02d}/06", fg=P.C["white"])
    fr.write(r, 162, "YIELD", fg=P.C["dim"])
    fr.write(r, 168, f"{(idx + 1) / 6 * 100:5.1f}%", fg=P.C["teal"])


def _flying_prev(fr, ctx, i, e):
    """Previous number shrinking out of the hero into the bottom strip."""
    word = TL.COUNT_WORDS[i][0]
    col = NUM_COLS[i]
    sr, sc = CARD_H * 0 + 36, 2 + i * 31
    h = int(round(fx.lerp(12, 3, fx.ease_inout(e))))
    r0 = int(round(fx.lerp(12, sr + 2, fx.ease_inout(e))))
    c0 = int(round(fx.lerp(96, sc + 14, fx.ease_inout(e))))
    fr.paint_text(word, r0, c0, h, fg=col, fg2=mix(col, P.C["white"], 0.5),
                  align="center", alpha=max(0.35, 1.0 - 0.6 * e))


def _lang_panels(fr, ctx, idx):
    r0, c0 = 25, 4
    c1p = 62
    panel(fr, r0, c0, r0 + 8, 62, "LANGUAGE BANK",
          fg=mix(P.C["void"], P.C["teal"], 0.7),
          bg=mix(P.C["void"], P.C["teal"], 0.03))
    fr.write(r0 + 1, c0 + 2, "01  LANG  WORD   ONSET     STATE", fg=P.C["grid"])
    for i, (word, cn, lang, wt) in enumerate(TL.COUNT_WORDS):
        r = r0 + 2 + i
        cur = i == idx
        settled = i <= idx
        col = NUM_COLS[i] if settled else P.C["grid"]
        if cur:
            fr.fill_rect(r, c0 + 1, r, c1p - 2, " ",
                         bg=mix(P.C["void"], col, 0.18))
            fr.write(r, c0 + 2, "◆", fg=P.C["white"])
        else:
            fr.write(r, c0 + 2, "·", fg=P.C["grid"])
        fr.write(r, c0 + 4, f"{i + 1:02d}", fg=P.C["white"] if cur else col)
        fr.write(r, c0 + 7, f"{LANGS[i]:<3}", fg=col)
        fr.write(r, c0 + 11, f"{word:<6}", fg=P.C["white"] if cur else
                 (P.C["fg"] if settled else P.C["grid"]))
        fr.write(r, c0 + 19, f"{wt:8.3f}", fg=P.C["dim"] if not settled else P.C["mid"])
        fr.write(r, c0 + 29, "██" if settled else "░░",
                 fg=col if settled else P.C["grid"])
        fr.write(r, c0 + 32, f"{'SYNTH' if settled else 'WAIT':<6}", fg=P.C["dim"])
        if cur:
            fr.write(r, c0 + 46, "SYNTHED", fg=P.C["gold"])
        elif settled:
            fr.write(r, c0 + 46, "OK", fg=P.C["green"])
    # right column: counters
    r1, cc = 25, 146
    panel(fr, r1, cc, r1 + 8, 189, "COUNTER",
          fg=mix(P.C["void"], P.C["teal"], 0.7),
          bg=mix(P.C["void"], P.C["teal"], 0.03))
    rows = [
        ("COUNT", f"{idx + 1:02d}/06", P.C["white"]),
        ("BASE", "10 / 6-LANG", P.C["fg"]),
        ("CLOCK", "130 BPM 2/1", P.C["teal"]),
        ("DRIFT", f"{0.001 * (idx + 1):.4f}s", P.C["green"]),
        ("EXEC", "161.727", P.C["red"]),
        ("NEXT", TL.COUNT_WORDS[idx + 1][0] if idx < 5 else "EXECUTION",
         P.C["gold"]),
    ]
    for i, (nm, val, col) in enumerate(rows):
        fr.write(r1 + 1 + i, cc + 2, nm, fg=P.C["dim"])
        fr.write(r1 + 1 + i, cc + 10, val, fg=col)
    W.progress_bar(fr, r1 + 8, cc + 2, 36, (idx + 1) / 6.0, fg=P.C["gold"],
                   show_pct=True)
    fr.vline(64, 10, 22, "│", fg=mix(P.C["void"], P.C["teal"], 0.35))
    fr.vline(142, 10, 22, "│", fg=mix(P.C["void"], P.C["teal"], 0.35))


def _lang_chips(fr, ctx, idx, post):
    r = 34
    fr.write(r, 2, "LANG", fg=P.C["dim"])
    for i in range(6):
        c = 9 + i * 26
        cur = (i == idx) and not post
        done = i < idx or post
        col = NUM_COLS[i]
        if cur:
            fr.fill_rect(r, c, r, c + 20, " ", bg=mix(P.C["void"], col, 0.22))
            fr.write(r, c, f"◆[{LANGS[i]}] {TL.COUNT_WORDS[i][0]:<6} SYNTH",
                     fg=P.C["white"])
        elif done:
            fr.write(r, c, f"[{LANGS[i]}] {TL.COUNT_WORDS[i][0]:<6}  ✓", fg=col)
        else:
            fr.write(r, c, f"[{LANGS[i]}] {TL.COUNT_WORDS[i][0]:<6}  ·", fg=P.C["grid"])
    fr.write(r, 168, "EXEC 161.727", fg=P.C["red"])


def _num_strip(fr, ctx, idx, post):
    r0 = 36
    for i in range(6):
        c0 = 2 + i * 31
        r1, c1 = r0 + CARD_H - 1, c0 + CARD_W - 1
        word, cn, lang, wt = TL.COUNT_WORDS[i]
        col = NUM_COLS[i]
        cur = (i == idx) and not post
        done = i < idx or post
        if done or cur:
            bg = mix(P.C["void"], col, 0.14 if cur else 0.05)
            fr.fill_rect(r0, c0, r1, c1, " ", bg=bg)
            fr.box(r0, c0, r1, c1, 2 if cur else 1,
                   fg=P.C["white"] if cur else col)
            fr.write(r0, c0 + 2, f" #{i + 1:02d} {LANGS[i]} ",
                     fg=P.C["white"] if cur else col)
            if cur:
                fr.write(r0, c1 - 7, " LIVE ", fg=P.C["white"])
            elif done:
                fr.write(r0, c1 - 5, " ✓ ", fg=P.C["green"])
            # letter-spaced word
            spaced = " ".join(word)
            fr.write(r0 + 2, c0 + max(2, (CARD_W - len(spaced)) // 2), spaced,
                     fg=P.C["white"] if cur else mix(col, P.C["void"], 0.15))
            fr.write(r0 + 3, c0 + 2, f"{LANG_NAMES[i]:<12}", fg=P.C["mid"])
            fr.write(r0 + 3, c1 - 6, f"{i + 1:02d}/06", fg=P.C["fg"])
            fr.write(r0 + 4, c0 + 2, f"{wt:8.3f}  {len(word)}S", fg=P.C["dim"])
            W.segmented_bar(fr, r0 + 5, c0 + 2, 20, 1.0, cells=10,
                            fg=P.C["gold"] if cur else col)
            fr.write(r0 + 5, c1 - 6, "SYNTH" if not cur else "LIVE",
                     fg=P.C["green"] if not cur else P.C["gold"])
            fr.write(r0 + 6, c0 + 2, f"LOCKED  {i + 1:02d}/06", fg=P.C["grid"])
            if cur:
                fr.write(r0 + 6, c1 - 12, "◆ PLAYING", fg=P.C["gold"])
        else:
            fr.fill_rect(r0, c0, r1, c1, " ", bg=mix(P.C["void"], P.C["blood"], 0.02))
            fr.box(r0, c0, r1, c1, 1, fg=mix(P.C["void"], P.C["line"], 0.7))
            fr.write(r0, c0 + 2, f" #{i + 1:02d} {LANGS[i]} ", fg=P.C["grid"])
            fr.write(r0 + 2, c0 + 4, f"{word}", fg=P.C["grid"])
            fr.write(r0 + 4, c0 + 2, f"{wt:8.3f}", fg=mix(P.C["void"], P.C["line"], 0.9))
            fr.write(r0 + 6, c0 + 2, "WAIT BEAT", fg=mix(P.C["void"], P.C["line"], 0.9))


# --------------------------------------------------------------------------
# post-slam: EXECUTION kills the counter
# --------------------------------------------------------------------------
def _post_top(fr, ctx):
    p = fx.clamp((ctx.t - EXEC_SLAM) / (T1 - EXEC_SLAM))
    fr.write(0, 7, "┤ COUNT TERMINATED ├", fg=P.C["crimson"])
    fr.write(0, 30, "// MULTILINGUAL COUNTER // ABORTED", fg=P.C["red"])
    fr.write(0, 68, f"EXEC {ctx.t:8.3f}", fg=P.C["white"])
    fr.write(0, 90, "SIGNAL: 1", fg=P.C["gold"])
    fr.write(0, 104, "STATE: OBLITERATED", fg=P.C["crimson"])
    fr.rtext(0, "rc=0  TARGETS=ALL  ESCAPE=NONE", fg=P.C["red"], pad=6)
    rule(fr, 1, fg=P.C["blood"], step=8)
    # the vocal trace flatlines
    fr.write(2, 4, "FLATLINE", fg=P.C["crimson"])
    for c in range(14, 189):
        v = int(2 * math.sin(ctx.t * 2.0 + c * 0.5)) if c > 150 else 0
        fr.put(3 + (v > 0), c, "─" if c % 2 == 0 else " ", fg=P.C["blood"])
    fr.write(4, 4, f"VOICE  0.00    RMS 0.00    EXEC {int(100 * p)}%", fg=P.C["red"])
    fr.write(5, 4, "ALL CHANNELS MUTED - ONLY EXECUTION REMAINS", fg=P.C["fg"])
    for i, c in enumerate(range(6, 189, 6)):
        fr.put(5, c, "█" if (i + int(ctx.t * 4)) % 3 else "░", fg=P.C["blood"])
    # the six words erased in a scrolling band
    W.marquee(fr, 6, " EIN -ERASED-  DOS -ERASED-  TROIS -ERASED-  "
                     "NE -ERASED-  FEM -ERASED-  LIU -ERASED-  EXECUTION ", ctx.t,
              speed=30.0, fg=P.C["blood"], gap=4)
    for c in range(2, 189, 8):
        fr.put(7, c, "█", fg=mix(P.C["void"], P.C["crimson"], 0.5))
    fr.write(7, 4, "IRREVERSIBLE" if p > 0.3 else "COMMITTING", fg=P.C["crimson"])
    fr.write(7, 160, f"T+{(ctx.t - EXEC_SLAM):5.2f}s", fg=P.C["gold"])
    rule(fr, 8, fg=P.C["blood"], step=8)


def _execution_slam(fr, ctx):
    t = ctx.t
    p = fx.clamp((t - EXEC_SLAM) / (T1 - EXEC_SLAM))
    age = t - EXEC_SLAM
    fr.fill_rect(9, 2, 24, 189, " ", bg=mix(P.C["void"], P.C["blood"], 0.22 + 0.22 * p))
    fr.hline(9, 2, 189, "═", fg=P.C["crimson"])
    fr.hline(24, 2, 189, "═", fg=P.C["crimson"])
    fr.write(9, 5, "┤ EXECUTION ├", fg=P.C["white"])
    fr.write(9, 138, f"// SLAM {p * 100:5.1f}%", fg=P.C["red"])
    h = min(11, 9 + int(round(2 * (1.0 - fx.ease_out(fx.clamp(age / 0.12))))))
    big(fr, "EXECUTION", 12, 96, h, fg=P.C["crimson"], fg2=P.C["white"],
        align="center")
    # red bars jammed above/below
    for i, c in enumerate(range(4, 189, 8)):
        fr.put(11, c, "█", fg=mix(P.C["blood"], P.C["crimson"], (i % 3) / 2))
        fr.put(23, c, "█", fg=mix(P.C["blood"], P.C["crimson"], ((i + 1) % 3) / 2))
    fr.write(23, 4, f"T+{age:5.2f}s", fg=P.C["gold"])
    fr.write(23, 14, "irreversible" if p > 0.4 else "committing...", fg=P.C["red"])
    fr.write(23, 40, "COUNT 06/06", fg=P.C["fg"])
    fr.write(23, 54, "rc=0", fg=P.C["green"])
    fr.write(23, 62, "TARGETS=1", fg=P.C["crimson"])
    fr.write(23, 74, "ALTERNATIVES=0", fg=P.C["crimson"])
    fr.write(23, 100, "EIN DOS TROIS NE FEM LIU -> 0", fg=P.C["blood"])
    ctx.set_glitch(min(0.20, 0.05 + 0.15 * p))
    if age < 0.16:
        ctx.meta["flash"] = 0.45 * (1 - age / 0.16)
        ctx.meta["flash_color"] = P.C["white"]
    ctx.shake(2 + 5 * p)
    ctx.meta["bloom"] = 0.36
    ctx.meta["vignette"] = 1.0


def _post_bottom(fr, ctx):
    p = fx.clamp((ctx.t - EXEC_SLAM) / (T1 - EXEC_SLAM))
    # left: aftermath
    panel(fr, 25, 4, 33, 60, "AFTERMATH", fg=P.C["blood"],
          bg=mix(P.C["void"], P.C["blood"], 0.06))
    lines = [("LANG BANK", "PURGED", P.C["crimson"]),
             ("ENTRIES", "6 -> 0", P.C["red"]),
             ("COUNTER", "OVERFLOW", P.C["gold"]),
             ("STATE", "EXECUTED", P.C["white"])]
    for i, (nm, val, col) in enumerate(lines):
        fr.write(26 + i, 6, nm, fg=P.C["dim"])
        fr.write(26 + i, 20, val, fg=col)
    fr.write(30, 6, "irreversible damage:", fg=P.C["red"])
    fr.write(31, 6, ">>> no rollback available", fg=P.C["crimson"])
    fr.write(32, 6, ">>> next: ONLY EXECUTION", fg=P.C["red"])
    # center: the charging execution
    panel(fr, 25, 64, 33, 142, "EXECUTING", fg=P.C["crimson"],
          bg=mix(P.C["void"], P.C["blood"], 0.08))
    fr.write(26, 66, "TARGET", fg=P.C["dim"])
    fr.write(26, 74, "ALL", fg=P.C["red"])
    fr.write(26, 80, "TARGETS", fg=P.C["dim"])
    fr.write(26, 89, "1", fg=P.C["crimson"])
    fr.write(26, 93, "ALTERNATIVES", fg=P.C["dim"])
    fr.write(26, 107, "0", fg=P.C["crimson"])
    fr.write(27, 66, "irreversible" if p > 0.4 else "committing...", fg=P.C["red"])
    fr.write(28, 66, "EXEC", fg=P.C["dim"])
    W.progress_bar(fr, 28, 72, 66, p, fg=P.C["crimson"], show_pct=True)
    fr.write(29, 66, "COUNT", fg=P.C["dim"])
    fr.write(29, 73, "06/06 words  ->  0", fg=P.C["fg"])
    fr.write(30, 66, "SIGNAL", fg=P.C["dim"])
    fr.write(30, 74, "1 EXECUTION ONLY", fg=P.C["crimson"])
    fr.write(31, 66, "T-MINUS", fg=P.C["dim"])
    fr.write(31, 75, f"{max(0.0, T1 - ctx.t):5.2f}s", fg=P.C["gold"])
    fr.write(32, 66, "MEMORY OF THE SIX NUMBERS: ERASED", fg=P.C["blood"])
    # right: counters
    panel(fr, 25, 146, 33, 189, "COUNTER", fg=P.C["blood"],
          bg=mix(P.C["void"], P.C["blood"], 0.06))
    fr.write(26, 148, "COUNT", fg=P.C["dim"])
    fr.write(26, 158, f"{int(6 * p):02d}/06", fg=P.C["white"])
    fr.write(27, 148, "TARGETS", fg=P.C["dim"])
    fr.write(27, 158, "1", fg=P.C["crimson"])
    fr.write(28, 148, "ALTERNATIVES", fg=P.C["dim"])
    fr.write(28, 162, "0", fg=P.C["crimson"])
    fr.write(29, 148, "NEXT", fg=P.C["dim"])
    fr.write(29, 158, "ONLY EXEC", fg=P.C["red"])
    fr.write(30, 148, "T-MINUS", fg=P.C["dim"])
    fr.write(30, 158, f"{max(0.0, T1 - ctx.t):5.2f}s", fg=P.C["gold"])
    W.progress_bar(fr, 32, 148, 38, p, fg=P.C["crimson"], show_pct=True)
    # row 34: the six words crossed out
    fr.write(34, 2, "ERASED", fg=P.C["crimson"])
    for i in range(6):
        c = 10 + i * 29
        fr.write(34, c, f"✗ {TL.COUNT_WORDS[i][0]:<6}", fg=P.C["blood"])
        for cc in range(c, c + 10, 2):
            fr.put(34, cc, "─", fg=mix(P.C["void"], P.C["line"], 0.8))
    fr.write(34, 172, "ONLY EXEC", fg=P.C["crimson"])

def _synth_panel(fr, ctx):
    """Rows 25..33 centre: the six numbers being synthesised side by side."""
    r0, c0 = 25, 66
    panel(fr, r0, c0, r0 + 8, 142, "SYNTHESIS BUS",
          fg=mix(P.C["void"], P.C["teal"], 0.7),
          bg=mix(P.C["void"], P.C["teal"], 0.03))
    idx = -1
    for i, wd in enumerate(TL.COUNT_WORDS):
        if ctx.t >= wd[3]:
            idx = i
    for i in range(6):
        r = r0 + 1 + i
        settled = i <= idx
        col = NUM_COLS[i] if settled else P.C["grid"]
        cur = i == idx
        fr.write(r, c0 + 2, f"{LANGS[i]}", fg=P.C["white"] if cur else col)
        fr.write(r, c0 + 6, f"{TL.COUNT_WORDS[i][0]:<6}", fg=col)
        w = 46
        done = 1.0 if settled else 0.0
        filled = int(w * (done if not cur else 0.4 + 0.6 * fx.clamp((ctx.t - TL.COUNT_WORDS[i][3]) / 0.5)))
        for j in range(w):
            fr.put(r, c0 + 14 + j, "█" if j < filled else "░",
                   fg=col if j < filled else P.C["grid"])
        fr.write(r, c0 + 62, f"{TL.COUNT_WORDS[i][3]:8.3f}", fg=P.C["mid"])
        fr.write(r, c0 + 72, "OK" if settled else "..", fg=P.C["green"] if settled else P.C["grid"])
    fr.write(r0 + 8, c0 + 2, "BUS // 6 LANG // 1 TARGET WORD PER BEAT", fg=P.C["dim"])
