"""s01_boot - the world (and the machine) switching itself on.

0.190 - 3.882  switch on the power line / put on protection
3.882 - 7.575  lay down your pieces / object creation
7.575 - 11.267 fill in my data, parameters, initialization
11.267 - 14.960 setup our new world / begin the simulation
"""
from __future__ import annotations

import math

import numpy as np

from .. import fx
from .. import palette as P
from .. import timeline as TL
from .. import widgets as W

PANEL = P.C["panel"]
PANEL2 = P.C["panel2"]
CONSOLE_TOP = 34


def draw(ctx):
    t = ctx.t
    fr = ctx.frame()
    _backdrop(fr, ctx)
    if t < 3.882:
        _power(fr, ctx)
    elif t < 7.575:
        _objects(fr, ctx)
    elif t < 11.267:
        _data(fr, ctx)
    else:
        _world(fr, ctx)
    _console(fr, ctx)
    if t > 14.15:
        g = fx.smoothstep(t, 14.15, 14.96)
        ctx.set_glitch(0.12 + 0.35 * g)
        ctx.meta["flash"] = 0.7 * fx.smoothstep(t, 14.62, 14.96)
        ctx.meta["flash_color"] = P.C["primary"]
    return fr



# ------------------------------------------------------- startup aperture --
def _startup(fr, ctx):
    """Power-on: a bright line opens into a rectangle, then fills the screen."""
    t = ctx.t
    R, C = fr.rows, fr.cols
    cy = R // 2
    if t >= 1.95:
        return
    # 1) line grows horizontally 0.00-0.55 s
    w = fx.ease_out(fx.clamp(t / 0.55))
    half = int(w * (C // 2))
    hh = 0.0
    if t > 0.55:                      # 2) line opens vertically 0.55-1.25 s
        hh = fx.ease_out(fx.clamp((t - 0.55) / 0.70)) * (R / 2)
    # 3) overshoot flash 1.25-1.95 s, then gone
    flash = fx.smoothstep(t, 1.25, 1.45) * (1.0 - fx.smoothstep(t, 1.55, 1.95))
    r0 = max(0, int(round(cy - hh)))
    r1 = min(R - 1, int(round(cy + hh)))
    c0 = max(0, C // 2 - half)
    c1 = min(C - 1, C // 2 + half)
    # black outside the aperture
    for r in range(R):
        if r < r0 or r > r1:
            for c in range(C):
                fr.put(r, c, " ", fg=P.C["void"], bg=P.C["void"])
        else:
            for c in list(range(0, c0)) + list(range(c1 + 1, C)):
                fr.put(r, c, " ", fg=P.C["void"], bg=P.C["void"])
    # bright edges of the aperture
    edge = P.mix(P.C["primary"], P.C["white"], 0.35 + 0.3 * flash)
    for c in range(c0, c1 + 1):
        fr.put(r0, c, "─", fg=edge, bg=P.C["void"])
        fr.put(r1, c, "─", fg=edge, bg=P.C["void"])
    for r in range(r0, r1 + 1):
        fr.put(r, c0, "│", fg=edge, bg=P.C["void"])
        fr.put(r, c1, "│", fg=edge, bg=P.C["void"])
    for rr, cc in ((r0, c0), (r0, c1), (r1, c0), (r1, c1)):
        fr.put(rr, cc, "◉", fg=P.C["gold"], bg=P.C["void"])
    # scan line travelling inside the aperture
    if r1 > r0:
        sr = r0 + int(((t * 2.6) % 1.0) * (r1 - r0))
        for c in range(c0, c1 + 1):
            fr.put(sr, c, "═", fg=P.mix(P.C["primary"], P.C["void"], 0.45),
                   bg=P.C["void"])
    # power-on caption below the aperture
    if half > 6:
        tx = f"POWER ON  //  DISPLAY {int(100 * (half / (C / 2))):3d}%  //  SIGNAL OK"
        fr.write(max(0, r1 + 2), max(0, C // 2 - len(tx) // 2), tx,
                 fg=P.C["primary"])


# ------------------------------------------------------------------ shared --
def _backdrop(fr, ctx):
    t = ctx.t
    # dot lattice
    for r in range(0, fr.rows, 2):
        for c in range(r % 4, fr.cols, 4):
            fr.put(r, c, "·", fg=P.mix(P.C["void"], P.C["line"], 0.5))
    # data drizzle in the gutters
    W.matrix_rain(fr, t, seed=11, density=0.24, speed=5.5, fg=P.C["green"],
                  region=(0, 0, CONSOLE_TOP - 1, 22))
    W.matrix_rain(fr, t, seed=12, density=0.24, speed=4.6, fg=P.C["green"],
                  region=(0, 170, CONSOLE_TOP - 1, fr.cols - 1))
    _scanline(fr, ctx)
    # breadcrumb + clock
    phase = ("01 POWER LINE", "02 OBJECT CREATION", "03 DATA PARAMETERS",
             "04 WORLD SETUP")[min(3, int(fx.clamp(ctx.local / 3.88)))]
    fr.write(0, 2, "┤ INTRO", fg=P.C["primary"])
    fr.write(0, 10, "::", fg=P.C["dim"])
    fr.write(0, 13, phase, fg=P.C["gold"])
    fr.write(0, 44, "│", fg=P.C["line"])
    fr.write(0, 46, "SWITCH ON THE POWER LINE / REMEMBER TO PUT ON PROTECTION",
             fg=P.C["dim"])
    fr.rtext(0, f"T+00:{ctx.t:06.3f}   FRM {ctx.fi:05d}   STAGE 0/9", fg=P.C["dim"], pad=2)
    # corner ticks
    for (r, c, dr, dc) in ((2, 1, 1, 1), (2, fr.cols - 2, 1, -1),
                           (CONSOLE_TOP - 2, 1, -1, 1), (CONSOLE_TOP - 2, fr.cols - 2, -1, -1)):
        for k in range(4):
            fr.put(r + dr * k, c, "│", fg=P.mix(P.C["line"], P.C["void"], 0.3))
            fr.put(r, c + dc * k, "─", fg=P.mix(P.C["line"], P.C["void"], 0.3))
    # boot percentage
    pct = (ctx.local / max(1e-6, ctx.dur)) * 100.0
    fr.write(CONSOLE_TOP - 2, 8, f"BOOT {pct:5.1f}%", fg=P.C["dim"])


def _panel(fr, r0, c0, r1, c1, title=None, fg=None, style=1, bg=None):
    fg = fg or P.C["line"]
    fr.box(r0, c0, r1, c1, style=style, fg=fg, bg=bg or P.C["void"])
    if title:
        fr.write(r0, c0 + 2, f"┤ {title} ├", fg=P.C["primary"])
    return r0, c0


def _kv(fr, r, c, key, val, kfg=None, vfg=None, klen=10):
    fr.write(r, c, key.ljust(klen), fg=kfg or P.C["dim"])
    fr.write(r, c + klen, val, fg=vfg or P.C["fg"])


def _scanline(fr, ctx):
    sy = int((ctx.t * 20) % (CONSOLE_TOP + 6)) - 3
    if 0 <= sy < CONSOLE_TOP:
        for c in range(0, fr.cols, 3):
            fr.put(sy, c, "─", fg=P.mix(P.C["primary"], P.C["void"], 0.86))
        fr.write(sy, 0, "◀", fg=P.mix(P.C["primary"], P.C["void"], 0.5))


# ------------------------------------------------------------- console bar --
_LOGS = {
    0: ["[ ok ] power line switched on",
        "[ ok ] protection shield: enabled",
        "[ ok ] voltage regulator: 48.0V",
        "[ ok ] grounding check: PASS",
        "[ .. ] waiting for object creation"],
    1: ["[ ok ] object slots allocated: 52",
        "[ ok ] pieces falling in",
        "[ ok ] lattice binding on beat",
        "[ .. ] collision test: 0 faults"],
    2: ["[ ok ] parameter table loaded",
        "[ ok ] memory allocated: 0x7FF2A0",
        "[ ok ] sensors linked",
        "[ .. ] initialising kernel"],
    3: ["[ ok ] new world constructed",
        "[ ok ] gravity: 0x0148",
        "[ ok ] simulation kernel: START",
        "[ !! ] entering title sequence"],
}


def _console(fr, ctx):
    t = ctx.t
    r0 = CONSOLE_TOP
    fr.fill_rect(r0, 0, fr.rows - 1, fr.cols - 1, " ", bg=P.C["black"])
    fr.hline(r0, 0, fr.cols - 1, "═", fg=P.C["mid"])
    # three sub panels
    _panel(fr, r0 + 1, 1, 44, 86, title="EVENT LOG", fg=P.C["line"], bg=P.C["black"])
    _panel(fr, r0 + 1, 88, 44, 138, title="SIGNAL", fg=P.C["line"], bg=P.C["black"])
    _panel(fr, r0 + 1, 140, 44, fr.cols - 2, title="STATUS", fg=P.C["line"],
           bg=P.C["black"])
    # log lines
    ph = 0 if t < 3.882 else 1 if t < 7.575 else 2 if t < 11.267 else 3
    logs = _LOGS.get(ph, [])
    n = min(len(logs), 1 + int((ctx.local % 3.88) * 2.2))
    for i in range(min(n, 4)):
        ln = logs[i]
        col = P.C["green"] if "[ ok" in ln else (P.C["gold"] if "[ .." in ln else P.C["primary"])
        fr.write(r0 + 2 + i, 3, ln, fg=P.C["dim"] if i < n - 1 else col)
    if int(t * 5) % 2 == 0 and n < 4:
        fr.put(r0 + 2 + n, 3, "█", fg=P.C["primary"])
    # signal scope
    a = ctx.assets
    hop = 1 / 30.0
    vals = [a.rms_at(max(0.0, min(211.9, t - 30 * hop + i * hop)))
            for i in range(30)]
    mx = max(0.05, max(vals))
    vals = [v / mx for v in vals]
    W.sparkline(fr, r0 + 3, 90, vals, 6, fg=P.C["primary"])
    fr.write(r0 + 2, 90, f"RMS {a.rms_at(t):5.3f}", fg=P.C["teal"])
    fr.write(r0 + 2, 104, f"PEAK {mx:5.3f}", fg=P.C["dim"])
    fr.write(r0 + 10, 90, "WAVEFORM / 30 SAMPLES / AGC ON", fg=P.C["dim"])
    # status block
    c = 142
    _kv(fr, r0 + 2, c, "KERNEL", "init", klen=9, vfg=P.C["gold"])
    _kv(fr, r0 + 3, c, "MEMORY", "0x7FF2A0", klen=9, vfg=P.C["fg"])
    _kv(fr, r0 + 4, c, "OBJECTS", "39 / 39", klen=9, vfg=P.C["teal"])
    _kv(fr, r0 + 5, c, "PARAMS", "12 / 12", klen=9, vfg=P.C["teal"])
    _kv(fr, r0 + 6, c, "TEMP", f"{34 + int(fx.noise1d(t * 0.7, 3) * 3)}.2 C",
       klen=9, vfg=P.C["mid"])
    W.progress_bar(fr, r0 + 8, c, 20, fx.clamp(ctx.local / max(1e-6, ctx.dur) * 1.06), fg=P.C["gold"],
                   show_pct=True)
    W.progress_bar(fr, r0 + 9, c, 20, fx.clamp(0.4 + 0.55 * ctx.pulse), fg=P.C["primary"],
                   show_pct=False)
    fr.write(r0 + 9, c + 22, "CPU", fg=P.C["dim"])


# ---------------------------------------------------------------- phase 01 --
def _power(fr, ctx):
    t = ctx.t
    # left voltage rail
    _panel(fr, 2, 2, 19, 11, title="AC", fg=P.C["line"])
    fr.write(3, 4, "VOLTAGE", fg=P.C["dim"])
    lvl = fx.clamp((t - 0.15) / 0.9)
    for k in range(16):
        r = 18 - k
        on = k / 16 < lvl * (0.55 + 0.4 * ctx.rms)
        fr.write(r, 4, f"{int(k / 16 * 260):3d}", fg=P.C["dim"] if not on else P.C["mid"])
        fr.write(r, 8, "█" if on else "░", fg=P.C["red"] if on else P.mix(P.C["line"], P.C["void"], 0.6))
    fr.write(20, 3, f"{int(220 * lvl):3d}V", fg=P.C["gold"])
    # bus + stations
    bus_r = 19
    x0, x1 = 14, fr.cols - 14
    fr.hline(bus_r, x0, x1, "═", fg=P.mix(P.C["cyan2"], P.C["void"], 0.2))
    for c in range(x0, x1 + 1, 12):
        fr.put(bus_r, c, "╬", fg=P.C["cyan2"])
    head = x0 + int(fx.ease_out(fx.clamp(t / 3.4)) * (x1 - x0))
    for k in range(7):
        x = x0 + int((t * (30 + 3 * k) + k * 29) % (x1 - x0))
        fr.put(bus_r, x, "█", fg=P.C["white"])
        fr.put(bus_r, x - 1, "▓", fg=P.C["primary"])
        fr.put(bus_r, x + 1, "▓", fg=P.C["primary"])
        fr.put(bus_r - 1, x, "⚡", fg=P.C["gold"])
        fr.put(bus_r + 1, x, "╨", fg=P.mix(P.C["gold"], P.C["void"], 0.5))
    fr.write(bus_r + 2, max(x0 + 2, head - 2), "▶▶", fg=P.C["gold"])
    fr.write(16, 60, "┤ AC BUS 220V 50Hz ├", fg=P.C["primary"])
    fr.write(16, 84, "LOAD 12.4A", fg=P.C["dim"])
    # telemetry stream above the bus keeps the run-up moving
    for k in range(14):
        x = x0 + int((t * (18.0 + 4.5 * k) + k * 27) % (x1 - x0))
        rr = 17 + (k % 2)
        fr.put(rr, x, "·" if k % 3 else "+", fg=P.mix(P.C["primary"], P.C["void"], 0.45))
        if k % 4 == 0:
            fr.put(rr, x + 1, "▸", fg=P.mix(P.C["gold"], P.C["void"], 0.35))
    # protection shield encloses the bus
    if t > 1.0:
        a = fx.smoothstep(t, 1.0, 1.8)
        for c in range(10, fr.cols - 9, 2):
            fr.put(14, c, "═", fg=P.mix(P.C["primary"], P.C["void"], 0.45 * a))
            fr.put(23, c, "═", fg=P.mix(P.C["primary"], P.C["void"], 0.45 * a))
        for r in range(14, 24):
            fr.put(r, 10, "║", fg=P.mix(P.C["primary"], P.C["void"], 0.45 * a))
            fr.put(r, fr.cols - 10, "║", fg=P.mix(P.C["primary"], P.C["void"], 0.45 * a))
        fr.write(14, 13, "┤ PROTECTION SHIELD ├", fg=P.C["gold"])
        fr.write(14, fr.cols - 30, "GROUNDED", fg=P.C["green"])
    # stations above the bus
    stations = [("AC IN", "220V / 50Hz", "ac"), ("TRANSFORMER", "STEP-DOWN 48V", "tr"),
                ("DC OUT", "48V / 12A", "dc")]
    for i, (name, spec, kind) in enumerate(stations):
        c0 = 14 + i * 54
        c1 = c0 + 34
        r0, r1 = 4, 13
        active = head > c0 + 6
        fg = P.C["primary"] if active else P.C["line"]
        _panel(fr, r0, c0, r1, c1, title=name, fg=fg)
        fr.write(r0 + 2, c0 + 3, spec, fg=P.C["mid"])
        fr.write(r0 + 2, c1 - 9, "LIVE" if active else "IDLE",
                 fg=P.C["green"] if active else P.C["dim"])
        for k in range(26):
            x = c0 + 3 + k
            if kind == "ac":
                v = math.sin((k * 0.5) + t * 7) * 1.4
            elif kind == "dc":
                v = 1.3 if active else 0.0
            else:
                v = math.sin((k * 0.5) + t * 7) * (1.4 if active else 0)
            rr = int(round(r0 + 6 - v))
            if fr.inb(rr, x):
                fr.put(rr, x, "●" if k % 3 == 0 else "─",
                       fg=P.C["teal"] if active else P.C["line"])
        load = fx.clamp((t - 0.3) / 3.0 + i * 0.12)
        W.progress_bar(fr, r0 + 8, c0 + 3, 24, load * (0.35 + 0.6 * (i + 1) / 3),
                       fg=P.C["gold"], show_pct=False)
        fr.write(r0 + 8, c0 + 29, f"{int(load * 100 * (i + 1) / 3):3d}%", fg=P.C["dim"])
    # right meter panel
    _panel(fr, 2, 158, 13, fr.cols - 3, title="METER", fg=P.C["line"])
    fr.write(3, 160, "PWR  ", fg=P.C["red"])
    fr.write(3, 165, f"{40 + int(fx.noise1d(t * 3, 2) * 4)}.2 V", fg=P.C["gold"])
    fr.write(4, 160, "FREQ ", fg=P.C["dim"])
    fr.write(4, 165, "50.00 Hz", fg=P.C["teal"])
    fr.write(5, 160, "ROLE ", fg=P.C["dim"])
    fr.write(5, 165, "PROTECTED", fg=P.C["green"])
    fr.write(6, 160, "LOAD ", fg=P.C["dim"])
    fr.write(6, 165, f"{int(20 + t * 9)} %", fg=P.C["mid"])
    W.progress_bar(fr, 8, 160, 24, fx.clamp(0.2 + t * 0.2), fg=P.C["red"],
                   show_pct=False)
    W.progress_bar(fr, 11, 160, 24, fx.clamp(0.1 + t * 0.22), fg=P.C["gold"],
                   show_pct=False)
    # big volts under the bus
    fr.paint_text("220V", 25, 86, 3, fg=P.C["gold"], fg2=P.C["white"], align="center")
    # checklist + log
    _panel(fr, 21, 2, 32, 40, title="SAFETY", fg=P.C["line"])
    checks = ["protection shield", "grounding", "insulation", "overvoltage",
              "emergency stop"]
    for i, ck in enumerate(checks):
        done = t > 0.5 + i * 0.45
        fr.write(23 + i, 4, "✓" if done else "·", fg=P.C["green"] if done else P.C["dim"])
        fr.write(23 + i, 6, ck, fg=P.C["fg"] if done else P.C["dim"])
    _panel(fr, 21, 136, 32, fr.cols - 3, title="NEURAL BUS", fg=P.C["line"])
    W.braille_plot(fr, 23, 138, 50, 8,
                   [fx.noise1d(t * 3 + i * 0.2, 4) for i in range(50)],
                   fg=P.C["primary"])


    # centre-bottom scope: phase waveform + EQ bars (fills the empty middle)
    _panel(fr, 21, 44, 32, 134, title="PHASE SCOPE", fg=P.C["primary"])
    base_r = 26
    for c in range(46, 133):
        v = (math.sin(c * 0.24 + t * 6.3) * 0.55
             + math.sin(c * 0.081 - t * 2.6) * 0.35
             + math.sin(c * 0.42 + t * 11.0) * 0.10)
        h = max(1, int(round(abs(v) * 3.2 + 0.4)))
        for q in range(h):
            ch = "█" if q == h - 1 else ("▓" if q > h - 3 else "░")
            fr.put(base_r - q, c, ch,
                   fg=P.mix(P.C["primary"], P.C["void"], 0.30 + 0.50 * (q / max(1, h))))
    fr.hline(base_r + 1, 46, 132, "─", fg=P.mix(P.C["line"], P.C["void"], 0.5))
    fr.write(22, 46, f"FREQ {120 + int(26 * math.sin(t)):3d}Hz  RMS {ctx.rms:.3f}  PHASE A-B-C  LIVE",
             fg=P.C["mid"])
    for k in range(17):
        c = 47 + k * 5
        h = max(1, int(3.4 * abs(math.sin(t * 5.0 + k * 0.7)) * (0.5 + 1.1 * ctx.rms) + 0.6))
        for q in range(h):
            ch = "█" if q == h - 1 else ("▓" if q > h - 3 else "░")
            fr.put(30 - q, c, ch, fg=P.mix(P.C["gold"], P.C["primary"], 0.25 + 0.1 * (k % 4)))
    fr.write(31, 47, "CH1 50Hz  CH2 60Hz  CH3 400Hz   SAMPLES 4096   WINDOW HANN   FFT 1024",
             fg=P.C["dim"])


# ---------------------------------------------------------------- phase 02 --
_OBJECTS = None


def _object_defs():
    global _OBJECTS
    if _OBJECTS is None:
        glyphs = "◆■●▲▼◀▶★✦✧⚡♥♪∞◈○◇"
        objs = []
        cols, rows = 20, 3
        for i in range(cols * rows):
            x = 8 + (i % cols) * 9
            y = 10 + (i // cols) * 5
            g = glyphs[i % len(glyphs)]
            objs.append((x, y, g, fx.hash01(i, 7) * 1.9, i))
        _OBJECTS = objs
    return _OBJECTS


def _objects(fr, ctx):
    t = ctx.t
    lt = t - 3.882
    objs = _object_defs()
    fr.write(7, 3, "┤ OBJECT CREATION", fg=P.C["primary"])
    fr.write(7, 24, f"// PIECES {len(objs)}   LATTICE: PENDING", fg=P.C["dim"])
    fr.write(7, fr.cols - 46, "OBJECT CLASS INSTANCES", fg=P.C["dim"])
    fr.paint_text("OBJECT CREATION", 1, 96, 5, fg=P.C["primary"], fg2=P.C["teal"],
                  align="center")
    # drop zones: a crosshair slot per landing cell, turning into a lit cluster
    landed_n = 0
    for (x, y, g, delay, i) in objs:
        start = delay * 0.5
        p = fx.clamp((lt - start) / 0.8)
        if p <= 0.0:
            fr.put(y, x, "⌖", fg=P.mix(P.C["void"], P.C["line"], 0.65))
            fr.put(y, x - 1, "─", fg=P.mix(P.C["void"], P.C["line"], 0.35))
            fr.put(y, x + 1, "─", fg=P.mix(P.C["void"], P.C["line"], 0.35))
            continue
        e = fx.ease_out_back(p, 1.15)
        yy = int(round(fx.lerp(-14, y, e)))
        landed = p >= 0.999
        if landed:
            landed_n += 1
        # trail behind the falling piece
        if not landed:
            for k in range(1, 6):
                rr = yy - k * 2
                if fr.inb(rr, x):
                    fr.put(rr, x, "░", fg=P.mix(P.C["primary"], P.C["void"], 0.45 + k * 0.07))
            if fr.inb(yy - 1, x + 1):
                fr.put(yy - 1, x + 1, "▓", fg=P.mix(P.C["primary"], P.C["void"], 0.6))
        fg = P.C["white"] if landed else P.mix(P.C["primary"], P.C["white"], 0.35)
        if fr.inb(yy, x):
            fr.put(yy, x, g, fg=fg)
        if landed and fr.inb(yy, x - 1):
            fr.put(yy, x - 1, "[", fg=P.mix(P.C["teal"], P.C["white"], 0.6))
            fr.put(yy, x + 1, "]", fg=P.mix(P.C["teal"], P.C["white"], 0.6))
            for dc in (-1, 0, 1):
                fr.put(yy + 1, x + dc, "▁", fg=P.mix(fg, P.C["void"], 0.55))
            fr.put(yy - 1, x, "▔", fg=P.mix(fg, P.C["void"], 0.35))
            if i == landed_n - 1:
                fr.write(yy - 1, x - 2, f"0x{i:02X}", fg=P.mix(P.C["gold"], P.C["void"], 0.35))
    # lattice
    if landed_n > 10:
        a = fx.clamp((landed_n - 10) / 30)
        for (x, y, g, d, idx) in objs:
            if idx % 20 < 19:
                W.line_cells(fr, y + 1, x + 1, y + 1, x + 8,
                             fg=P.mix(P.C["line"], P.C["primary"], a * 0.6), ch="·")
            if idx + 20 < len(objs):
                W.line_cells(fr, y + 1, x, y + 4, x,
                             fg=P.mix(P.C["line"], P.C["primary"], a * 0.6), ch="·")
    # right rail: object class list + counters
    _panel(fr, 2, 168, 32, fr.cols - 2, title="CLASSES", fg=P.C["line"])
    classes = ["POINT", "LINE", "CIRCLE", "SINE", "PLANE", "SOLID", "HUMAN"]
    for i, cl in enumerate(classes):
        on = landed_n > i * 5
        fr.write(4 + i * 2, 171, "▶", fg=P.C["primary"] if on else P.C["line"])
        fr.write(4 + i * 2, 173, f"{cl:<8}", fg=P.C["fg"] if on else P.C["dim"])
        fr.write(5 + i * 2, 173, f"{min(landed_n, (i + 1) * 5):02d} obj",
                 fg=P.C["dim"] if on else P.mix(P.C["line"], P.C["void"], 0.5))
    # bottom bars in a panel
    _panel(fr, 24, 2, 33, 52, title="ASSEMBLY", fg=P.C["line"])
    W.progress_bar(fr, 26, 4, 44, fx.clamp(landed_n / len(objs)), fg=P.C["gold"],
                   label="PLACED", show_pct=True)
    W.progress_bar(fr, 28, 4, 44, fx.clamp(landed_n / len(objs) * 0.9), fg=P.C["primary"],
                   label="LATTICE", show_pct=True)
    W.progress_bar(fr, 30, 4, 44, fx.clamp((landed_n - 10) / max(1, len(objs) - 10)),
                   fg=P.C["teal"], label="BINDING", show_pct=True)
    fr.write(32, 4, f"pieces in flight: {len(objs) - landed_n:02d}   seed 0x2B7C",
             fg=P.C["dim"])
    # inspector: the piece that landed last
    _panel(fr, 24, 56, 33, 140, title="PIECE INSPECTOR", fg=P.C["line"])
    if landed_n:
        (x, y, g, d, idx) = objs[landed_n - 1]
        fr.write(26, 58, "ID    ", fg=P.C["dim"])
        fr.write(26, 64, f"0x{idx:02X}   {g}", fg=P.C["gold"])
        fr.write(27, 58, "CLASS ", fg=P.C["dim"])
        fr.write(27, 64, ["POINT", "LINE", "CIRCLE", "SINE", "PLANE", "SOLID"][idx % 6],
                 fg=P.C["teal"])
        fr.write(28, 58, "COORD ", fg=P.C["dim"])
        fr.write(28, 64, f"({x:03d}, {y:02d})  mass=1.{idx % 9}g  spin={idx % 7}deg",
                 fg=P.C["fg"])
        fr.write(29, 58, "FLAGS 0b" + format(idx % 256, "08b"), fg=P.C["mid"])
        W.progress_bar(fr, 31, 58, 40, (idx % 17) / 17, fg=P.C["primary"], show_pct=False)
        fr.write(31, 100, "collision: none", fg=P.C["dim"])
    fr.write(33, 60, "→ let's begin object creation", fg=P.C["dim"])


# ---------------------------------------------------------------- phase 03 --
_FIELDS = [
    ("PARAM_000", "position", "0x3F2A"),
    ("PARAM_001", "dimension", "0x00A1"),
    ("PARAM_002", "circumference", "0x1C4E"),
    ("PARAM_003", "amplitude", "0x7D02"),
    ("PARAM_004", "frequency", "0x0BB8"),
    ("PARAM_005", "phase", "0x00FF"),
    ("PARAM_006", "color_space", "0xFF00"),
    ("PARAM_007", "object_count", "0x0039"),
    ("PARAM_008", "limits", "0x7FFF"),
    ("PARAM_009", "seed", "0x2B7C"),
    ("PARAM_010", "gravity", "0x0148"),
    ("PARAM_011", "love", "0xFFFF"),
]
_CHECKLIST = ["LOAD PARAM TABLE", "ALLOCATE MEMORY", "BIND OBJECTS",
              "SET LIMITS", "LINK SENSORS", "START KERNEL"]


def _data(fr, ctx):
    t = ctx.t
    lt = t - 7.575
    # left hex dump
    _panel(fr, 2, 2, 33, 25, title="MEMORY", fg=P.C["line"])
    W.hex_dump(fr, 4, 4, 26, 20, t, seed=5, fg=P.C["dim"], step=0.35)
    fr.write(31, 4, "0x7FF2A0 - 0x7FF3FF", fg=P.C["green"])
    # center param table
    _panel(fr, 2, 27, 21, 166, title="DATA / PARAMETERS / INITIALIZATION",
           fg=P.C["primary"], style=2)
    per = 0.17
    cur = -1
    for i, (name, field, val) in enumerate(_FIELDS):
        r = 4 + i
        start = i * per
        p = fx.clamp((lt - start) / (per * 1.7))
        if p <= 0:
            continue
        if p < 1.0:
            cur = i
        active = p < 1.0
        fr.write(r, 29, name, fg=P.C["gold"] if active else P.C["teal"])
        fr.write(r, 40, field, fg=P.C["dim"])
        if active:
            s = "".join("0123456789ABCDEF"[int(fx.hash01(i, k, int(t * 30)) * 16)]
                        for k in range(4))
            fr.write(r, 58, "0x" + s, fg=P.C["gold"])
        else:
            fr.write(r, 58, val, fg=P.C["gold"] if val != "0xFFFF" else P.C["red"])
        W.progress_bar(fr, r, 68, 26, p, fg=P.C["primary"], show_pct=False)
        fr.write(r, 96, "✓" if p >= 1.0 else "…",
                 fg=P.C["green"] if p >= 1.0 else P.C["gold"])
        fr.write(r, 100, "OK" if p >= 1.0 else "WRITING",
                 fg=P.C["green"] if p >= 1.0 else P.C["dim"])
    if cur >= 0:
        for c in range(28, 166):
            fr.put(4 + cur, c, "─", fg=P.mix(P.C["primary"], P.C["void"], 0.55))
        fr.write(4 + cur, 150, f"◀ {_FIELDS[cur][0]}", fg=P.C["white"])
    # memory map below the table
    _panel(fr, 22, 27, 33, 136, title="MEMORY MAP", fg=P.C["line"])
    mem = fx.clamp(lt / 3.2)
    cols = 34
    for j in range(cols):
        c = 29 + j * 3
        f = fx.clamp(mem * 2.9 - j / cols * 2.0)
        for k in range(7):
            rr = 25 + k
            if k < int(f * 7):
                ch, fg = "▓", P.C["primary"] if j % 4 else P.C["teal"]
            else:
                ch, fg = "░", P.mix(P.C["line"], P.C["void"], 0.55)
            fr.put(rr, c, ch, fg=fg)
            fr.put(rr, c + 1, ch, fg=P.mix(fg, P.C["void"], 0.45))
        if int(f * 7) >= 1:
            fr.put(24 + int(f * 7), c, "┴", fg=P.C["gold"])
    fr.write(31, 138, f"{int(mem * 100):3d}%", fg=P.C["gold"])
    # INIT checklist panel
    _panel(fr, 2, 138, 21, fr.cols - 2, title="INIT", fg=P.C["line"])
    for i, item in enumerate(_CHECKLIST):
        done = lt > 0.3 + i * 0.55
        fr.write(4 + i * 2, 140, "✓" if done else "·",
                 fg=P.C["green"] if done else P.C["dim"])
        fr.write(4 + i * 2, 142, item, fg=P.C["fg"] if done else P.C["dim"])
        W.dots_progress(fr, 5 + i * 2, 142, 16, int(done) * 16, fg=P.C["primary"])
    fr.write(18, 140, "kernel handoff", fg=P.C["dim"])
    # central caption
    fr.paint_text("FILL IN MY DATA", 23, 96, 2, fg=P.C["primary"], fg2=P.C["white"],
                  align="center")
    fr.write(26, 66, "parameters / initialization / seed = 0x2B7C", fg=P.C["dim"])


# ---------------------------------------------------------------- phase 04 --
def _world(fr, ctx):
    t = ctx.t
    lt = t - 11.267
    horizon = 18
    # wireframe globe
    cx, cy, rx, ry = 96, 9, 40, 7.2
    rot = lt * 1.1
    fr.write(2, 3, "┤ WORLD SETUP", fg=P.C["primary"])
    fr.write(2, 20, "── new world / simulation", fg=P.C["dim"])
    fr.write(2, fr.cols - 44, "BUILD", fg=P.C["dim"])
    W.progress_bar(fr, 3, fr.cols - 44, 36, fx.clamp(lt / 2.4), fg=P.C["gold"], show_pct=True)
    for lat_i in range(-4, 5):
        lat = lat_i / 5 * math.pi / 2
        for lon_i in range(0, 60):
            lon = lon_i / 60 * 2 * math.pi
            x3 = math.cos(lat) * math.sin(lon + rot)
            y3 = math.sin(lat)
            z3 = math.cos(lat) * math.cos(lon + rot)
            if z3 < -0.1:
                continue
            fr.put(int(round(cy + y3 * ry)), int(round(cx + x3 * rx)),
                   "·" if abs(lat_i) % 2 else "•",
                   fg=P.mix(P.C["void"], P.C["primary"], 0.4 + 0.6 * (z3 * 0.5 + 0.5)))
    for lon_i in range(0, 40):
        lon = lon_i / 40 * 2 * math.pi
        for lat_i in range(-8, 9):
            lat = lat_i / 8 * math.pi / 2
            x3 = math.cos(lat) * math.sin(lon + rot)
            y3 = math.sin(lat)
            z3 = math.cos(lat) * math.cos(lon + rot)
            if z3 < 0.15:
                continue
            fr.put(int(round(cy + y3 * ry)), int(round(cx + x3 * rx)), "•",
                   fg=P.mix(P.C["primary"], P.C["white"], z3 * 0.6))
    # orbit ring
    for k in range(80):
        ang = k / 80 * 2 * math.pi
        fr.put(int(round(cy + math.sin(ang) * (ry + 2))),
               int(round(cx + math.cos(ang) * (rx + 8))), "·",
               fg=P.mix(P.C["line"], P.C["primary"], 0.4))
    # perspective floor
    for k in range(26):
        p = ((k * 0.11 + lt * 0.62) % 1.0)
        y = horizon + int((p ** 2.3) * (33 - horizon))
        bright = 0.25 + 0.75 * p
        for c in range(0, fr.cols, 2):
            fr.put(y, c, "─", fg=P.mix(P.C["void"], P.C["primary"], bright))
    for c in range(-30, fr.cols + 30, 7):
        x_top = 96 + (c - 96) * 0.16
        for k in range(0, 180):
            p = k / 180
            y = horizon + int(p ** 2.3 * (33 - horizon))
            x = int(fx.lerp(x_top, c, p ** 1.7))
            if fr.inb(y, x):
                fr.put(y, x, "·" if k % 2 else "│",
                       fg=P.mix(P.C["void"], P.C["primary"], 0.55 - 0.25 * p))
    fr.hline(horizon, 0, fr.cols - 1, "─", fg=P.C["primary"])
    # side data columns
    W.data_column(fr, 1, 2, 32, t, seed=7, speed=7.0, fg=P.C["dim"])
    W.data_column(fr, 1, fr.cols - 3, 32, t, seed=8, speed=6.0, fg=P.C["dim"])
    # big countdown / text
    if lt < 2.1:
        n = 3 - int(lt / 0.7)
        if n >= 1:
            fr.paint_text(str(n), 20, 96, 6, fg=P.C["primary"], fg2=P.C["white"],
                          align="center")
            fr.write(27, 88, f"T-{n}  SIMULATION IMMINENT", fg=P.C["gold"])
    # big RUN after the countdown (fills the empty tail of the intro)
    if 2.15 <= lt <= 3.55:
        k = fx.smoothstep(lt, 2.15, 2.62)
        h = 2 + int(round(7.0 * fx.ease_out(fx.clamp(k))))
        fr.paint_text("RUN", 15, 96, max(2, h), fg=P.C["green"], fg2=P.C["white"],
                      align="center")
        if k > 0.85:
            on = int(t * 6.0) % 2 == 0
            fr.write(27, 76,
                     "▶ EXECUTION STARTED  //  SIMULATION LIVE",
                     fg=P.C["green"] if on else P.C["teal"])
            for j in range(16):
                ang = j / 16.0 * 2 * math.pi
                rr = 6 + ((lt - 2.15) * 26.0 + j) % 10
                fr.put(int(round(21 + math.sin(ang) * rr * 0.42)),
                       int(round(96 + math.cos(ang) * rr * 1.9)),
                       "✦", fg=P.mix(P.C["green"], P.C["void"], 0.35))
    # status panels
    _panel(fr, 23, 2, 33, 62, title="SIMULATION", fg=P.C["line"])
    W.progress_bar(fr, 25, 4, 50, fx.clamp(lt / 3.2), fg=P.C["primary"],
                   label="BOOT", show_pct=True)
    W.progress_bar(fr, 27, 4, 50, fx.clamp(lt / 2.8), fg=P.C["gold"],
                   label="WORLD", show_pct=True)
    W.progress_bar(fr, 29, 4, 50, fx.clamp(lt / 2.5), fg=P.C["teal"],
                   label="RENDER", show_pct=True)
    _panel(fr, 23, 130, 33, fr.cols - 2, title="WORLD STATE", fg=P.C["line"])
    _kv(fr, 25, 132, "OBJECTS", "39 / 39", klen=10, vfg=P.C["teal"])
    _kv(fr, 26, 132, "PARAMS", "12 / 12", klen=10, vfg=P.C["teal"])
    _kv(fr, 27, 132, "GRAVITY", "0.0148 g", klen=10, vfg=P.C["fg"])
    _kv(fr, 28, 132, "STATE", "RUNNING", klen=10, vfg=P.C["green"])
    _kv(fr, 29, 132, "MODE", "AUTO", klen=10, vfg=P.C["gold"])
    fr.write(31, 132, ">> simulation begins", fg=P.C["primary"])
    # expanded rings
    for k in range(60):
        ang = fx.hash01(k, 1) * 2 * math.pi
        sp = 0.4 + fx.hash01(k, 2)
        p = (lt * 0.8 * sp) % 1.0
        dist = p * 88
        x = int(96 + math.cos(ang) * dist * 1.7)
        y = int(20 + math.sin(ang) * dist * 0.5)
        if fr.inb(y, x):
            fr.put(y, x, "+" if p > 0.65 else "·",
                   fg=P.mix(P.C["void"], P.C["primary"], 0.25 + 0.75 * (1 - p)))
