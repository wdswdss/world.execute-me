# SCENE API — world.execute(me); ASCII MV

All paths below are relative to the project root.

Requires Python 3.10+ with numpy and Pillow (`pip install -r requirements.txt`).
Always run with `PYTHONIOENCODING=utf-8` on Windows (the console codepage is GBK
and will crash when printing `░▒▓█`).

```
python tools/still.py --scene infinity --n 8 --sheet qa/sheet_inf.png
python tools/still.py --t 30.5 --out qa/x.png
```

## The surface you draw on

`draw(ctx) -> Frame` renders the **stage**: `Frame(45, 192)` = rows 0..44, cols 0..191.
The chrome layer is added afterwards by the pipeline and is NOT yours:

- header row (0), rules, **subtitle zone (rows 48-59)** — never draw there.
- 1920x1080 total; cell = 10x18 px.

```python
from .. import palette as P, fx, widgets as W, art, timeline as TL
from .. import layout as L

def draw(ctx):
    fr = ctx.frame()          # cleared 45x192 Frame
    t = ctx.t                 # absolute song time (s)
    lt = ctx.local            # seconds since this scene started
    ...
    ctx.set_glitch(0.3)       # optional post FX hint 0..1.5
    ctx.meta["bloom"] = 0.5   # optional (default 0.35)
    ctx.meta["flash"] = 0.2; ctx.meta["flash_color"] = P.C["primary"]
    ctx.shake(4)              # optional camera shake in px
    return fr
```

Scene keys, modules and exact time windows (`engine/sceneapi.py` SCHEDULE):

| key | module | t0 | t1 | content |
|---|---|---|---|---|
| boot | s01_boot | 0.000 | 14.960 | data fill / initialisation (DONE) |
| title | s02_title | 14.960 | 29.730 | scramble all chars → WORLD.EXECUTE(ME); (DONE by Lead) |
| infinity | s03_infinity | 29.730 | 44.500 | ∞ redraw + growing scale |
| acdc | s04_acdc | 44.500 | 59.270 | AC→DC, dizzy, A.D→B.C, unite |
| stim | s05_stim | 59.270 | 62.962 | STIMULATION |
| satisfy | s06_satisfy | 62.962 | 66.654 | SATISFACTION progress bars |
| happy | s07_happy | 66.654 | 70.347 | happy + EXECUTION + two-side data scroll |
| trapped | s08_trapped | 70.347 | 74.040 | trapped in strange simulation |
| characters | s09_characters | 74.040 | 88.810 | eggplant / tomato / tabby cat / only god |
| transform | s10_transform | 88.810 | 103.580 | F→M, AM→PM, S→M, trance |
| heartbeat | s11_heartbeat | 103.580 | 110.964 | vibrations + completion → ECG |
| leaving | s12_leaving | 110.964 | 122.041 | nodes disconnect, richer/longer, glitch up |
| fragments | s13_fragments | 122.041 | 133.110 | erase fragments, disheartened, heartbreak, illegal args |
| heartfix | s14_heartfix | 133.110 | 147.880 | rebuild heart, fill holes + 3 dents |
| count | s15_count | 147.880 | 162.650 | EXECUTION x4 then EIN/DOS/TROIS/NE/FEM/LIU main frame |
| onlyexec | s16_onlyexec | 162.650 | 173.727 | THE ONLY EXECUTION, yandere possessive |
| study | s17_study | 173.727 | 188.496 | ML/LLM working principle collapse |
| trappedlove | s18_trappedlove | 188.496 | 192.190 | free vs trapped in love + heart check |
| outro99 | s19_outro99 | 192.190 | 203.720 | progress bar stuck at 99% |
| redexec | s20_redexec | 203.720 | 206.960 | huge red EXECUTION, same style |
| endtext | s21_endtext | 206.960 | 211.905 | only: PROCESS ENDED. THE LOOP REMAINS. |

## Ctx fields

`ctx.t` absolute time · `ctx.fi` frame index · `ctx.local` since scene start · `ctx.dur` scene length
`ctx.t0/t1` scene bounds · `ctx.section` section name · `ctx.sec_local` since section start
`ctx.beat_i`, `ctx.bar_i`, `ctx.beat_p` (0..1 in beat), `ctx.bar_p`, `ctx.pulse` (1 at beat → 0),
`ctx.bar_pulse`, `ctx.rms` (0..1 loudness), `ctx.bands` (64 floats), `ctx.line_i`, `ctx.line`
(current lyric dict: t0, t1, en, cn, section), `ctx.line_p` (0..1 in line)
`ctx.assets` — `bands_at(t)`, `rms_at(t)`, `vocal_at(t)`, `energy(t, win)`, `low_at/mid_at/high_at(t)`
`ctx.rng(seed)` → deterministic Rng: `.random()`, `.random((h,w))`, `.randint(a,b)`, `.randint(a,b,(h,w))`, `.choice(seq)`
`ctx.norm(a,b)` clamp-normalise t · `ctx.fade(t0,t1,fi,fo)` envelope · `ctx.gate(a,b)` bool
`ctx.set_glitch(g)` · `ctx.shake(amp)` · `ctx.meta` dict

## Frame primitives (engine/frame.py)

```python
fr.put(r,c,ch,fg,bg)                 # one cell; fg/bg are RGB tuples
fr.write(r,c,"TEXT",fg,bg)           # returns end col; CJK becomes 2 blanks (never use CJK on stage!)
fr.ctext(r,"TEXT",fg)                # centred
fr.rtext(r,"TEXT",fg,pad=1)          # right aligned
fr.fill_rect(r0,c0,r1,c1," ",fg,bg)  # fill (also sets bg)
fr.hline(r,c0,c1,"─",fg)  fr.vline(c,r0,r1,"│",fg)
fr.box(r0,c0,r1,c1,style,fg,bg,title)  # style 1 single / 2 double / 3 heavy
fr.paint_text("WORD", r0, c0, h_cells, fg=..., fg2=..., align="center")
    # big text from coverage mask; c0 is the anchor for align center/right;
    # h_cells 3..12 typical. RAMP_BLOCK default → solid readable letterforms.
fr.paint_mask(mask, c0, r0, w, h, ramp=..., fg=..., fg2=..., gain=1.8, alpha=1.0)
    # coverage mask (any size) → cells. gain ~1.8 for solid shapes, 1.0 for airy.
fr.paint_mask_colored(mask, c0, r0, w, h, color_fn, ramp=...)
fr.scramble_region(r0,c0,r1,c1,rng,density)  # random glyph corruption in region
fr.shift_region(r0,c0,r1,c1,dr,dc)
fr.tint_region(...) / fr.dim_region(...,f=0.5)
fr.get(r,c) -> char      fr.inb(r,c) -> bool
```

## Palette (engine/palette.py)

`P.C[name]` RGB tuples: void #03060b, void2, panel, panel2, grid, line, dim, mid, fg, white,
primary #5fe6ff, teal, green, grass, gold #ffc96b, amber, orange, red #ff5d6c, crimson, blood,
magenta, violet, blue, cyan2.
`P.mix(a,b,f)` · `P.shade(col,f)` · `P.dark(col,f)` · `P.RAMP_HI=" .:-=+*#%@"`,
`P.RAMP_BLOCK=" ░▒▓█"`, `P.RAMP_DOT`, `P.RAMP_VERT=" ▁▂▃▄▅▆▇█"`, `P.RAMP_ASCII`.

## Widgets (engine/widgets.py)

```python
W.progress_bar(fr, r, c, w, frac, fg, bg, label, style=1, show_pct=True, color_by=fn)
W.segmented_bar(fr, r, c, w, frac, cells=8, fg)
W.ecg_trace(fr, r0, c0, w, h, t, fg, fg_peak, grid=True, bpm=130, amp=1.0)
W.sparkline(fr, r0, c0, values, h, ramp, fg)       # single-line trace
W.plot_columns(fr, c0, r0, values, h, lo, hi, ramp, fg, dot=False)
W.braille_plot(fr, r0, c0, w, h, values, fg)       # 2x4 sub-cell plot, very sharp
W.matrix_rain(fr, t, seed=0, density=0.55, speed=9.0, fg=..., region=(r0,c0,r1,c1))
W.side_data(fr, t, seed=0, left_w=14, right_w=14, fg=...)   # 2-side scrolling data
W.data_column(fr, r0, c0, h, t, seed=0, speed=6.0, fg=...)
W.hex_dump(fr, r0, c0, rows, cols, t, seed=0, fg=..., step=0.35)
W.line_cells(fr, r0,c0, r1,c1, fg, ch=None)        # cell-space line
W.node(fr, r, c, state="on"|"off"|"dead"|"warn", fg, label, halo=0)
W.attention_matrix(fr, r0, c0, n, t, seed=0, fg)   # attention heatmap
W.token_grid(fr, r0, c0, rows, cols, tokens, weights, fg, highlight=-1)
W.marquee(fr, r, text, t, speed=12, fg) · W.typing(fr, r, c, text, t, start, cps, fg)
W.crosshair(fr, r, c, size, fg, label) · W.spinner · W.dots_progress
```

## Art masks (engine/art.py)

```python
egg = art.get("eggplant", w=640, h=780)   # dict: body leaf stem shine eye glint mouth blush + eyes=[(x,y,r),(x,y,r)]
tom = art.get("tomato", w=680, h=680)     # same keys
cat = art.get("tabby", w=760, h=820)      # body inner_ear stripes muzzle eye pupil glint nose mouth whiskers + eyes
heart = art.get("heart", w=600, h=560)    # solid heart coverage (add holes=[(fx,fy,fr)], dents=[...])
heart_o = art.get("heart_outline", w=600, h=560, thick=0.04)
inf = art.get("infinity", w=900, h=400)
# masks are float32 0..1 any size; draw with fr.paint_mask(mask, c0, r0, w, h, ramp=..., fg=..., gain=1.8)
```

## Audio / beat helpers (engine/assets.py, engine/timeline.py)

```python
A.beat_time(k), A.bar_time(b), A.beat_phase(t), A.bar_phase(t), A.beat_pulse(t), A.bar_pulse(t)
A.section_at(t) -> (name, t0, t1); A.SECTIONS; A.T0=0.190, A.BEAT=0.461538, A.BAR=1.846154
TL.LINES (list of dicts), TL.line_at(t) -> (i, line), TL.EVENTS dict, TL.COUNT_WORDS
TL.EVENTS["left_1"]=110.964, ["heart_repair_start"]=133.110, ["last_execution"]=203.720, ...
```

## Quality bar (this is graded)

1. **Dense**: the stage should usually be ≥ 50% covered with something; no long empty bands.
   Layer it: dim background (rain/grid/particles) + mid structure + bright foreground accents.
2. **Full-screen motion**: every frame differs; big translations/scale/pulses across the whole stage,
   not just a small widget. Use `ctx.pulse` / `ctx.rms` to drive scale, brightness, flash.
3. **Readable hierarchy**: important words big (`paint_text` h≥3), UI small. High-contrast accents on
   near-black background. Never leave text unreadable on top of busy noise: put a `fill_rect(...,bg=P.C["panel"])`
   behind panels first.
4. **Program-interface look**: panels, labels, brackets `[ ] │ ┌ ┐ ▸ ◂`, status lines, IDs, counters.
5. **CRT**: afterimages (draw the same shape 2-3 times with decaying alpha/offset), scanning lines,
   glitch via `ctx.set_glitch()`, chromatic feel via palette (red/cyan).
6. **Beat sync**: pulse on every beat, event hit on downbeats/lyrics. Each lyric line needs a visible action.
7. Verify with stills at 6-10 times per scene, including boundaries (`t0+0.05`, `t1-0.05`). Fix exceptions.
8. Do not edit shared engine files; put helpers inside your own scene module.
9. Keep each frame fast: target < 120 ms (loops over cells are fine; avoid per-cell Python work
   larger than ~200k ops/frame).
