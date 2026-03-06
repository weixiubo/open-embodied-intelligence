# 项目整理决策矩阵

## 结构结论

- 唯一活跃工程：仓库根目录当前这套代码。
- 主线来源：原 `大创agentV3/`，已平铺到根目录。
- 历史代码归档：`archive/code/`
- 历史文档归档：`docs/archive/`

## 目录级决策

| 原目录/对象 | 性质判断 | 最终去向 | 是否吸收 | 结论理由 |
|---|---|---|---|---|
| 根目录主线 | 唯一完整工程 | 保留为活跃工程 | 是 | 唯一同时具备入口、依赖、配置、数据、测试的候选。 |
| `228` | 早期原型快照 | `archive/code/legacy-228/` | 否 | 文件少且结构不完整，不具备主线资格。 |
| `229` | 中期快照/部分重复实现 | `archive/code/legacy-229/` | 部分 | 含重复和分叉实现；仅保留比对价值，不再并列存在。 |
| `229/assistant.py` | 与主线完全重复 | 仅作为归档快照保留 | 否 | 已确认内容与主线 `voice/assistant.py` 相同，无独立保留价值。 |
| `229_1` | 空目录 | 删除 | 否 | 无内容。 |
| `302` | 低延迟音乐分析实验 | `archive/code/spike-302-latency/` + `docs/archive/302/` | 部分 | 有明确收益的参数与局部行为可吸收，但不能整目录覆盖主线。 |
| `303` | 语音命令解析/日志实验 | `archive/code/spike-303-voice/` | 部分 | 中文时长解析有价值，但部分等待逻辑明显过重，不适合直并。 |
| `304` | 阿里云语音替换实验 | `archive/code/spike-304-aliyun/` + `docs/archive/304/` | 否 | 目前主线未确认要迁移供应商，保留实验材料即可。 |
| `__pycache__/`、`*.pyc` | 生成产物 | 删除 | 否 | 无源代码价值。 |

## 主线接口约束

- 保持 `python main.py` 为主入口。
- 保持 `RobotController.handle_voice_command(text) -> bool` 不变。
- 保持 `SpeechRecognizer.recognize(audio_data, sample_rate) -> (bool, str)` 不变。
- 保持 `TextToSpeech.speak(text) -> bool` 不变。
