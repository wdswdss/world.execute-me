# fonts/ — 字体不随仓库分发

原画用的字体都是**商业字体**，不能放进仓库：

| 用途 | 字体 | 说明 |
|---|---|---|
| 英文主字（标题、HUD） | **Consolas** / Consolas Bold | Windows 自带；字形是双宽等宽的方块感，是整片气质的一半 |
| 中文（ZH 字幕行） | **微软雅黑** Microsoft YaHei / YaHei Bold | Windows 自带 |
| 韩文（`넷`） | **Malgun Gothic** | Windows 自带 |
| 符号（箭头、框线） | Segoe UI Symbol / Arial | Windows 自带 |

`engine/font.py` 按这个顺序找字体：

1. 环境变量 `$ASCIIMV_FONTS`（目录列表，`;` 或 `:` 分隔）
2. 本目录 `fonts/`（你可以自己放，`.gitignore` 只保留本 README）
3. 系统字体目录：`C:\Windows\Fonts`、`/System/Library/Fonts`、`/usr/share/fonts`、`~/.fonts` 等
4. 找不到时回退到 DejaVu Sans / Noto（Linux 常见），字形会变，但不会崩

## 想完全复刻原画

把 Consolas / 雅黑 / Malgun 拷进这个目录（**不要提交**）：

```
fonts/
  consola.ttf  consolab.ttf  segoeuisl.ttf  arial.ttf  arialbd.ttf
  msyh.ttc  msyhbd.ttc  malgun.ttf  malgunbd.ttf
```

或者：

```bash
export ASCIIMV_FONTS="D:/fonts/ms;C:/Windows/Fonts"
```

## Linux / macOS 上的观感差异

- Consolas 缺失 → 回退 DejaVu Sans Mono：等宽但字形更"圆"，标题的方块感会弱一些。
- 雅黑缺失 → 回退 Noto Sans CJK（需 `fonts-noto-cjk` 包），中文能显示但字重不同。
- 韩文缺失 → `넷` 会变成方块；装 `fonts-noto-cjk` 或在 `fonts/` 放 Malgun。

如果只是想看效果，1080p 下这些差异不影响构图；做正式成片建议在 Windows 上渲。
