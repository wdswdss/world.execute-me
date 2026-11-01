# 提示词文档

这支 MV 的创作过程与可复用的指令都在这里，分三块：

| 文件 | 用途 |
|---|---|
| [creation-prompts.md](creation-prompts.md) | **创作提示词整理**：按轮次记录实际提出过的需求、场景位置与修改方向，文末有[合并使用版](creation-prompts.md#combined-prompt)。[纯文本版](creation-prompts.txt) 方便本地保存。 |
| [method.md](method.md) | **方法论**：怎样让人给意图、agent 写场景、静帧验收，包含分工、验收标准和常见失败模式。 |
| [templates/](templates/) | **可直接复制的模板**：项目 brief、场景 spec、review 回合、真实例子、agent 行为准则。 |

姊妹仓库 [yym8224961/world.execute-me-ascii](https://github.com/yym8224961/world.execute-me-ascii/blob/main/docs/prompts/creation-prompts.md) 里的 25 轮提示词，是终端播放器形态下把画面语言定下来的那一段；本仓库的 `creation-prompts.md` 从「做成 4K60 视频」开始接力。

配套阅读：[`../ARCHITECTURE.md`](../ARCHITECTURE.md)（帧的生命周期与模块边界）、[`../RENDERING.md`](../RENDERING.md)（4K 管线与分帧重渲）、[`../SCENE_API.md`](../SCENE_API.md)（写一个场景需要的 API）。
