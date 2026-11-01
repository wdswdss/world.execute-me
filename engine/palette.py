"""Terminal / CRT palette for world.execute(me); ASCII MV.

The palette keeps the confirmed design language of the project family
(deep-space void, cyan phosphor, gold user/memory, red failure) and adds
the green/amber phosphor shades needed for a program-interface look.
"""
import numpy as np

C = {
    "black":   (0, 0, 0),
    "void":    (3, 6, 11),
    "void2":   (5, 10, 17),
    "panel":   (8, 17, 26),
    "panel2":  (11, 24, 34),
    "grid":    (16, 42, 52),
    "line":    (30, 78, 92),
    "dim":     (48, 112, 124),
    "mid":     (92, 180, 186),
    "fg":      (168, 232, 226),
    "white":   (226, 250, 250),
    "primary": (95, 230, 255),   # cyan - "her" / system
    "teal":    (72, 255, 214),   # phosphor cyan-green
    "green":   (120, 255, 168),
    "grass":   (168, 255, 120),
    "gold":    (255, 201, 107),  # user / memory (confirmed design)
    "amber":   (255, 176, 64),
    "orange":  (255, 138, 58),
    "red":     (255, 93, 108),   # failure / loss (confirmed design)
    "crimson": (255, 40, 66),
    "blood":   (176, 18, 36),
    "magenta": (255, 93, 190),
    "violet":  (168, 130, 255),
    "blue":    (96, 150, 255),
    "cyan2":   (60, 170, 220),
}

# Named alpha-blend helpers ---------------------------------------------------


def rgb(name):
    if isinstance(name, tuple):
        return name
    return C[name]


def mix(a, b, f):
    """Linear blend a->b for rgb tuples / names."""
    a, b = rgb(a), rgb(b)
    f = np.clip(f, 0.0, 1.0)
    return tuple(int(round(a[i] + (b[i] - a[i]) * f)) for i in range(3))


def shade(name, k):
    """Multiply brightness (k>1 brightens toward white a little)."""
    a = rgb(name)
    out = []
    for v in a:
        w = v * k
        out.append(int(max(0, min(255, round(w)))))
    return tuple(out)


def dark(name, f):
    return mix(name, "black", f)


def blend_over(fg, bg, alpha):
    return mix(bg, fg, alpha)


# 8-step brightness ramps used by masks / coverage art -----------------------
RAMP_HI = " .:-=+*#%@"
RAMP_BLOCK = " ░▒▓█"
RAMP_DOT = " ˙·:•●"
RAMP_VERT = " ▁▂▃▄▅▆▇█"
RAMP_ASCII = " .:-=+*#%▓█"

BAND_COLORS = ["blue", "primary", "teal", "green", "grass", "gold", "amber", "orange", "red"]
