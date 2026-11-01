# 渲染管线

## 三条渲染路径

| 命令 | 产出 | 用途 | 成本（12 核 / 1080p） |
|---|---|---|---|
| `tools/still.py` | 单帧 PNG | 看构图、验收场景 | ~1.5 s |
| `tools/render.py` | 无声视频（rawvideo → ffmpeg） | 出片、区间重渲 | ~1.7 fps/worker |
| `bin/asciimv.py` | 终端里的 ANSI 动画 | 直接看、做动图 | 实时 |

`render.py` 的 `--workers` 是按**帧**并行的：每个 worker 拿帧号自己算 `t = fi / FPS`，
场景内所有随机数都由帧号播种，所以**任何一帧都能单独重渲且结果一致**。
这是能"只重渲改动区间再拼接"的前提。

## 全片出片（1080p）

```bash
export FFMPEG=/usr/bin/ffmpeg        # 或确保 ffmpeg 在 PATH
python tools/build_assets.py         # 音频 -> audio/spectrum.npz, beats.npz, beats.json

python tools/render.py --workers 8 --preset medium --crf 17 --out out/video.mp4
python tools/render_subs.py --outdir out/subs          # 字幕 PNG（与帧号同名）
python tools/compose_subs.py --base out/video.mp4 --subs "out/subs/%05d.png" \
       --start-frame 0 --encoder nvenc --crf 21 --bitrate 18M --maxrate 28M \
       --out out/video_subbed.mp4
python tools/mux_sfx.py --video out/video_subbed.mp4 --out out/final.mp4
```

- `compose_subs.py` 用 `-framerate 60 -start_number <start-frame>` 读序列，overlay 到 0:0，
  `-c:v` 用硬编（nvenc/x264 都可以）。字幕 PNG 的编号 = 视频帧号，所以区间重渲时
  `--start-frame` 必须等于该区间的第一帧号。
- `mux_sfx.py` 把 `audio/song.wav` + `audio/sfx.wav` 混在一起（`apad` + `amix normalize=0`），
  视频流直接 copy；总长取三者最大。

## 4K 母版

同一套命令加一个环境变量：

```bash
export MV_SCALE=2                    # 格子 20×36 -> 3840×2160
python tools/render.py --workers 10 --preset faster --crf 17 --out out/v4k.mp4
```

4K60 整片在 12 核机器上约 85–100 分钟。**别一次性渲全片再改小地方**——见下面。

## 分帧拼接：只重渲改动的区间

剪辑里 90% 的返工都是"改 3-10 秒的画面"。做法：

1. 算出改动的帧区间 `[A, B)`（`A = round(t0 * 60)`，`B = round(t1 * 60)`）
2. 只渲这一段（`render.py --start t0 --end t1`），烧上对应字幕（`--start-frame A`）
3. 用 trim + concat 把旧母版的两头和新段拼起来

```bash
ffmpeg -y -i out/old_subbed.mp4 -i out/_seg_subbed.mp4 \
  -filter_complex "\
    [0:v]trim=start_frame=0:end_frame=${A},setpts=PTS-STARTPTS[a];\
    [1:v]format=yuv420p,setpts=PTS-STARTPTS[b];\
    [0:v]trim=start_frame=${B},setpts=PTS-STARTPTS[c];\
    [a][b][c]concat=n=3:v=1:a=0[out]" \
  -map "[out]" -c:v h264_nvenc -preset p7 -tune hq -rc vbr -cq 20 \
  -b:v 18M -maxrate 28M -bufsize 56M -profile:v high -level 5.2 -r 60 \
  out/new_subbed.mp4
```

三次编码（旧母版已经压过一遍）会有轻微画质损失，所以**尽量攒批改动**再拼，
不要一句字幕就拼一次；想要零损失就把母版也存一份"段文件清单"（本项目就是这么做的：
`out/_seg_*.mp4` + 每次只重渲一段）。

## 验收：怎么确认"只有该变的地方变了"

别用眼睛看整片，用像素 diff：

```bash
# 逐帧比较新旧母版，只在字幕/画面该变的帧附近出现峰值
ffmpeg -hide_banner -i new.mp4 -i old.mp4 \
  -filter_complex "[0:v][1:v]psnr" -f null - 2>&1 | tail -3
```

项目里常用的两个检查：

- **整帧均值差**：编码噪声 0.8–2.4（PSNR > 45 dB 视为同画面）
- **局部带差**：某一行带的均值差 > 10 说明那里真的改了（换字幕时会看到）

以及 `tools/check_timeline.py` 的冒烟检查：抽样渲染全片，断言 0 异常 / 0 NaN /
EN 行无 CJK / 字形全部有掩码。CI 里跑的就是它（stride 调大以控制时间）。

## 故障排查

| 现象 | 原因 |
|---|---|
| `FileNotFoundError: ffmpeg` | 脚本里硬编码的 ffmpeg 路径不存在；用 `$FFMPEG` 或装到 PATH |
| 字幕是方块 | 系统缺 Consolas/雅黑/Malgun，`engine/font.py` 回退到 DejaVu/Noto，CJK 无字形 |
| 某个 worker 结果不一样 | 场景里用了 `time`/全局随机数（必须用 `ctx.rng()`） |
| 4K 比 1080p 糊 | `post.py` 的部分常量按 1080p 调的，`SCALE` 乘了但颗粒半径没跟着放大 |
| 拼接处一帧抖 | `A/B` 算错或 `--start-frame` 与 `trim` 不一致 |
