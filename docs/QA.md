# QA notes — WORLD.EXECUTE(ME);

Snapshot of the automated and visual checks that gate the final render.

## Automated sweep — `tools/check_timeline.py`

| check | result |
| --- | --- |
| scene schedule | 21 scenes, 42/42 dispatch edges, max boundary delta 0.000000 s, no gaps/overlaps |
| lyric coverage | 48 timeline lines, 0 gaps, every line inside its section |
| outro progress | strictly `< 100` before the cut: min 98.973 %, max 99.975 % — PASS |
| CJK on the stage surface | 0 cells (bilingual lyric text only lives in the subtitle rows 49/51) |
| NaN / Inf in scene meta | 0 |
| runtime exceptions | 0 after the two `ctx.line_i is None` crashes in s09/s10 were fixed |
| glyph coverage | 0 missing glyphs after adding ╨ … ▸ — ▐ › ◂ to the atlas (519 glyphs) |

`qa/check_timeline.json` holds the raw report; `qa/overview_01..14.png` are the
5-second contact sheets (one frame per second over the whole song).

## Visual checks

- Every scene reviewed as a contact sheet (`qa/sheet_*.png`, `qa/final_*.png`) plus full-res spot frames at key beats.
- Boundaries checked at `t0+0.05` / `t1-0.05` for all 21 scenes — no visual pops, chrome stays constant.
- Subtitle strip: English karaoke line on row 49, Chinese on row 51, both inside the dedicated 5-row band; long lines auto-shrink. Top-right chrome is English-only by design.
- Subtitle zone: 12 rows (48-59) with 46 px EN / 38 px CN lines, frame rules and a faint separator; no bottom spectrum band.
- Heart beats: s14 finds/fills `HOLE#001` (a hole that should not exist) plus `DENT#001–003`
  (three local concavities) and re-checks the same defect set on the heart in s18.

## Performance

- Per-frame worker cost after the fused-pass optimisation: draw 14–120 ms (scene dependent),
  chrome ≈ 12–47 ms, compose ≈ 114–192 ms, subtitle ≈ 20–31 ms, post ≈ 240–470 ms.
- Full movie: 6357 frames at 1920×1080 / 30 fps.
- Rendering is deterministic per frame (`rng` seeded from frame index), so stills, segmented
  renders and the terminal player all produce identical content.

## Polish pass 2 (after the first full render)

- s01_boot power phase: added a centre **PHASE SCOPE** panel (live phase waveform +
  EQ bars + FFT readout) filling the previously empty middle band, plus a telemetry
  dot stream above the AC bus and 7 travelling electron heads instead of 4.
- s07_happy: added a full-screen radial glyph burst, beat-locked scan rings, six
  scrolling hex columns in the gaps between panels and two marquee bands; smiley is
  larger and breathes on the beat. The frame now moves across the whole stage.
- s14_heartfix: added a cardiac scan field (mesh grid, concentric rings, 16 radial
  spokes, edge rulers, left/right scale bars, drifting dust) so the assembly and
  patching phases are not half-empty.
- Re-rendered the entire 6357 frames with the same settings (`--crf 21 --preset faster`).

## v2 final verification (2026-10-31)

- Render: `tools/render.py --start 0 --end 211.905 --workers 10 --preset faster --crf 21`
  → 6357/6357 frames in 1650 s (3.9 fps avg).
- Mux: `tools/encode.py --copy` → `out/world_execute_me_phone.mp4`
  143.7 MB, 211.9 s, h264 1920x1080 30.0 fps 5424 kb/s, AAC 48 kHz stereo.
- 16-frame contact sheet `qa/v2_sheet.png` at 2/12/21/26.5/45/63/68/90/105/120/136/141/150/165/190/205 s:
  boot power + scope, boot countdown, title scramble, title formed, AC/DC sine,
  SATISFACTION bar, EXECUTION + happy smiley, F→M, HEARTBEAT ECG, ISOLATION,
  heart with hole+dents, heart being patched, count EXECUTION, ALL (only execution),
  trapped-in-love FREE/trapped, red EXECUTION — all correct, no missing-glyph '?'.
- Terminal player: `python bin/asciimv.py` (see --help) renders the same 192x60 grid
  as ANSI; `--still T` prints a single frame, `--from/--to`, `--width`, `--no-audio`,
  `--list` documented in docs/TERMINAL.md.

## v3: subtitles-only bottom zone (user request)

- Removed the bottom spectrum band and its ruler entirely (rows 53-59); the freed
  space became a 12-row subtitle zone (rows 48-59).
- Subtitles are now large and always bilingual: EN 46 px Consolas with karaoke
  progressive highlight, CN 38 px Microsoft YaHei below it, both centred inside a
  framed zone with side rails, a faint separator and EN/ZH anchors.
- EN lines now use per-character font fallback, so the multilingual counting line
  renders "네" (Malgun Gothic) and "六" (YaHei) instead of tofu boxes.
- Re-rendered all 6357 frames (`out/full_v3.mp4`, 961 s, 6.6 fps), muxed to
  `out/world_execute_me_phone.mp4` (132.5 MB, 211.9 s, h264 1920x1080 30 fps
  5003 kb/s, AAC 48 kHz stereo). Proof crops: `qa/subtitle_proof.png`.

## v4: baked subtitles + cropped bottom + heart/tangent fixes (user feedback)

1. Subtitles were missing from the encoded MP4: `tools/render.py` ignored the
   return value of `Chrome.draw_subtitles` (it builds a new image). Fixed to
   `img = _W["chrome"].draw_subtitles(img, t)`. Spot-check after re-render must
   extract frames FROM the MP4, not from tools/still.py.
2. Bottom cropped: subtitle band 12 -> 8 rows (rows 48-55, EN row 50 / CN row 53)
   plus a 4-row footer (rows 56-59) with per-line lyric progress, "LINE nn/48
   EN-ZH" readout and a scrolling system telemetry marquee; total bottom chrome
   1080-864 = 216 px instead of 324 px.
3. s03_infinity sliding tangent: was a fixed 149-cell line that sliced across the
   wave field and panels. Now a clipped segment: half-extent = 34/hypot(1,slope)
   scaled by RMS, clipped to rows 11-36 / cols 5-187, dashed, with end caps and a
   contact dot, so it gets shorter on steep slopes and never crosses the HUD.
4. Heart silhouette: engine/art.py heart_fill rewritten as the classic implicit
   heart (solid body, natural cleft and apex); dents are shallow radial
   deformations of the field (concave bites on the silhouette) instead of interior
   circles; s13/s14 legacy "carve the cleft" wedges removed; s15/s16/s18 share the
   new silhouette. Fixes "reads like a head with two ears".

## v5: subtitle Latin-only + stable reading area + lyric-aligned AC/DC + late ∞

1. Counting line EN subtitle was "Ein, dos, trois, 네, fem, 六, execution" — Korean
   and Chinese glyphs inside the English line read as mojibake on some players.
   Now romanised: "Ein, dos, trois, ne, fem, liu, execution"; CN line unchanged.
2. Subtitles are now composited AFTER the CRT post pass (tools/render.py,
   tools/still.py), so glitch/tear/scan effects never distort the reading area.
3. s04 AC/DC: the conversion now follows the lyric. Pure AC with
   "AC >>> DC [ ARMED ]" for the first ~1 s, then a visible SWITCHING ramp with a
   CONVERSION % bar, AC SOURCE fading / DC OUTPUT charging, ending fully
   RECTIFIED at the end of the line (was: already rectified when the line began).
   Also replaced the noisy hex-letter ruler columns with clean coordinate ticks.
4. s03 infinity: the lemniscate is no longer drawn before the "If I approach
   infinity" line; in phase 4 it grows from small to swallow the stage
   (`_hero_geom(0.30 + 0.70*pl)`), so 30-40 s has no ∞ symbol.

## v7: typewriter subtitles + varied outro lyrics

1. Subtitles are typed out instead of appearing whole: EN reveals over the first
   72 % of each line, CN over the first ~70 % (both start together), followed by a
   small accent-coloured "typing head" block that blinks until the line completes.
   Nothing is pre-rendered in the un-typed part, so there is no karaoke sweep.
   Same logic mirrored in `bin/asciimv.py` (`n_sung` / `cnum` reveal counts).
2. The outro no longer repeats "Execution, execution" three times:
   192.19 "Execution, execution" / 执行，执行; 195.88 "The loop is still running" /
   循环仍在运行; 199.58 "I will execute you again" / 我会再一次执行你;
   203.27 "Execution" / 执行 (red, final).

## v8: beat-synced typing, red 3:04, F->M rebuild (1:30), press at 1:12

1. Subtitle typing is now quantised to the song's 8th-note grid
   (`_rhythm_progress`: step = BEAT/2, last 3 steps reserved), so characters
   appear in rhythm with the music instead of a smooth sweep; both languages share
   the same reveal count and the blinking head disappears on the final step.
2. 3:04 ("I know the algebraic expression of love", 184.804-188.496) added to the
   red subtitle zones at 0.90 heat.
3. s10_transform F->M segment rebuilt: the hero is now a code-glyph morph - the
   letter F is drawn out of hundreds of "F" characters which sweep left-to-right
   and recombine into "M" (each glyph flips to M on arrival), plus a new
   "GENDER.SWITCH PROGRESS" bar (rows 28-29, cols 40-152) whose cells literally
   turn from F to M as the value rises, ending "M 100% LOCKED".
4. s08_trapped 1:12: added a hydraulic press - the recursive boxes compress
   vertically 1.5x faster than horizontally, two-cell-thick plates close in from
   above/below, side bars from left/right, arrows + "COMPRESSION nn% / HOLDS n /
   STRESS nn" readout, and the prisoner figure is squashed from 7 cells to 2 as
   the press closes (beat-locked jolt on strong pulses).

## v9: cursor weight, textbook AC/DC, beat-locked session frames

1. Typing head doubled: EN cursor width max(9, 46*0.26)=12 px (was ~5 px) and CN
   max(10, 38*0.28)=11 px (was ~5 px); still blinks at 5 Hz and disappears on the
   last revealed glyph.
2. s04 `_ph_rect` now follows the textbook picture
   (DC = flat constant line, AC = sine crossing zero):
   - stage 1 `m1` (pl 0.06-0.30) folds every negative half-cycle up -> the wave
     becomes all-positive humps (rectification);
   - stage 2 `m2` (pl 0.34-0.72) filters the ripple away -> the curve becomes a
     FLAT constant DC level (LVL = 0.78 Vp), the AC ghost and the bar fill fade
     out, and the "═" level line is drawn constant;
   - the caption switches from "AC: V(t)=Vp*sin(wt) -> current direction
     ALTERNATES (crosses 0)" to "DC: V = CONSTANT -> current direction NEVER
     changes", the plates report direction/ripple/status accordingly
     (AC LIVE->FADING->OFFLINE, DC IDLE->CHARGING->RECTIFIED).
3. s08 1:12: removed the hydraulic press rig (plates, arrows, COMPRESSION /
   HOLDS / STRESS readout). Instead the SESSION nesting frames are beat-locked:
   `bounce = exp(-4.5 * beat_p)` gives a sharp attack on every beat, the boxes
   scale by `1 - 0.13*bounce - 0.03*bar_pulse` (both axes now equal, so the frames
   breathe instead of being crushed), the prisoner squashes slightly with the
   same bounce, and the readout is "FRAME PINCH nn% / BEAT SYNC nn% / bars / walls
   CLOSING / frames 5 deep".

## v11: startup aperture, bottom music bar, RUN, smaller years, RNA + god girl, 3-D globe

1. **Startup animation** (s01_boot `_startup`): 0.00-0.55 s a bright horizontal line
   grows from the centre; 0.55-1.25 s it opens vertically into a rectangle (bright
   edges + ◉ corners + travelling scan line inside); 1.25-1.95 s the aperture fills
   the frame with an overshoot flash, then the normal intro continues. Caption
   "POWER ON // DISPLAY nn% // SIGNAL OK".
2. **A.D./B.C. year numbers** (s04 `_ph_time`) reduced from 8 to 5 cells tall and
   moved down one row so they no longer dominate the frame around 0:52.
3. **Music scroll bar** (chrome footer, very last row, no layout growth): per-column
   peak envelope of the whole song (cached `_wave_profile`), played part in the
   current accent colour, unplayed dim, a white `▌` playhead, `♪ m:ss` on the left
   and `AUDIO m:ss / 03:31` on the right.
4. **RUN** (s01_boot after the 3-2-1 countdown): a big painted "RUN" scales in at
   13.4-14.5 s with "▶ EXECUTION STARTED // SIMULATION LIVE" and a ✦ burst, filling
   the previously empty tail of the intro.
5. **AC/DC** reverted to the previous delivered look (per user request): the wave
   folds from sine to |sin| with the 2/π DC level line; the textbook two-stage
   flattening was removed.
6. **RNA** beside the eggplant (left, 1:16) and tomato (right, 1:19): A/U/G/C strand
   with backbone, polymerase marker, 5'/3' caps and a `┤ mRNA ├` readout.
7. **God girl** (1:25-1:28, s09): the reference maid is now drawn in ASCII — blue
   wavy hair, blue **cat ears**, white frilled headband, one open blue eye + one
   winking eye, blush, open smile, navy dress with white apron and ribbon, plus a
   **rotating golden halo** (✧-dotted ellipse + dim outer ring) and "HALO / DIVINITY
   100% / BLESSING ACTIVE · RADIANCE OK".
8. **1:00 STIMULATIONS** rebuilt by scenes-a as a pseudo-3D neural globe: 7 latitude
   rings + 5 rotating meridians with Lambert lighting, 8 electrode probes, ⚡ bolts,
   scanner ring and spike trains on the surface (draw 13.7 ms median).

## v12: round-14 feedback pass

- Subtitles are BLUE in normal sections (EN 206/233/255 + dim 84/143/210, CN 128/192/255,
  accent 96/176/255); red zones unchanged. Terminal player colours matched.
- Startup animation now overlays the WHOLE 60x192 frame (header, footer and subtitle
  band included), not just the 45-row stage: line -> opening rectangle -> full frame;
  lyrics hidden until t=1.62.
- Music bar (footer last row) is now a live scrolling waveform of the last ~4 s of the
  song (band energy, per-window normalised) that sways with the audio instead of a
  progress bar; colour follows the section accent.
- A.D./B.C. years drawn crisp with block ramp (RAMP_BLOCK, gain 2.4) on cleared panels,
  captions moved to row 24.
- s08 stick figure: label moved to cy-9 and the figure is drawn after it, so the head
  is never overwritten (also for the squeezed 2-row state).
- s09 "only god" portrait replaced with a real pixel-art portrait generated from
  qa/ref_god.png: `tools/make_god_pixels.py` keys out the blue background, downsamples
  to 48x60 pixels, quantises to 40 colours + transparency and writes
  `engine/god_pixels.py`; s09 renders it as colour half-blocks (█ / ▀ with bg), with a
  wide golden halo ring, crown glow, aura sparkles and a DEUS.SOLUS label.

## v13: round-15 feedback pass

- Music bar: waveform confined to cols 12..151 and the `♪ m:ss` / `AUDIO m:ss`
  labels get their own reserved columns with a divider, so nothing covers the wave.
- Post-processing: bloom threshold raised 150->186 and strength 0.55->0.40, chromatic
  split 9->5 px, grain 3.1->2.3, and a 1.36/0.36 unsharp-mask pass added after bloom;
  small UI text and the big years are visibly crisper.
- A.D./B.C years restored to h=8 solid RAMP_BLOCK digits (gain 2.8) on cleared panels.
- s14 heartfix: scan sweep band is now a 5-row soft gradient (lead/trail fade) and the
  scan arm beam has a 4-row glow trail — the sweep glides instead of jumping.
- s08 trapped: SESSION frames squeeze continuously with the lyric progress
  (`sx=1-0.60*sq`, `sy=1-0.80*sq`, `sq=p**1.2`) *together with* the closing walls, with
  the beat bounce kept; the figure shrinks with them.
- s09 god: portrait rebuilt from the new tight-crop reference `qa/ref_god2.png` as a
  blue-duotone pixel portrait (luminance mapped through a navy->ice ramp, 24 colours,
  56x70 px -> 28 cells wide), drawn opaque on a void backing, no halo ring / crown glow.

## v14: round-16 reverts

- s14 heartfix scan: back to a single-row sweep band and single-row SCAN beam
  (the 5-row soft gradient was rejected).
- s09 god: back to the previous colour pixel portrait (48x60 colour, halo ring +
  crown glow + aura + DEUS.SOLUS label) rendered on the opaque backing.

## v34: fixed-size infinity

- s03 infinity: the lemniscate no longer zooms in from far away / swallows the stage.
  It holds one box for the whole "If I approach infinity" line (`_HERO_FIX = (11, 47, 98, 24)`)
  and is animated by a light wave sliding along the figure-eight path (`_inf_cells()` bakes
  per-cell ink + curve position u; `flow = u - lt*0.55` drives the band/head). Fade-in 0.26 s
  from 40.807 s.
- v34 cut re-renders only s03 (frames 1782-2669, 888 f) and splices it into the subbed v33
  master: `v33_subbed[0:1782] + seg + v33_subbed[2670:]`, then `mux_sfx` -> tools/finish_v34.sh.
- s02 title (21-25 s) unchanged from v33: desk/monitors stay drawn under the code storm and
  the forming title; `_dissolve` / `_regather` are no longer called from draw().

## v35: multilingual counting line (2:39-2:41) restored

- The bridge-solo count line at 158.957-161.730 is multilingual in the song (German ein,
  Spanish dos, French trois, Korean 넷, Swedish fem, Chinese 六). v5 had romanised it to
  "ne / liu" because "glyphs read as mojibake on some players". Now restored to the original
  scripts: EN subtitle = "Ein, dos, trois, 넷, fem, 六, execution"; CN line unchanged.
  The subtractive subtitle layer is PIL-rendered per script (chrome `_font_for`: Latin ->
  Consolas, Hangul -> Malgun, CJK -> YaHei), so nothing is lost in the burn-in.
- chrome.py `draw_subtitles`: the keyword glow ("execution") used to measure its x-offset with
  the Latin font only; on a mixed-script line that misplaces the highlight. It now measures the
  prefix with `runs_width()` so each glyph is counted with the font that draws it.
- bin/asciimv.py: EN subtitle centring used `len(en)` (code points) instead of `_disp_width(en)`,
  so a line with full-width glyphs sat 2 cells off; fixed.
- Cut: only the 220 frames 9530-9749 (158.833-162.500 s) are affected. Re-rendered that range
  subtitle-free (`MV_NOSUB=1`), re-rendered the 220 subtitle PNGs into `out/subs_v29_4k/`,
  composited, and spliced into the subbed v34 master: `v34[0:9530] + seg(220) + v34[9750:]`,
  then `mux_sfx` -> tools/finish_v35.sh. Verified: 12954 frames / 3:35.91, boundary diffs
  (frames 9529/9530/9749/9750/9751) are encode noise only, frame 9700 differs only in the
  subtitle strip.

## B站 封面（tools/cover_bili.py）

- 投稿封面 1920x1080（16:9）在 cover.py 的海报帧上重排：∞ 缩到 90x22（藏在标题上方），
  中间一行金色中文钩子「大肥鱼眼中的」（PIL 直接画在合成图上，画在 post 之前所以跟扫描线
  一起吃；paint_text 走 Consolas 没有中日韩字形，不能用），主标题放大到 10 cells，
  底部一行 "4K60 · 12954 FRAMES · UNOFFICIAL FAN MV"。
- 手机信息流缩到 320x180 仍能读出钩子+标题；输出 PNG 2.5MB / JPG(92, 4:4:4) 0.58MB，投稿用 JPG。

## 双比例封面（tools/cover_aspect.py）

- 一套设计出两个原生版面（不是裁切）：16:9 = 192×45 格 → 1920×1080；4:3 = 144×45 格 → 1440×1080。
  引擎按格网格排版，所以 4:3 是把画布收窄、字号/间距重排（`LAYOUT` 里的 `title_h`/`hook_frac`/`inf_w`）。
- 16:9 保留正片的 page chrome（页眉/走带条/字幕条/波形），4:3 用干净海报框（细线+状态行+MILI 署名），
  因为 chrome 的页眉/页脚是按 192 列写的，144 列会挤。
- 中文钩子「大肥鱼眼中的」用 PIL 画在合成图上、在 post 之前（`tools/cover_bili_lib.py`），
  所以扫描线/颗粒/色散同样作用于字；`Frame.paint_text` 用 Consolas，没有中日韩字形不能用。
- 4:3 标题 h=8（135 列）；h=7 时笔画被 mask 的 hard 阈值吃掉会变形，h=10 又超出 144 列。
  两个比例都在 320 宽缩略图下验证过可读。

### 纯画面版（无文字钩子/歌词）

- 用户要求封面去掉中间的「大肥鱼眼中的」和底部歌词后，`cover_aspect.py` 增加 `--variant plain`（默认）：
  只保留 ∞ + 心 + 大标题 + MILI 署名，左右 HUD 小字照留（那是画面质感，不是「字」）。
- plain 版不用正片 page chrome：chrome 的页眉/页脚按 192 列写死，且会给成片字幕条留一条空带
  （做封面像未加载的播放器）；改用 `_clean_frame`：stage 居中、页眉 rule + 底部 rule + 署名行。
- 参数：16:9 `inf 107×26 / title_h=10 / stage_top=7`；4:3 `inf 98×24 / title_h=8 / stage_top=7`。
- 交付：`out/cover_16x9.jpg`（1920×1080）、`out/cover_4x3.jpg`（1440×1080），PNG 与 `_thumb320` 同名。
