# audio/ — 音频不随仓库分发

这支 MV 用的是 **Mili《world.execute(me);》**，版权归 Mili / 权利人。
仓库里**不含**任何歌曲音频，只有引擎生成的、与具体录音无关的派生数据。

## 你需要自己放进来

```
audio/
  song.wav       # 你自己合法持有的音频（48000 Hz，单声道或立体声都行，引擎会按需重采样读取）
  sfx.wav        # 可选：音效层（转场、打字、电流声），没有就跳过混音
```

`engine/assets.py` 只要求 `song.wav` 能被 `wave` 模块读出来；时长/采样率不必和原曲一致，
但**时间码是对着原版录制的**——换了版本（比如现场版、加速版）时间轴要重排
（`engine/timeline.py` + `engine/sceneapi.py` 的 `SCHEDULE`）。

## 生成派生数据

```bash
python tools/build_assets.py
```

会写出（都被 `.gitignore` 忽略）：

| 文件 | 内容 |
|---|---|
| `audio/spectrum.npz` | 每帧 64 段频谱包络（页脚波形用） |
| `audio/beats.npz` | 节拍网格（用于 `ctx.beat_p` / `bar_p`） |
| `audio/beats.json` | 同上，人可读（130 BPM、4/4 时可直接手写） |
| `audio/song_info.json` | 时长、采样率、RMS 曲线摘要 |

## 版权

- 不要把这个目录里的音频 push 上去（`.gitignore` 已经挡住 `*.wav|*.mp3|*.m4a|*.flac|*.ogg`）；
- 成片若上传到平台，按平台规则与原权利人的二创声明投稿（本项目按"非商业同人"处理，
  见 [`../NOTICE.md`](../NOTICE.md)）；
- 若你是权利人希望仓库移除任何内容，开 issue，24 小时内处理。
