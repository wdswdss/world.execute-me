# Terminal player — `bin/asciimv.py`

Plays **WORLD.EXECUTE(ME);** inside your terminal: the same 192×60 character
grid the video renderer composes (`engine.sceneapi.draw_scene` +
`engine.chrome.build`), encoded as ANSI truecolor and paced against
`audio/song.wav`.

```
python bin/asciimv.py                    # full MV, with sound
python bin/asciimv.py --still 203.9      # one frame at 03:23.9, printed and exit
python bin/asciimv.py --list             # scene table
```

On Windows, redirecting output to a file needs
`set PYTHONIOENCODING=utf-8` (or `$env:PYTHONIOENCODING="utf-8"` in PowerShell),
otherwise Python may encode the block glyphs with the legacy code page.

---

## 1. Requirements

| thing | needed for | notes |
| --- | --- | --- |
| Python 3.10+ | everything | the project itself targets 3.12 |
| UTF-8 stdout | everything | box drawing `─│┌┐`, blocks `█░▒▓▏`, symbols `◉▎♪` |
| 192 columns × 60 rows | full-size grid | below that use `--width` or `--scale` |
| 24-bit colour | full fidelity | `--color-depth 256` / `16` / `--no-color` otherwise |
| terminal audio | sound | `winsound` on Windows, `afplay` (macOS), `aplay` (Linux) |

**Terminals known to work:** Windows Terminal, WezTerm, kitty, iTerm2,
Alacritty, GNOME Terminal / VTE, Konsole. Windows 10+ consoles get VT
processing switched on automatically (`SetConsoleMode(... ENABLE_VIRTUAL_TERMINAL_PROCESSING)`).

**Fonts:** any monospace font that covers Unicode box drawing, block elements
and geometric shapes — Cascadia Mono, JetBrains Mono, Consolas, Iosevka, DejaVu
Sans Mono. A cell height of ~18 px or more keeps the three-row `paint_text`
headlines readable.

**Terminal size:** the grid is 192×60 cells. Most terminals open at 120×30 — use

```
python bin/asciimv.py --width
```

which measures the window with `shutil.get_terminal_size()`, keeps the 16:9
aspect and letterboxes the result. `--scale 0.75` / `0.5` gives a fixed
144×45 / 96×30 grid instead.

---

## 2. Usage

```
usage: asciimv.py [-h] [--from SEC] [--to SEC] [--fps FPS]
                  [--scale {1.0,0.75,0.5}] [--width] [--still T] [--list]
                  [--loop] [--no-color] [--color-depth {24,256,16,mono}]
                  [--no-audio] [--audio FILE] [--timing]
```

| flag | meaning |
| --- | --- |
| `--from SEC` | start time in seconds (default `0`) |
| `--to SEC` | stop time in seconds (default: end of the song, 211.905) |
| `--fps FPS` | playback / render rate (default `30`) |
| `--scale {1.0,0.75,0.5}` | nearest-neighbour downsample of the 192×60 grid |
| `--width` | fit the grid to the current terminal, letterboxed |
| `--still T` | render a single frame at `T` seconds and exit (pipe-friendly) |
| `--list` | print the scene table and exit |
| `--loop` | loop playback (only honoured when stdout is a terminal) |
| `--no-color` | monochrome, no ANSI escapes at all (logs, `less`, CI) |
| `--color-depth {24,256,16,mono}` | explicit colour depth |
| `--no-audio` | silent playback |
| `--audio FILE` | play a different audio file (default `audio/song.wav`) |
| `--timing` | performance summary on stderr |

### Examples

```
python bin/asciimv.py                          # the whole thing
python bin/asciimv.py --from 192.2 --to 206.9  # just the ending (outro → collapse)
python bin/asciimv.py --width --no-audio       # fit the window, silent
python bin/asciimv.py --loop --no-audio        # kiosk / screensaver
python bin/asciimv.py --still 26.0 > frame.txt # timestamped frame for a bug report
python bin/asciimv.py --list
```

`--from` also seeks the audio (MCI `play ... from <ms>` on Windows), so
`--from 120` starts sound and picture together instead of waiting 2 minutes.

`--still T` never touches the alternate screen or the cursor; it prints exactly
60 newline-separated rows (192 columns each at scale 1.0) and exits 0. At
`--scale 0.5` the rows are 96 columns wide.

If stdout is **not** a terminal (a file, a pipe, a CI log) the player drops the
alternate screen, the cursor hiding and the realtime pacing: it writes frames
back-to-back as fast as it can, so `asciimv.py --from 60 --to 63 > out.txt`
produces a deterministic, complete recording.

---

## 3. Colour modes

| mode | flag | what it emits |
| --- | --- | --- |
| 24-bit (default) | — | `\x1b[38;2;R;G;Bm` / `\x1b[48;2;R;G;Bm` |
| 256 | `--color-depth 256` | xterm-256 cube + grayscale, one SGR per colour |
| 16 | `--color-depth 16` | nearest of the 16 ANSI colours |
| mono | `--no-color` or `--color-depth mono` | no escapes, plain text |

The encoder batches cells that share a foreground/background pair into a single
style escape: a typical frame is ~100 KB of UTF-8 at scale 1.0 and ~30 KB at
scale 0.5.

Lyrics are part of the terminal grid, not the chrome: the player writes the
English line into subtitle row 49 and the Chinese line into row 51 (both from
`engine.timeline.line_at(t)`), with the sung portion of the English line
highlighted, exactly where the video's subtitle strip sits.

---

## 4. Performance

Measured on the development machine (Windows, Python 3.12, 192×60 grid,
`--timing`), one frame at a time:

| stage | scale 1.0 (192×60) | scale 0.5 (96×30) |
| --- | --- | --- |
| scene draw (`draw_scene`) | 1–15 ms quiet scenes, up to ~90 ms in dense chorus sections | same (the scene always draws the full grid) |
| chrome build (`Chrome.build`) | ~20–30 ms | same (chrome is built at full size, then downsampled) |
| ANSI encode + subtitle overlay | ~5–9 ms | ~1–3 ms |
| **frame total** | **~30–50 ms typical** | **~25–40 ms typical** |

So on this machine the player runs at roughly **20–30 fps**: quiet sections
(intro, tail) hit 30, dense chorus sections drop frames to stay in sync. These
numbers were taken with the CPU otherwise idle — the offline video renderer
(`tools/render.py`) and other Python processes on the same box push them up
several times over, so `--timing` on your machine is always the real answer.

**Recommendations**

* Steady playback on a normal laptop: `python bin/asciimv.py --fps 20`.
  A dropped frame under `--fps 30` keeps sync but looks uneven.
* `--scale 0.75` / `--scale 0.5` shrink the grid *and* the encode cost, but
  scene draw and chrome build are scale-independent — expect ~20 % savings at
  0.5, not 4×.
* `--width` is free: it only changes the final slicing.
* Close other CPU-heavy programs; the encoder is pure Python and one rendered
  frame is a single-threaded burst.
* The video renderer (`tools/render.py` → PNG frames → ffmpeg) is offline and
  unaffected by any of this — it composites 1080p images, not terminal bytes.

`--timing` example:

```
[timing] frames=90 dropped=0 loops=0 wall=4.37s target=3.00s
[timing] draw   avg= 41.28 ms  p95= 62.10  max= 98.40
[timing] encode avg=  6.21 ms  p95=  8.57  max= 10.47
[timing] total  avg= 47.49 ms  budget= 33.33 ms  headroom=0.70x  scale=1 grid=192x60
[timing] WARNING: slower than 30 fps at this scale; --scale 0.75 should keep up
```

(When the fixed cost of scene + chrome alone exceeds the budget the warning says
so and recommends a lower `--fps` instead of pretending a smaller grid helps.)

---

## 5. Troubleshooting

**Boxes are fine but some symbols are `?` or blank.**
The terminal font is missing a glyph. The engine maps unknown characters to a
blank cell, so a font downgrade shows up as missing `♪`, `◉` or `▔`. Install
Cascadia Mono or JetBrains Mono; on Windows Terminal set it as the profile font.

**All colour is missing.**
You are probably piping: `--still`/file output still contains ANSI unless you
pass `--no-color`. If a terminal shows no colour in interactive mode, it may not
advertise truecolor — use `--color-depth 256`.

**Every frame is repeated / the screen scrolls.**
The window is smaller than the grid and the terminal is wrapping. Use
`--width`, `--scale 0.75`, or resize to at least 192×60.

**Nothing animates and it's very fast.**
stdout is not a TTY (pipe, redirect, IDE output panel). That is the supported
"record" mode: frames are printed back-to-back with no pacing.

**No sound.**
`winsound` only plays WAV — check that `audio/song.wav` exists (it ships with
the repo, ~40 MB). On Linux/macOS the player shells out to `aplay` / `afplay`;
pass `--no-audio` to silence the warning. Audio failures never stop playback.

**Playback stutters.**
Run `--timing`: if `draw` dominates, try `--fps 20`; if `encode` dominates,
try `--scale 0.5`. The chrome and scene draws are Python and scale with the
machine, not with the grid.

**The terminal is stuck in the alternate screen after a crash (SIGKILL, hard
power loss).**
The player restores the terminal in a `finally` block (alternate screen off,
cursor visible, `--no-color` state reset) for Ctrl+C and normal exits. After a
`kill -9` the terminal cannot be cleaned up from inside; restore it with
`printf '\033[?1049l\033[?25h'` (or `reset`).

**Windows classic console (`conhost.exe`).**
It works — VT processing is enabled automatically — but its renderer is slow.
Windows Terminal is strongly recommended for full-size playback.

**tmux / screen.**
Truecolor needs a modern tmux (`tmux-256color`, `terminal-features` including
`RGB`). If colour looks quantised, use `--color-depth 256`.

---

## 6. How it is put together

`bin/asciimv.py` is intentionally a thin shell around the engine — no engine
file is modified.

* `Player` — owns the `Chrome`, the assets and the current grid scale. For each
  timestamp it calls `sceneapi.draw_scene(t)`, then `Chrome.build(stage, t, …)`,
  downsamples by nearest neighbour, and overlays the two lyric rows.
* `Encoder` — turns `frame.ch` (glyph indices), `frame.fg`, `frame.bg` into one
  `bytes` object per frame. It packs colours into ints, finds style changes with
  a numpy diff, caches escape sequences per colour pair, and concatenates glyph
  bytes with precomputed offsets (this is what took encoding from ~42 ms to
  ~6 ms per frame).
* `Audio` — `winsound.PlaySound(SND_ASYNC)` for plain playback, MCI
  `play … from <ms>` when `--from` seeks into the track, `afplay`/`aplay`
  elsewhere; disabled gracefully if none is available.
* `Screen` — alternate screen buffer, hidden cursor, VT enable on Windows,
  restored in `finally`.
* `play()` — warms the first frame before the clock starts, then paces with
  `time.perf_counter()`, skipping frames when more than 150 ms behind so sound
  and picture never drift; `--timing` reports the result.

Related docs: [`SCENE_API.md`](SCENE_API.md) for the scene/context API and the
frame/chrome grid, `engine/chrome.py` for the header / transport / subtitle /
spectrum furniture, `engine/timeline.py` for the lyrics.
