# 架构

一句话：**一个 192×60 的字符网格，被当成一台低分辨率显示器来画**。
每格 = 一个字符 + 一个前景色 + 一个背景色；格子 10×18 px（`MV_SCALE` 乘倍）。
所有画面都是"往格子里写字"，最后由 `post.py` 当作 CRT 屏幕过一遍。

```
                 t, beat, bars, 频谱                    meta（glitch/bloom/flash…）
                        │                                        │
   SCHEDULE ──► Ctx ──► scene.draw(ctx) ──► Frame(45×192) ──► chrome.build() ──► post.process() ──► ffmpeg
   (21 段)      (场景上下文)   (只画舞台)      舞台帧            60×192 整帧           CRT 后处理
```

## 1. 网格与舞台

`engine/layout.py` 是唯一的尺寸真相：

| 常量 | 值 | 说明 |
|---|---|---|
| `COLS × ROWS` | 192 × 60 | 整帧，含页眉页脚 |
| `STAGE_W × STAGE_H` | 192 × 45 | 场景能画的区域（`STAGE_Y=2` 起） |
| `CELL_W × CELL_H` | 10 × 18 px | `MV_SCALE=2` 时 20 × 36 |
| `PX_W × PX_H` | 1920×1080 / 3840×2160 | |
| `FPS` / `DURATION` | 60 / 211.905 + 4.0 尾留白 | |

场景拿到的永远是 `Frame(45, 192)`，**碰不到页眉（row 0-1）、走带条（row 47）、
字幕条（row 48-55）、页脚（row 56-59）**。这是全片能保持"一个界面"的原因。

## 2. 一条帧的生命周期

1. `sceneapi.Ctx(t)` 算好时间语义：`local`（场景内秒）、`beat_i`/`bar_i`、`beat_p`/`bar_p`、
   `pulse`（每拍衰减脉冲）、`rms`/`bands`（音频特征）、当前歌词 `line`、以及 `meta` 默认值。
2. `scenes.sNN.draw(ctx)` 返回舞台 `Frame`。场景可以改 `ctx.meta`（`glitch`/`flash`/`bloom`/
   `tint`/`shake`/`grain`）来影响后面的 CRT 后处理。
3. `chrome.Chrome.build(stage, t, scene, assets)` 把舞台贴进 60×192 的整帧，再画页眉、
   走带条（进度 + 时间码）、字幕条、页脚频谱与滚动字。
4. `post.Post.process(img, fi, t, meta)` 做 CRT：扫描线 × 孔径 × 暗角（预乘成一张 `mul`）、
   漂移亮带、色散、抖动、闪白、噪点、颗粒，还有随时间推进的"老化"（彩色边越来越宽）。
5. `tools/render.py` 把整帧塞进 ffmpeg 的 rawvideo 管道。

## 3. 模块一览

| 文件 | 职责 |
|---|---|
| `layout.py` | 网格/像素/时长常量 |
| `palette.py` | 颜色与 17 级色阶（`ramp()`），`mix()`/`shade()` 等 |
| `font.py` | 字符 → 覆盖率掩码：自己用 PIL 光栅化、裁到墨水框、细字加 1px 腐蚀；带字形缓存与字体查找（`font_path()`） |
| `frame.py` | `Frame`：`ch`（int16 字符索引）+ `fg/bg`（每格 RGB）；`paint_mask` / `paint_mask_colored` / `paint_text` / `box` / `compose` |
| `widgets.py` | 面板、进度条、折线、表盘、刻度尺等复用部件（都画在字符网格上） |
| `art.py` | 造型掩码：心、∞、番茄、茄子、猫、鲸鱼…（`heart_filled` 之外大多只有描边） |
| `fx.py` | 缓动、噪声、抖动、溶解、粒子、Rng |
| `timeline.py` | 歌词 + 时间码（`_L(t0, t1, en, zh, section)`），字幕的唯一来源 |
| `sceneapi.py` | `SCHEDULE`、`Ctx`、`draw_scene()`、场景热重载 |
| `scenes/s01…s21` | 21 个场景，各自 ~300-900 行，互不 import |
| `chrome.py` | 页眉/走带条/字幕条/页脚；字幕按字符脚本选字体（Latin=等宽、CJK=雅黑、Hangul=Malgun） |
| `post.py` | CRT 后处理与"老化" |

## 4. 约定（写给要改代码的人 / agent）

- **场景内不要有跨场景状态**：同一场景的同一帧必须可重入（渲染是多进程按帧号并行的）。
  随机数只准用 `ctx.rng(seed)`，它按帧号播种 —— 这样任何一帧都能单独重渲。
- **不要画到舞台外**：`Frame(45,192)` 越界会静默丢弃；想加页眉就改 `chrome.py`。
- **时间只从 `ctx` 拿**，不要 `time.time()`；否则重渲区间会不一致。
- **字幕里不要塞中文到 EN 行**：`chrome.draw_subtitles` 按 `timeline` 的 EN/ZH 两行分开画，
  EN 行混 CJK 会让字形选择和居中一起出错（历史上踩过）。
- **性能**：一帧 1080p 约 0.6 s/核。重的场景（s02/s03/s10）要避免每帧重新光栅化文字——
  `F.text_mask` 有缓存，但如果 h_cells 或文本变了就会重新算。

## 5. 已知技术债

1. `s04`–`s08` 各自复制了一份字符栅格辅助函数（`paint/bigtext/cell/…`），应提取为
   `engine/cellraster.py`。
2. `post.py` 里多处像素级常量按 1080p 手调，`MV_SCALE=2` 时靠 `SCALE` 乘，边缘颗粒感略有差异。
3. 场景的 `draw()` 普遍偏长（300-900 行），缺少单元测试；目前靠 `tools/check_timeline.py`
   抽样渲染全片做冒烟检查。
