# 提示词模板

给"写代码的 agent"用的可复制片段。按使用顺序：

| 文件 | 什么时候用 |
|---|---|
| [`00-project-brief.md`](00-project-brief.md) | 项目开头，只发一次。定死网格/图层/技术栈/禁止项/验收 |
| [`01-scene-spec.md`](01-scene-spec.md) | 每个场景一份。分层、运动切片、固定文案、验收帧 |
| [`02-review.md`](02-review.md) | 打回时。四种形态 + 反模式（怎样写一定返工） |
| [`03-examples.md`](03-examples.md) | 三份真实 spec（∞ / 报数 / 结尾），可直接改成你的 |
| [`04-agent-rules.md`](04-agent-rules.md) | 给 agent 的"现场守则"——多帧渲染/并行的坑，贴在 brief 后面 |

方法论（为什么这么写、循环节奏、踩过的坑）在
[`../method.md`](../method.md)。

## 最短可用流程

```bash
# 1. 发 brief（00）
# 2. 发第一个场景 spec（01 + 03 里的例子改）
# 3. agent 交代码 + 三张静帧
python tools/still.py --t 2.0 --out qa/s01_2.png      # 你也自己看一眼
# 4. 打回（02 的 A 形态），一次一条
# 5. 过了就进渲染队列，换下一个场景
```

一支 3 分半的 MV 大约 21 个场景；按这个流程一个人 + 一个 agent 大约 2–3 天能出第一版。
