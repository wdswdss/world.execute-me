#!/usr/bin/env python3
"""asciimv.py — play WORLD.EXECUTE(ME); inside a real terminal.

This is the terminal front-end for the same engine that renders the video: it
draws the identical 192x60 character grid (scene + chrome + lyric strip) and
prints it as ANSI 24-bit colour text, paced against ``audio/song.wav``.

The grid comes from ``engine.sceneapi.draw_scene()`` (scene -> 45x192 stage
frame) and ``engine.chrome.Chrome.build()`` (60x192 full frame with header,
transport bar, lyric strip and spectrum).  Lyrics are *not* baked into the grid
by the engine (the video renderer paints them as PIL text on the 1080p image),
so this player writes them itself into the subtitle strip rows: EN on row 49
and CN on row 51, karaoke-style for the English line.

Examples
--------
    python bin/asciimv.py                     # full MV, start to end, with audio
    python bin/asciimv.py --still 26          # one frame to stdout, then exit
    python bin/asciimv.py --from 60 --to 63   # 3 s excerpt
    python bin/asciimv.py --width             # fit whatever terminal you have
    python bin/asciimv.py --loop              # keep looping (good for a kiosk)
    python bin/asciimv.py --list              # print the scene table

See ``docs/TERMINAL.md`` for terminal requirements, colour modes, audio
back-ends and troubleshooting.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
import traceback
import unicodedata

import numpy as np

# --------------------------------------------------------------------------
# repo bootstrap: allow `python bin/asciimv.py` from anywhere
# --------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import font as F            # noqa: E402
from engine import layout as L          # noqa: E402
from engine import palette as P         # noqa: E402
from engine import sceneapi             # noqa: E402
from engine import timeline as TL       # noqa: E402
from engine.chrome import Chrome        # noqa: E402

DURATION = float(getattr(L, "DURATION", 211.905))
FPS_DEFAULT = float(getattr(L, "FPS", 30.0))

# supported grid downsample factors, largest first (cost scales with area)
SCALES = (1.0, 0.75, 0.5)

SONG = os.path.join(ROOT, "audio", "song.wav")

# lyric strip colours (the video renderer uses white for the sung part of the
# English line and a dim cyan-grey for the rest; CN sits one shade dimmer)
EN_SUNG = (206, 233, 255)
EN_SUNG_RED = (255, 96, 104)
EN_REST_RED = (132, 34, 40)
CN_COLOR_RED = (255, 150, 150)
EN_REST = tuple(int(v) for v in P.mix(P.C["dim"], P.C["fg"], 0.35))
CN_COLOR = (128, 192, 255)


# ==========================================================================
# glyph tables
# ==========================================================================
# engine.font builds its atlas lazily and only then fills IDX_CHARS, so the
# glyph tables have to be created after the first atlas build.
_GLYPHS = None
_GLENGTHS = None


def glyph_tables():
    """(list-of-bytes per glyph index, int64 array of UTF-8 byte lengths)."""
    global _GLYPHS, _GLENGTHS
    if _GLYPHS is None:
        F.get_atlas()
        _GLYPHS = [ch.encode("utf-8") for ch in F.IDX_CHARS]
        _GLENGTHS = np.fromiter((len(b) for b in _GLYPHS), dtype=np.int64,
                                count=len(_GLYPHS))
    return _GLYPHS, _GLENGTHS


# ==========================================================================
# colour encoding
# ==========================================================================
_ANSI16 = (
    (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
    (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
    (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
)


def _xterm256(rgb):
    """Nearest xterm-256 palette index for an RGB triple (6x6x6 cube or grey ramp)."""
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])

    def q(v):
        return 0 if v < 48 else (1 if v < 115 else (v - 35) // 40)

    r6, g6, b6 = q(r), q(g), q(b)
    cube = 16 + 36 * r6 + 6 * g6 + b6
    cr, cg, cb = r6 * 51, g6 * 51, b6 * 51
    d_cube = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
    grey = (r * 299 + g * 587 + b * 114) // 1000
    gi = 0 if grey < 8 else min(23, (grey - 8) // 10)
    gv = 8 + gi * 10
    d_grey = (r - gv) ** 2 + (g - gv) ** 2 + (b - gv) ** 2
    return 232 + gi if d_grey < d_cube else cube


def _ansi16(rgb):
    best, bd = 0, 1 << 30
    for i, c in enumerate(_ANSI16):
        d = (rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2 + (rgb[2] - c[2]) ** 2
        if d < bd:
            best, bd = i, d
    return best


class Encoder:
    """Turn one 60x192 frame into a single bytes blob.

    Colours are packed per cell into one int64 key so run boundaries are found
    with a numpy diff, each distinct (fg, bg) pair becomes an escape sequence at
    most once (cached across frames), and glyph UTF-8 bytes are joined per row
    with offsets taken from a cumulative sum of glyph lengths.  Overlay rows
    (the lyric strip) fall back to a per-cell byte list so wide CJK glyphs can
    occupy two grid cells.
    """

    def __init__(self, depth=24):
        self.depth = int(depth)          # 24 / 256 / 16 / 0 (mono)
        self._cache = {}
        self._take = None
        self._glen = None

    def _tables(self):
        if self._take is None:
            idxb, glen = glyph_tables()
            self._take = idxb.__getitem__
            self._glen = glen
        return self._take, self._glen

    # -- escape sequence for one packed (fg, bg) pair -----------------------
    def _style_packed(self, k):
        st = self._cache.get(k)
        if st is not None:
            return st
        fg24, bg24 = (k >> 24) & 0xFFFFFF, k & 0xFFFFFF
        fg = ((fg24 >> 16) & 255, (fg24 >> 8) & 255, fg24 & 255)
        bg = ((bg24 >> 16) & 255, (bg24 >> 8) & 255, bg24 & 255)
        d = self.depth
        if d == 0:
            st = b""
        elif d == 24:
            st = b"\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm" % (
                fg[0], fg[1], fg[2], bg[0], bg[1], bg[2])
        elif d == 256:
            st = b"\x1b[38;5;%dm\x1b[48;5;%dm" % (_xterm256(fg), _xterm256(bg))
        else:
            f, b = _ansi16(fg), _ansi16(bg)
            fgpart = b"\x1b[%dm" % (30 + (f & 7)) if f < 8 else b"\x1b[%dm" % (90 + (f & 7))
            bgpart = b"\x1b[%dm" % (40 + (b & 7)) if b < 8 else b"\x1b[%dm" % (100 + (b & 7))
            st = fgpart + bgpart
        self._cache[k] = st
        return st

    # -- packed colour keys -------------------------------------------------
    @staticmethod
    def _pack_rows(fg, bg):
        fg24 = ((fg[..., 0].astype(np.int64) << 16)
                | (fg[..., 1].astype(np.int64) << 8) | fg[..., 2])
        bg24 = ((bg[..., 0].astype(np.int64) << 16)
                | (bg[..., 1].astype(np.int64) << 8) | bg[..., 2])
        return (fg24 << 24) | bg24

    # -- overlay one string into a row (wide chars take two cells) ---------
    @staticmethod
    def _place(pieces, fgrow, col, text, rgb):
        n = len(pieces)
        for ch in text:
            if col >= n:
                break
            wide = unicodedata.east_asian_width(ch) in ("W", "F")
            pieces[col] = ch.encode("utf-8")
            fgrow[col] = rgb
            if wide:
                if col + 1 < n:
                    pieces[col + 1] = b""
                    fgrow[col + 1] = rgb
                col += 2
            else:
                col += 1
        return col

    # -- main ---------------------------------------------------------------
    def encode(self, ch, fg, bg, extras=None, tty=True, pad_top=0, pad_left=0):
        """ch int16 (rows,cols) / fg,bg uint8 (rows,cols,3) -> bytes."""
        rows, cols = ch.shape
        take, glen = self._tables()
        key = self._pack_rows(fg, bg)
        rows_list = ch.tolist()
        lens_all = glen[ch]
        mask = key[:, 1:] != key[:, :-1]
        changes_all = [(np.flatnonzero(mask[r]) + 1).tolist() for r in range(rows)]

        out = bytearray()
        pad = b""
        if tty:
            out += b"\x1b[%d;1H" % (pad_top + 1) if pad_top else b"\x1b[H"
            if pad_left:
                pad = b" " * pad_left
        depth = self.depth

        for r in range(rows):
            rowl = rows_list[r]
            ov = extras.get(r) if extras else None
            if ov:
                pieces = [take(i) for i in rowl]
                for col, segments in ov:
                    for text, rgb in segments:
                        col = self._place(pieces, fg[r], col, text, rgb)
                rowtext = b"".join(pieces)
                lens = np.fromiter(map(len, pieces), np.int64, count=cols)
                kr = self._pack_rows(fg[r:r + 1], bg[r:r + 1])[0]
                changes = [c for c in range(1, cols) if kr[c] != kr[c - 1]]
            else:
                rowtext = b"".join(map(take, rowl))
                lens = lens_all[r]
                kr = key[r]
                changes = changes_all[r]

            off = np.empty(cols + 1, np.int64)
            off[0] = 0
            np.cumsum(lens, out=off[1:])
            offl = off.tolist()

            row = bytearray()
            if tty:
                row += pad
            if depth == 0:
                row += rowtext
            else:
                prev = 0
                last = -1
                for b in changes:
                    chunk = rowtext[offl[prev]:offl[b]]
                    if chunk:
                        kk = int(kr[prev])
                        if kk != last:
                            row += self._style_packed(kk)
                            last = kk
                        row += chunk
                    prev = b
                chunk = rowtext[offl[prev]:]
                if chunk:
                    kk = int(kr[prev])
                    if kk != last:
                        row += self._style_packed(kk)
                    row += chunk

            if tty:
                if depth:
                    row += b"\x1b[0m"
                row += b"\x1b[K"
                if r != rows - 1:
                    row += b"\r\n"
            elif r != rows - 1:
                row += b"\n"
            out += row

        if not tty:
            out += b"\n"
        return bytes(out)


# ==========================================================================
# renderer
# ==========================================================================
def _disp_width(text):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


class Player:
    """Renders timeline seconds to small arrays of glyphs / colours."""

    def __init__(self, scale=1.0, fit=False, depth=24):
        self.chrome = Chrome()
        self.assets = sceneapi.A.get_assets()
        self.enc = Encoder(depth)
        self.scale, self.out_cols, self.out_rows, self.pad_top, self.pad_left = \
            self._geometry(scale, fit)
        self.ridx = self._index(self.out_rows, L.ROWS, self.scale)
        self.cidx = self._index(self.out_cols, L.COLS, self.scale)
        self.en_row = self._row_of(L.SUB_EN_ROW)
        self.cn_row = self._row_of(L.SUB_CN_ROW)
        self._error_shown = False

    # -- geometry -----------------------------------------------------------
    @staticmethod
    def _index(n_out, n_src, scale):
        pos = (np.arange(n_out, dtype=np.float64) + 0.5) / scale - 0.5
        return np.clip(np.rint(pos).astype(np.int64), 0, n_src - 1)

    def _geometry(self, scale, fit):
        pad_top = pad_left = 0
        if fit:
            ts = shutil.get_terminal_size((L.COLS, L.ROWS))
            cols, lines = max(16, ts.columns), max(8, ts.lines)
            scale = min(cols / L.COLS, lines / L.ROWS, 1.0)
        out_cols = max(16, int(round(L.COLS * scale)))
        out_rows = max(8, int(round(L.ROWS * scale)))
        if fit:
            pad_top = max(0, (lines - out_rows) // 2)
            pad_left = max(0, (cols - out_cols) // 2)
        return scale, out_cols, out_rows, pad_top, pad_left

    def _row_of(self, src_row):
        pos = (src_row + 0.5) * self.scale - 0.5
        return int(min(self.out_rows - 2, max(1, round(pos))))

    # -- lyrics -------------------------------------------------------------
    def lyrics(self, t):
        idx, ln = TL.line_at(t)
        if not ln:
            return {}
        en = str(ln.get("en") or "")
        cn = str(ln.get("cn") or "")
        t0 = float(ln.get("t0", t))
        t1 = float(ln.get("t1", t))
        p = 0.0 if t1 <= t0 else max(0.0, min(1.0, (t - t0) / (t1 - t0)))
        room = self.out_cols - 12
        extras = {}
        try:
            hot = self.chrome.sub_heat(t) > 0.5
        except Exception:
            hot = False
        en_sung = EN_SUNG_RED if hot else EN_SUNG
        en_rest = EN_REST_RED if hot else EN_REST
        cn_col = CN_COLOR_RED if hot else CN_COLOR
        if en and room >= 8:
            while en and _disp_width(en) > room:
                en = en[:-1]
            start = max(6, (self.out_cols - _disp_width(en)) // 2)
            qp = getattr(self.chrome, "_rhythm_progress", None)
            try:
                q = qp(t, t0, t1)[0]
            except Exception:
                q = min(1.0, p / 0.72)
            n_sung = max(0, min(len(en), int(round(len(en) * q))))
            segs = []
            if n_sung:
                segs.append((en[:n_sung], en_sung))
            if n_sung < len(en):
                segs.append((en[n_sung:], en_rest))
            if segs:
                extras[self.en_row] = [(start, segs)]
        if cn and _disp_width(cn) <= room:
            try:
                q2 = qp(t, t0, t1)[0]
            except Exception:
                q2 = min(1.0, p / 0.72)
            cnum = max(0, min(len(cn), int(round(len(cn) * q2))))
            cn_show = cn[:cnum]
            start = max(6, (self.out_cols - _disp_width(cn)) // 2)
            if cn_show:
                extras[self.cn_row] = [(start, [(cn_show, cn_col)])]
        return extras

    # -- one frame ----------------------------------------------------------
    def render(self, t):
        try:
            stage, _meta, ctx = sceneapi.draw_scene(t, self.assets)
            scene = getattr(ctx, "scene", "")
        except Exception:
            if not self._error_shown:
                self._error_shown = True
                print("[asciimv] scene error at t=%.3f s" % t, file=sys.stderr)
                traceback.print_exc()
            stage = sceneapi.err_frame(t)
            scene = "error"
        full = self.chrome.build(stage, t, scene, self.assets)
        ch = full.ch[self.ridx][:, self.cidx]
        fg = full.fg[self.ridx][:, self.cidx]
        bg = full.bg[self.ridx][:, self.cidx]
        extras = self.lyrics(t)
        if extras and self.scale < 0.999:
            # the sampled chrome strip is not readable once squeezed: clear it
            for r in extras:
                ch[r, 6:max(7, self.out_cols - 6)] = 0
        return ch, fg, bg, extras

    def encode(self, t, tty=True):
        ch, fg, bg, extras = self.render(t)
        return self.encode_frame(ch, fg, bg, extras, tty=tty)

    def encode_frame(self, ch, fg, bg, extras, tty=True):
        return self.enc.encode(ch, fg, bg, extras, tty=tty,
                               pad_top=self.pad_top, pad_left=self.pad_left)


# ==========================================================================
# audio
# ==========================================================================
class Audio:
    """Best-effort audio playback of audio/song.wav, seeking when possible."""

    def __init__(self, path=SONG, enabled=True):
        self.path = path
        self.requested = bool(enabled)
        self.enabled = bool(enabled) and os.path.exists(path)
        self.backend = None
        self._mci = None
        self._mci_buf = None
        self._proc = None
        self._alias = "asciimv"

    # -- windows MCI (seeking) ---------------------------------------------
    def _mci_open(self):
        if self._mci is not None:
            return True
        try:
            import ctypes
            self._mci = ctypes.windll.winmm.mciSendStringW
            self._mci_buf = ctypes.create_unicode_buffer(600)
        except Exception:
            self._mci = None
            return False
        return True

    def _mci_cmd(self, cmd):
        self._mci(cmd, self._mci_buf, 600, 0)
        return self._mci_buf.value

    def _mci_start(self, offset):
        if os.name != "nt" or not self._mci_open():
            return False
        try:
            self._mci_cmd("close %s" % self._alias)
            if self._mci_cmd('open "%s" type waveaudio alias %s' % (self.path, self._alias)):
                return False
            self._mci_cmd("set %s time format milliseconds" % self._alias)
            if offset > 0.05:
                r = self._mci_cmd("play %s from %d" % (self._alias, int(offset * 1000.0)))
            else:
                r = self._mci_cmd("play %s" % self._alias)
            if r:
                return False
            self.backend = "mci"
            return True
        except Exception:
            return False

    def _winsound_start(self):
        if os.name != "nt":
            return False
        try:
            import winsound
            winsound.PlaySound(self.path,
                               winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
            self.backend = "winsound"
            return True
        except Exception:
            return False

    # -- non-windows fallback ----------------------------------------------
    def _subprocess_start(self):
        for exe, argv in (("afplay", ["afplay", self.path]),
                          ("aplay", ["aplay", "-q", self.path])):
            if shutil.which(exe):
                try:
                    self._proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.DEVNULL)
                    self.backend = exe
                    return True
                except Exception:
                    continue
        return False

    def start(self, offset=0.0):
        if not self.enabled:
            if self.requested and not os.path.exists(self.path):
                print("[asciimv] audio file missing: %s (playing silently)" % self.path,
                      file=sys.stderr)
            return False
        if offset > 0.05 and self._mci_start(offset):
            return True
        if self._winsound_start():
            if offset > 0.05:
                print("[asciimv] audio backend cannot seek: started from the top",
                      file=sys.stderr)
            return True
        if self._mci_start(offset):
            return True
        if self._subprocess_start():
            if offset > 0.05:
                print("[asciimv] audio backend cannot seek: started from the top",
                      file=sys.stderr)
            return True
        self.enabled = False
        print("[asciimv] no usable audio backend found; playing silently", file=sys.stderr)
        return False

    def stop(self):
        if self.backend == "winsound":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        elif self.backend == "mci" and self._mci is not None:
            try:
                self._mci_cmd("stop %s" % self._alias)
                self._mci_cmd("close %s" % self._alias)
            except Exception:
                pass
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc = None
            except Exception:
                pass
        self.backend = None


# ==========================================================================
# terminal state
# ==========================================================================
ALT_ON = b"\x1b[?1049h"
ALT_OFF = b"\x1b[?1049l"
CURSOR_OFF = b"\x1b[?25l"
CURSOR_ON = b"\x1b[?25h"
CLEAR = b"\x1b[2J"
RESET = b"\x1b[0m"


def _enable_vt():
    """Turn on ANSI/VT processing on Windows consoles (no-op elsewhere)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(mode)):
            k32.SetConsoleMode(h, mode.value | 0x0004)
    except Exception:
        pass


class Screen:
    def __init__(self, tty):
        self.tty = tty

    def enter(self):
        if not self.tty:
            return
        _enable_vt()
        sys.stdout.buffer.write(ALT_ON + CURSOR_OFF + CLEAR)
        sys.stdout.buffer.flush()

    def leave(self):
        if not self.tty:
            return
        sys.stdout.buffer.write(RESET + CURSOR_ON + ALT_OFF)
        sys.stdout.buffer.flush()


# ==========================================================================
# playback
# ==========================================================================
def print_scenes():
    print(f"{'scene':14s} {'start':>8s} {'end':>8s} {'dur':>7s}  {'module':16s} first lyric")
    for t0, t1, key, mod in sceneapi.SCHEDULE:
        i, ln = TL.line_at(t0 + 0.01)
        first = (ln.get("en", "") if ln else "")
        if len(first) > 36:
            first = first[:33] + "..."
        print(f"{key:14s} {t0:8.3f} {t1:8.3f} {t1 - t0:7.3f}  {mod:16s} {first}")
    print(f"\n{len(sceneapi.SCHEDULE)} scenes, {DURATION:.3f} s total, "
          f"{int(round(DURATION * FPS_DEFAULT))} frames at {FPS_DEFAULT:g} fps")


def _pct(values, q):
    if not values:
        return 0.0
    s = sorted(values)
    k = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[k]


def play(player, args, tty):
    out = sys.stdout.buffer
    screen = Screen(tty)
    audio = Audio(args.audio_path, enabled=not args.no_audio)
    fps = max(1.0, float(args.fps))
    start = max(0.0, min(float(args.start), DURATION - 1e-3))
    end = DURATION if args.end is None else max(start + 1e-3, min(float(args.end), DURATION))

    draws, encs = [], []
    frames = 0
    dropped = 0
    wall = 0.0
    loops = 0
    try:
        screen.enter()
        while True:
            loops += 1
            seg_start = time.perf_counter()
            n = max(1, int(math.ceil((end - start) * fps)))

            # warm the font/scene caches before the clock starts, so the first
            # visible frame costs what the rest do
            ch, fg, bg, extras = player.render(start)
            first = player.encode_frame(ch, fg, bg, extras, tty=tty)

            audio.start(offset=(start if start > 0.05 else 0.0))
            t0 = time.perf_counter()
            out.write(first)
            out.flush()
            frames += 1

            i = 1
            while i < n:
                t = start + i / fps
                if tty:
                    lag = time.perf_counter() - (t0 + i / fps)
                    if lag > 0.15:
                        skip = min(n - i - 1, int(lag * fps) - 1)
                        if skip > 0:
                            dropped += skip
                            i += skip
                            continue

                s = time.perf_counter()
                ch, fg, bg, extras = player.render(t)
                draws.append((time.perf_counter() - s) * 1000.0)
                s = time.perf_counter()
                buf = player.encode_frame(ch, fg, bg, extras, tty=tty)
                encs.append((time.perf_counter() - s) * 1000.0)

                if tty:
                    wait = (t0 + i / fps) - time.perf_counter()
                    if wait > 0:
                        time.sleep(wait)
                out.write(buf)
                out.flush()
                frames += 1
                i += 1

            wall += time.perf_counter() - seg_start
            audio.stop()

            if not args.loop:
                break
            if not tty:
                print("[asciimv] --loop ignored when stdout is not a terminal",
                      file=sys.stderr)
                break
    finally:
        audio.stop()
        screen.leave()

    if args.timing:
        budget = 1000.0 / fps
        avg_d = sum(draws) / len(draws) if draws else 0.0
        avg_e = sum(encs) / len(encs) if encs else 0.0
        avg_t = avg_d + avg_e
        print(f"[timing] frames={frames} dropped={dropped} loops={loops} "
              f"wall={wall:.2f}s target={frames / fps:.2f}s", file=sys.stderr)
        print(f"[timing] draw   avg={avg_d:6.2f} ms  p95={_pct(draws, .95):6.2f}  "
              f"max={max(draws) if draws else 0:6.2f}", file=sys.stderr)
        print(f"[timing] encode avg={avg_e:6.2f} ms  p95={_pct(encs, .95):6.2f}  "
              f"max={max(encs) if encs else 0:6.2f}", file=sys.stderr)
        head = (budget / avg_t) if avg_t > 0 else 0.0
        print(f"[timing] total  avg={avg_t:6.2f} ms  budget={budget:6.2f} ms  "
              f"headroom={head:.2f}x  scale={player.scale:g} "
              f"grid={player.out_cols}x{player.out_rows}", file=sys.stderr)
        if avg_t > budget:
            # scale only shrinks the per-cell part (slicing + encode); the scene
            # draw and the chrome build cost the same at any scale, so work out
            # how much a smaller grid would actually save before recommending it.
            fixed = max(0.0, avg_t - avg_e)
            choice = None
            for s in (x for x in SCALES if x <= player.scale + 1e-9):
                if fixed + avg_e * (s / player.scale) ** 2 <= budget:
                    choice = s
                    break
            if choice is not None:
                print(f"[timing] WARNING: slower than {fps:g} fps at this scale; "
                      f"--scale {choice:g} should keep up", file=sys.stderr)
            elif fixed > 0:
                keep = int(1000.0 / fixed)
                print(f"[timing] WARNING: slower than {fps:g} fps even with a smaller "
                      f"grid ({fixed:.0f} ms/frame of scene+chrome, independent of "
                      f"--scale); use --fps {max(10, min(keep, int(fps)))} or "
                      f"close other CPU-heavy programs", file=sys.stderr)
            else:
                print(f"[timing] WARNING: slower than {fps:g} fps; try --fps "
                      f"{max(10, fps // 2):g}", file=sys.stderr)


# ==========================================================================
# cli
# ==========================================================================
EPILOG = """\
examples:
  python bin/asciimv.py                     play the whole MV with audio
  python bin/asciimv.py --still 203.9       print a single frame (pipe-friendly)
  python bin/asciimv.py --from 60 --to 63   play 3 seconds from 01:00
  python bin/asciimv.py --width --no-audio  fit the current terminal, silent
  python bin/asciimv.py --loop --no-audio   loop forever (kiosk / screensaver)
  python bin/asciimv.py --list              scene table with timings

terminal: 192x60 cells or larger is best; use --width/--scale otherwise.
docs/TERMINAL.md has requirements, colour modes and troubleshooting.
"""


def build_parser():
    p = argparse.ArgumentParser(
        prog="asciimv.py",
        description="Play WORLD.EXECUTE(ME); as animated ANSI text in your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    p.add_argument("--from", dest="start", type=float, default=0.0, metavar="SEC",
                   help="start time in seconds (default: 0)")
    p.add_argument("--to", dest="end", type=float, default=None, metavar="SEC",
                   help="stop time in seconds (default: end of the song)")
    p.add_argument("--fps", type=float, default=FPS_DEFAULT,
                   help=f"frames per second (default: {FPS_DEFAULT:g})")
    p.add_argument("--scale", type=float, default=None, choices=SCALES,
                   help="downsample the 192x60 grid (default: 1.0)")
    p.add_argument("--width", action="store_true",
                   help="fit the grid to the current terminal (letterboxed)")
    p.add_argument("--still", type=float, default=None, metavar="T",
                   help="render one frame at T seconds, print it and exit")
    p.add_argument("--list", action="store_true", help="print the scene table and exit")
    p.add_argument("--loop", action="store_true", help="loop playback")
    p.add_argument("--no-color", action="store_true", help="monochrome output (no ANSI)")
    p.add_argument("--color-depth", choices=("24", "256", "16", "mono"), default=None,
                   help="colour depth (default: 24-bit)")
    p.add_argument("--no-audio", action="store_true", help="do not play the audio")
    p.add_argument("--audio", default=SONG, metavar="FILE",
                   help="audio file to play (default: audio/song.wav)")
    p.add_argument("--timing", action="store_true", help="print performance summary")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.list:
        print_scenes()
        return 0

    depth = 24
    if args.color_depth:
        depth = {"24": 24, "256": 256, "16": 16, "mono": 0}[args.color_depth]
    if args.no_color:
        depth = 0
    scale = 1.0 if args.scale is None else float(args.scale)
    args.audio_path = args.audio

    tty = sys.stdout.isatty()
    player = Player(scale=scale, fit=args.width, depth=depth)

    if tty and not args.width:
        ts = shutil.get_terminal_size((L.COLS, L.ROWS))
        if player.out_cols > ts.columns or player.out_rows > ts.lines:
            print("[asciimv] terminal is smaller than the grid; try --width or --scale 0.5",
                  file=sys.stderr)

    if args.still is not None:
        t = max(0.0, min(float(args.still), DURATION))
        buf = player.encode(t, tty=False)
        sys.stdout.buffer.write(buf)
        sys.stdout.buffer.flush()
        if args.timing:
            print(f"[timing] still t={t:.3f}s grid={player.out_cols}x{player.out_rows}",
                  file=sys.stderr)
        return 0

    start = float(args.start)
    if args.end is not None and float(args.end) <= start:
        print(f"[asciimv] --to ({args.end}) must be greater than --from ({start})",
              file=sys.stderr)
        return 2
    args.start = start
    try:
        play(player, args, tty)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
