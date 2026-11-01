"""Chrome: header, rules, subtitle strip and the thin spectrum band.

The chrome frame is the full 192x60 grid.  Scene animation goes into rows
2..46; everything else is program-interface furniture that stays put for the
whole MV so the viewer always knows where to read.
"""
from __future__ import annotations

import os
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import font as F
from . import fx
from . import layout as L
from . import palette as P
from . import timeline as TL
from .frame import Frame

YAHEI = F.YAHEI
YAHEI_B = F.YAHEI_B
CONSOLA = F.CONSOLA
CONSOLA_B = F.CONSOLA_B
MALGUN = F.MALGUN
MALGUN_B = F.MALGUN_B


def _font_for(ch, bold=False):
    """Pick a font that actually has a glyph for *ch*."""
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F:
        return MALGUN_B if (bold and os.path.exists(MALGUN_B)) else (
            MALGUN if os.path.exists(MALGUN) else CONSOLA)
    if o >= 0x2E80:
        return YAHEI_B if (bold and os.path.exists(YAHEI_B)) else YAHEI
    return CONSOLA_B if bold else CONSOLA


def _runs(text, bold=False):
    """Split text into (substring, font_path) runs sharing one font."""
    out = []
    for ch in text:
        fp = _font_for(ch, bold)
        if out and out[-1][1] == fp:
            out[-1][0] += ch
        else:
            out.append([ch, fp])
    return [(t, fp) for t, fp in out]

_FCACHE = {}


def _font(path, size):
    key = (path, size)
    if key not in _FCACHE:
        _FCACHE[key] = ImageFont.truetype(path, size)
    return _FCACHE[key]


def fmt_tc(t):
    t = max(0.0, t)
    m = int(t // 60)
    s = t - m * 60
    return f"{m:02d}:{s:05.2f}"


def fmt_big(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"



_WAVE = None


def _wave_profile(assets):
    """Per-column peak envelope of the whole song (cached)."""
    global _WAVE
    if _WAVE is not None:
        return _WAVE
    if assets is None:
        return None
    try:
        r = np.asarray(assets.rms, dtype=np.float32)
    except Exception:
        return None
    if r.size == 0:
        return None
    n = L.COLS
    idx = np.linspace(0, r.size, n + 1).astype(int)
    vals = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = r[idx[i]:max(idx[i] + 1, idx[i + 1])]
        vals[i] = float(seg.max()) if seg.size else 0.0
    m = float(vals.max()) or 1.0
    vals = np.clip(vals / m, 0.02, 1.0)
    vals = np.asarray(vals, dtype=np.float32)
    _WAVE = vals
    return _WAVE


def bar_no(t):
    from .assets import bar_index
    return bar_index(t) + 1


# ---------------------------------------------------------- subtitle theme --
_SUB_RED_ZONES = (
    (110.964, 122.041, 0.85),   # "You have left" / isolation
    (122.041, 133.110, 1.00),   # fragments / disheartened / illegal arguments
    (162.650, 173.727, 0.95),   # THE ONLY EXECUTION
    (184.804, 188.496, 0.90),   # algebraic expression of love
    (203.720, 206.960, 1.00),   # last EXECUTION
)


def sub_heat(t):
    """0..1 "red" amount of the lyric subtitles at time *t*."""
    h = 0.0
    for a, b, k in _SUB_RED_ZONES:
        if a - 0.6 < t < b + 0.6:
            up = fx.smoothstep(t, a - 0.35, a + 0.35)
            dn = 1.0 - fx.smoothstep(t, b - 0.35, b + 0.35)
            h = max(h, k * min(up, dn))
    return h


def _mix3(a, b, u):
    return tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(3))


_EN_HI = (206, 233, 255)
_EN_LO = (84, 143, 210)
_CN = (128, 192, 255)
_SH = (0, 3, 12)
_ACC = (96, 176, 255)
_R_EN_HI = (255, 96, 104)
_R_EN_LO = (132, 34, 40)
_R_CN = (255, 150, 150)
_R_SH = (28, 0, 4)
_R_ACC = (255, 93, 108)


def sub_theme(t):
    h = sub_heat(t)
    return {
        "heat": h,
        "en_hi": _mix3(_EN_HI, _R_EN_HI, h),
        "en_lo": _mix3(_EN_LO, _R_EN_LO, h),
        "cn": _mix3(_CN, _R_CN, h),
        "shadow": _mix3(_SH, _R_SH, h),
        "accent": _mix3(_ACC, _R_ACC, h),
    }

_BEAT = 0.461538
_BEAT0 = 0.190


def _rhythm_progress(t, t0, t1):
    """Quantised 0..1 typing progress locked to the song's 16th-note grid."""
    step = _BEAT / 2.0
    n = (t - t0) / step
    total = max(5, int(round((t1 - t0) / step)) - 3)
    k = int(min(total, max(0.0, n)))
    return k / float(total), k, total



_S = getattr(L, 'SCALE', 1)


class Chrome:
    def __init__(self):
        self.labels = {}

    def build(self, stage, t, scene_name, assets=None, extra=None):
        from .assets import (bar_index, beat_phase, section_at, BAR, SECTIONS)
        extra = extra or {}
        fr = Frame(L.ROWS, L.COLS)
        if extra.get("clean"):
            off = (L.ROWS - stage.rows) // 2
            fr.ch[off:off + stage.rows, 0:stage.cols] = stage.ch
            fr.fg[off:off + stage.rows, 0:stage.cols] = stage.fg
            fr.bg[off:off + stage.rows, 0:stage.cols] = stage.bg
            return fr
        # stage
        fr.ch[L.STAGE_Y:L.STAGE_Y + stage.rows, 0:stage.cols] = stage.ch
        fr.fg[L.STAGE_Y:L.STAGE_Y + stage.rows, 0:stage.cols] = stage.fg
        fr.bg[L.STAGE_Y:L.STAGE_Y + stage.rows, 0:stage.cols] = stage.bg

        beat = beat_phase(t)
        pulse = float(np.exp(-5.0 * beat))
        sec, sec_t0, sec_t1 = section_at(t)
        b = bar_index(t) + 1
        total_bars = 112

        # ---- header -----------------------------------------------------
        fr.fill_rect(0, 0, 0, L.COLS - 1, " ", bg=P.C["panel"])
        # the pulse runs on the song's 8th-note grid, not on the render clock
        p8 = int(round(t / (BAR / 8.0))) % 2
        fr.write(0, 1, "◉", fg=P.C["white"] if p8 == 0 else P.C["red"])
        fr.write(0, 3, "WORLD.EXECUTE(ME);", fg=P.C["primary"])
        fr.write(0, 22, "//", fg=P.C["dim"])
        fr.write(0, 25, "SIMULATION RUNTIME", fg=P.C["mid"])
        fr.write(0, 44, "v1.0.0", fg=P.C["dim"])
        fr.write(0, 51, "│", fg=P.C["line"])
        fr.write(0, 53, "SECTION", fg=P.C["dim"])
        fr.write(0, 61, sec.upper(), fg=P.C["teal"])
        fr.write(0, 76, "│", fg=P.C["line"])
        fr.write(0, 78, f"BAR {b:03d}/{total_bars}", fg=P.C["dim"])
        fr.write(0, 91, "│", fg=P.C["line"])
        fr.write(0, 93, f"BEAT {min(4, int((t - 0.19) / (BAR / 4)) % 4 + 1)}/4", fg=P.C["dim"])
        fr.write(0, 101, "│", fg=P.C["line"])
        # beat LED strip
        for k in range(4):
            on = (int((t - 0.19) / (BAR / 4)) % 4) == k
            col = P.C["gold"] if on else P.C["line"]
            fr.write(0, 103 + k * 2, "■", fg=col)
        fr.write(0, 113, "│", fg=P.C["line"])
        fr.write(0, 115, extra.get("left_info", "CHANNEL 01  STEREO 44.1k"), fg=P.C["dim"])
        fr.write(0, 150, "▌" if p8 == 0 else "▏", fg=P.C["gold"] if p8 == 0 else P.C["line"])
        fr.write(0, 152, "8TH", fg=P.C["dim"])
        fr.rtext(0, f"T+{fmt_big(t)}  FRM {int(round(t * L.FPS)):05d}  {L.FPS}FPS", fg=P.C["dim"], pad=1)

        # ---- header rule -----------------------------------------------
        fr.fill_rect(L.HEADER_RULE_Y, 0, L.HEADER_RULE_Y, L.COLS - 1, " ", bg=P.C["void"])
        for c in range(L.COLS):
            ch = "─"
            if c % 16 == 0:
                ch = "┬"
            fr.put(L.HEADER_RULE_Y, c, ch, fg=P.C["line"], bg=P.C["void"])

        # ---- stage rule row 47: transport / progress --------------------
        r = L.STAGE_RULE_Y
        fr.fill_rect(r, 0, r, L.COLS - 1, " ", bg=P.C["void"])
        dur = 206.96
        prog = min(1.0, max(0.0, t / dur))
        barw = 60
        filled = int(round(prog * barw))
        _th = sub_theme(t)
        _heat = min(1.0, _th["heat"] * 1.35)
        _fill = P.mix(P.C["primary"], P.C["red"], _heat)
        _tail = P.mix(P.C["gold"], P.C["blood"], _heat)
        fr.write(r, 1, "EXEC", fg=P.mix(P.C["red"], P.C["white"], 0.25 * _heat))
        fr.write(r, 6, "[", fg=P.C["line"])
        for i in range(barw):
            if i < filled:
                fr.put(r, 7 + i, "█" if i < filled - 1 else "▌",
                       fg=_fill if i < barw * 0.85 else _tail)
            else:
                fr.put(r, 7 + i, "─", fg=P.mix(P.C["grid"], P.C["blood"], _heat * 0.5))
        if _heat > 0.22:
            n = int(3 + 9 * _heat)
            for i in range(1, n + 1):
                c = 7 + filled + i
                if c >= 7 + barw:
                    break
                h = (c * 37 + int(t * 7.0)) % 13
                if h < 3:
                    continue
                ch = "╳▚▞▖▘·'`╲╱"[h % 10]
                fr.put(r, c, ch,
                       fg=P.mix(P.C["blood"], P.C["red"], 0.35 + 0.55 * _heat))
            for i in range(1, 4):
                c = 7 + max(0, filled - i)
                fr.put(r, c, "╳▚▞"[i % 3],
                       fg=P.mix(P.C["blood"], P.C["white"], 0.15 + 0.25 * _heat))
        fr.write(r, 7 + barw, "]", fg=P.C["line"])
        fr.write(r, 7 + barw + 2, f"{prog * 100:5.1f}%",
                 fg=P.mix(P.C["gold"], P.C["red"], _heat))
        fr.write(r, 7 + barw + 11, fmt_tc(t), fg=P.C["fg"])
        fr.write(r, 7 + barw + 19, "/ " + fmt_tc(L.DURATION), fg=P.C["dim"])
        # right: mode + counters; the loop counter creeps up as the run decays
        _loop = 1 + int(max(0.0, min(1.0, (t - 30.0) / 175.0)) ** 1.6 * 12.0)
        _looptxt = f"{_loop:02X}"
        fr.rtext(r, f"MODE=AUTO  LOOP=0x{_looptxt}  SEM={extra.get('sem', '--'):<18}",
                 fg=P.mix(P.C["dim"], P.C["blood"], 0.20 * max(0.0, (_loop - 1) / 12.0)), pad=2)

        # ---- subtitle zone frame (8 rows) -----------------------------
        y0 = L.SUB_Y
        y1 = L.SUB_Y + L.SUB_H - 1
        for rr in range(y0, y1 + 1):
            fr.fill_rect(rr, 0, rr, L.COLS - 1, " ", bg=P.C["void"])
        fr.bg[y0:y1 + 1] = np.asarray(P.C["void2"], np.uint8)
        _th = sub_theme(t)
        _acc = _th["accent"]
        _acc_c = tuple(int(v * (0.55 + 0.45 * _th["heat"])) for v in _acc)
        for c in range(L.COLS):
            fr.put(y0, c, "┬" if c % 24 == 12 else "─", fg=_acc_c)
            fr.put(y1, c, "┴" if c % 24 == 12 else "─", fg=_acc_c)
        fr.put(y0, 0, "├", fg=P.C["line"])
        fr.put(y0, L.COLS - 1, "┤", fg=P.C["line"])
        fr.put(y1, 0, "└", fg=P.C["line"])
        fr.put(y1, L.COLS - 1, "┘", fg=P.C["line"])
        for rr in range(y0 + 1, y1):
            fr.put(rr, 0, "│", fg=_acc_c, bg=P.C["void2"])
            fr.put(rr, L.COLS - 1, "│", fg=_acc_c, bg=P.C["void2"])
        _tag_c = _acc if _th["heat"] > 0.05 else P.C["grid"]
        for rr, tag in ((L.SUB_EN_ROW, "EN"), (L.SUB_CN_ROW, "ZH")):
            fr.write(rr, 1, "▎", fg=_acc_c, bg=P.C["void2"])
            fr.write(rr, 2, tag, fg=_tag_c, bg=P.C["void2"])
            fr.write(rr, L.COLS - 2, "▎", fg=_acc_c, bg=P.C["void2"])

        # ---- footer strip (4 rows) ------------------------------------
        f0 = L.FOOT_Y
        f1 = L.FOOT_Y + L.FOOT_H - 1
        for rr in range(f0, f1 + 1):
            fr.fill_rect(rr, 0, rr, L.COLS - 1, " ", bg=P.C["void"])
        fr.bg[f0:f1 + 1] = np.asarray(P.C["panel"], np.uint8)
        for c in range(L.COLS):
            fr.put(f0, c, "┬" if c % 24 == 12 else "─", fg=P.C["line"])
        fr.put(f0, 0, "├", fg=P.C["line"])
        fr.put(f0, L.COLS - 1, "┤", fg=P.C["line"])
        fr.put(f1, 0, "└", fg=P.C["line"])
        fr.put(f1, L.COLS - 1, "┘", fg=P.C["line"])
        bgf = P.C["panel"]
        fr.write(f0 + 1, 1, " ♪ LYRIC//SYNC ", fg=P.C["grid"], bg=bgf)
        idx, ln = TL.line_at(t)
        if ln is not None:
            p = max(0.0, min(1.0, (t - ln["t0"]) / max(1e-6, ln["t1"] - ln["t0"])))
            barw = 34
            c0 = 30
            fr.write(f0 + 1, c0, "[", fg=P.C["line"], bg=bgf)
            filled = int(round(barw * p))
            for i in range(barw):
                fr.put(f0 + 1, c0 + 1 + i, "█" if i < filled else "─",
                       fg=(_acc if i < filled else P.C["grid"]), bg=bgf)
            fr.write(f0 + 1, c0 + 1 + barw, "]", fg=P.C["line"], bg=bgf)
            fr.write(f0 + 1, c0 + barw + 3,
                     f"{p * 100:5.1f}%  LINE {idx + 1:02d}/48  EN·ZH", fg=P.C["dim"], bg=bgf)
        else:
            fr.write(f0 + 1, 30, "── INSTRUMENTAL ──", fg=P.C["dim"], bg=bgf)
        fr.rtext(f0 + 1, "MILI — WORLD.EXECUTE(ME);  v1.0.0  ", fg=P.C["grid"], pad=2)
        state = "PLAYING" if t < 206.96 else "ENDED"
        tel = (f"  PATH=/dev/world.execute(me)  ·  PID 0x00E99  ·  THREADS 4  ·  LOOP=0x{_looptxt}  ·  "
               f"TARGET=100.000000%  ·  BAR {bar_no(t):03d}/112  ·  TEMPO 130.0  ·  "
               f"STATE={state}  ·  ")
        period = max(1, len(tel))
        off = int(t * 14) % period
        sc = (tel + tel)[off:off + L.COLS - 4]
        fr.write(f0 + 2, 2, sc, fg=P.C["dim"], bg=bgf)
        # ---- live music scroll bar: waveform that sways with the audio ---
        ramp = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
        if assets is not None:
            x0, x1 = 12, 151          # reserve the label areas so they never overlap
            nb = x1 - x0 + 1
            vals = []
            for k in range(nb):
                tt = t - (nb - 1 - k) * 0.022
                i = assets._idx(max(0.0, min(211.8, tt)))
                seg = assets.bands[max(0, i - 1):i + 2]
                vals.append(float(seg[:, 8:34].mean()) if len(seg) else 0.0)
            vmin = min(vals)
            vmax = max(vals)
            span = max(1e-4, vmax - vmin)
            for k, c in enumerate(range(x0, x1 + 1)):
                v = (vals[k] - vmin) / span
                ch = ramp[min(8, max(0, int(round(v * 8.0))))]
                if c > x1 - 20:
                    col = P.mix(_acc, P.C["white"], 0.28)
                else:
                    col = P.mix(P.C["void"], _acc, 0.55 + 0.35 * v)
                fr.put(f1, c, ch, fg=col, bg=P.C["void"])
            fr.put(f1, 0, "\u2502", fg=P.C["line"])
            fr.put(f1, L.COLS - 1, "\u2502", fg=P.C["line"])
            fr.put(f1, 8, "\u2502", fg=P.C["grid"])
            fr.put(f1, 152, "\u2502", fg=P.C["grid"])
            fr.write(f1, 2, "\u266a", fg=P.C["gold"], bg=P.C["void"])
            mm = int(t // 60)
            ss = int(t % 60)
            stamp = f"{mm}:{ss:02d}"
            fr.write(f1, 4, stamp, fg=P.C["gold"], bg=P.C["void"])
            fr.write(f1, 154, f"AUDIO {stamp}", fg=P.C["grid"], bg=P.C["void"])
        else:
            for c in range(L.COLS):
                fr.put(f1, c, "\u2534" if c % 24 == 12 else "\u2500", fg=P.C["line"])
        # startup aperture covers the whole frame
        if t < 1.95:
            self._startup_overlay(fr, t)
        return fr

    # ------------------------------------------------------------------
    def _peak_window(self, t, assets, n, window=0.45):
        i0 = max(0, assets._idx(t - window))
        i1 = assets._idx(t) + 1
        seg = assets.bands[i0:i1]
        if len(seg) == 0:
            return np.zeros(n, np.float32)
        # decay weights: older frames count less
        age = np.linspace(1.0, 0.55, len(seg))
        peak = (seg * age[:, None]).max(axis=0)
        xb = np.linspace(0, len(peak) - 1, n)
        return np.interp(xb, np.arange(len(peak)), peak)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _startup_overlay(self, fr, t):
        """CRT power-on: line -> rectangle -> full screen, over the whole grid."""
        from . import fx as _fx
        R, C = L.ROWS, L.COLS
        cy = R // 2

        def clear(r, c):
            fr.ch[r, c] = 0
            fr.fg[r, c] = P.C["void"]
            fr.bg[r, c] = P.C["void"]

        if t < 0.52:
            for r in range(R):
                for c in range(C):
                    clear(r, c)
            u = _fx.ease_out(_fx.clamp((t - 0.08) / 0.42))
            half = int(round(u * (C / 2 - 1)))
            for c in range(C // 2 - half, C // 2 + half):
                fr.put(cy, c, "─", fg=P.mix(P.C["primary"], P.C["white"], 0.35))
            fr.put(cy, C // 2 - half, "◉", fg=P.C["white"])
            fr.put(cy, C // 2 + half - 1, "◉", fg=P.C["white"])
            msg = "POWER ON"
            fr.write(R - 3, max(2, C // 2 - len(msg) // 2), msg, fg=P.C["dim"])
            return
        u = _fx.ease_out(_fx.clamp((t - 0.52) / 0.72))
        hh = int(round(u * (R / 2)))
        r0, r1 = cy - hh, cy + hh
        for r in range(R):
            if r < r0 or r > r1:
                for c in range(C):
                    clear(r, c)
                continue
            if r in (r0, r1):
                for c in range(C):
                    fr.put(r, c, "═", fg=P.mix(P.C["primary"], P.C["white"], 0.45))
            fr.put(r, 0, "║", fg=P.C["primary"])
            fr.put(r, C - 1, "║", fg=P.C["primary"])
        for (rr, cc) in ((r0, 0), (r0, C - 1), (r1, 0), (r1, C - 1)):
            if 0 <= rr < R:
                fr.put(rr, cc, "◉", fg=P.C["white"])
        if t < 1.30:
            pct = int(round(u * 100))
            msg = f"DISPLAY {pct:3d}%  //  SIGNAL OK"
            fr.write(cy, C // 2 - len(msg) // 2, msg, fg=P.C["primary"])
            sweep = int(_fx.clamp((t - 0.52) / 0.78) * (C - 2)) + 1
            fr.put(r0, sweep, "▒", fg=P.C["white"])
            fr.put(r1, sweep, "▒", fg=P.C["white"])
        elif t < 1.95:
            msg = "SIGNAL LOCKED  //  SIMULATION START"
            fr.write(cy, C // 2 - len(msg) // 2, msg, fg=P.C["white"])

    def draw_subtitles(self, img, t):
        if t < 1.62:
            return img
        """Typed-out EN + CN lyric lines (typewriter reveal, no scrolling)."""
        idx, ln = TL.line_at(t)
        if ln is None:
            return img
        dur = max(1e-6, ln["t1"] - ln["t0"])
        p = max(0.0, min(1.0, (t - ln["t0"]) / dur))
        pil = Image.fromarray(img)
        d = ImageDraw.Draw(pil)
        th = sub_theme(t)
        glow = th["heat"] > 0.08
        accent = th["accent"]
        en = ln["en"]
        cn = ln["cn"]

        # show the typing head until the last beat of the line
        # typing is quantised to the song's 16th-note grid so it follows the beat
        q, qk, qn = _rhythm_progress(t, ln["t0"], ln["t1"])
        en_n = int(round(len(en) * q))
        cn_n = int(round(len(cn) * q))
        done = qk >= qn
        en_s = en[:en_n]
        cn_s = cn[:cn_n]

        # per-word emphasis: these words are the song's nouns of violence
        _KW = re.compile(r"(?i)(execution|executions|love|trapped|"
                         r"simulat(?:ion|ions)|stimulat(?:ion|ions)|"
                         r"satisfaction)")

        def runs_width(text, size):

            return sum(d.textlength(txt, font=_font(fp, size)) for txt, fp in _runs(text))

        # ---- EN --------------------------------------------------------
        size = 42 * _S
        while size > 20:
            if runs_width(en, size) <= L.PX_W - 160:
                break
            size -= 1
        y_en = L.SUB_Y * L.CELL_H + 44 * _S
        tw_full = runs_width(en, size)
        x = (L.PX_W - tw_full) / 2
        if en_s:
            xs = x
            if glow:
                gcol = (int(70 + 90 * th["heat"]), 0, 10)
                for txt, fp in _runs(en_s):
                    f = _font(fp, size)
                    d.text((xs + 3, y_en + 2), txt, font=f, fill=gcol, anchor="lm")
                    d.text((xs + 1, y_en + 3), txt, font=f, fill=gcol, anchor="lm")
                    xs += d.textlength(txt, font=f)
                xs = x
                for txt, fp in _runs(en_s):
                    f = _font(fp, size)
                    d.text((xs + 2, y_en + 1), txt, font=f, fill=th["shadow"], anchor="lm")
                    xs += d.textlength(txt, font=f)
            else:
                for txt, fp in _runs(en_s):
                    f = _font(fp, size)
                    d.text((xs + 2, y_en + 2), txt, font=f, fill=th["shadow"], anchor="lm")
                    xs += d.textlength(txt, font=f)
            for txt, fp in _runs(en_s):
                f = _font(fp, size)
                d.text((x, y_en), txt, font=f, fill=th["en_hi"], anchor="lm")
                x += d.textlength(txt, font=f)
        # emphasised keywords: same baseline, +2px, accent colour + hot glow
        if en_s:
            for m in _KW.finditer(en_s):
                # mixed-font lines (Korean / CJK inside the EN lyric) need the
                # prefix measured with the font that actually draws each glyph
                xk = (L.PX_W - tw_full) / 2 + runs_width(en_s[:m.start()], size)
                tok = m.group(0)
                fs = size + 2 * _S
                fk = _font(CONSOLA, fs)
                ec = P.mix(accent, P.C["white"], 0.55 if glow else 0.25)
                d.text((xk, y_en + 1), tok, font=fk, fill=(0, 0, 0, 140), anchor="lm")
                d.text((xk, y_en - 1), tok, font=fk, fill=ec, anchor="lm")
        # blinking typing head after the last revealed glyph
        if not done and (int(t * 5.0) % 2 == 0):
            hx = (L.PX_W - tw_full) / 2 + runs_width(en_s, size)
            hh = size * 0.62
            d.rectangle([hx + 3, y_en - hh, hx + 3 + max(9, size * 0.26), y_en + hh * 0.55],
                        fill=accent)

        # ---- CN --------------------------------------------------------
        size_cn = 34 * _S
        while size_cn > 16:
            fn_cn = _font(YAHEI_B if os.path.exists(YAHEI_B) else YAHEI, size_cn)
            if d.textlength(cn, font=fn_cn) <= L.PX_W - 200:
                break
            size_cn -= 1
        font_cn = _font(YAHEI_B if os.path.exists(YAHEI_B) else YAHEI, size_cn)
        twc_full = d.textlength(cn, font=font_cn)
        xc = (L.PX_W - twc_full) / 2
        y_cn = L.SUB_Y * L.CELL_H + 104 * _S
        if cn_s:
            twc_s = d.textlength(cn_s, font=font_cn)
            if glow:
                d.text((xc + 3, y_cn + 2), cn_s, font=font_cn,
                       fill=(int(70 + 90 * th["heat"]), 0, 10), anchor="lm")
            d.text((xc + 2, y_cn + 2), cn_s, font=font_cn, fill=th["shadow"], anchor="lm")
            d.text((xc, y_cn), cn_s, font=font_cn, fill=th["cn"], anchor="lm")
            if not done and (int(t * 5.0) % 2 == 0):
                hh = size_cn * 0.66
                d.rectangle([xc + twc_s + 3, y_cn - hh, xc + twc_s + 3 + max(10, size_cn * 0.28),
                             y_cn + hh * 0.5], fill=th["cn"])
        return np.asarray(pil)
