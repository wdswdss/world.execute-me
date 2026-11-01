# 贡献指南

欢迎 PR。这个项目最需要的是**新场景**、**可移植性修复**和**别的歌的适配经验**。

## 环境

```bash
git clone <your-fork> && cd world-execute-ascii
pip install -r requirements.txt     # numpy + Pillow
python tools/still.py --t 41.8 --out out/still.png    # 能出图就说明环境 OK
```

ffmpeg 只有出片才需要；字体见 [`fonts/README.md`](fonts/README.md)。

## 加一个场景

1. 在 `engine/scenes/` 新建 `sNN_name.py`，实现：

   ```python
   NAME = "sNN_name"
   def draw(ctx):
       fr = ctx.frame()
       ...
       return fr
   ```

2. 在 `engine/sceneapi.py` 的 `SCHEDULE` 里登记 `(t0, t1, "key", "sNN_name")`
3. `python tools/still.py --t <中点> --out qa/sNN.png` 看构图
4. `python tools/check_timeline.py --start t0 --end t1` 过检查
5. PR 里附 2–3 张静帧（PNG，1080p 即可）+ 一句话说明这一段在"执行"什么

## 场景代码的硬规则

这些不是风格偏好，违反了会产出不一致或崩坏的帧（原因见
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §4 与 [`docs/prompts/templates/04-agent-rules.md`](docs/prompts/templates/04-agent-rules.md)）：

- 只画 `Frame(45, 192)` 舞台；页眉/字幕条/页脚属于 `chrome.py`
- 时间只从 `ctx` 拿；**禁止** `time.time()`
- 随机数只用 `ctx.rng(seed)`；**禁止** 全局 `random` / `np.random`
- **禁止**模块级可变状态（渲染是多进程按帧并行的）
- 颜色从 `engine/palette.py` 取；不要写魔法 RGB
- 大段文字掩码要缓存（`F.text_mask` 自带缓存，但字号/文本变化会重算）

## 提交

- 一次 PR 一个场景或一类修复，别混在一起
- 不要提交：渲染产物（`out/`）、QA 帧（`qa/`）、音频（`audio/*.wav`）、字体（`fonts/*.ttf`）
- 提交信息用中文或英文都行，格式：`sNN: 一句话` / `fix: 一句话` / `docs: 一句话`

## 报告问题

开 issue 时请附：**时刻（秒）+ 一张静帧 + 期望的样子 + 你的系统（Windows/Linux/macOS）**。
"某一帧长得不对"这类报告，没有帧号是没法复现的——渲染是并行的，全靠帧号定位。

## 许可

提交即视为同意：代码以 MIT、画面以 CC BY-NC-SA 4.0 授权（见 [`NOTICE.md`](NOTICE.md)）。
注意 **不能** 把歌曲音频、商业字体、或任何第三方素材提交进仓库。
