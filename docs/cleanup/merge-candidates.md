# 主线吸收清单

## 已吸收

### 来自 `302` 的低延迟音乐分析点

- `config/audio_config.py`
  - `analysis_window` 从 `2.0` 调整为 `1.2`，缩短首次分析等待。
- `core/music_analyzer.py`
  - 增加简单噪音门槛：`noise_threshold = 250`
  - 连续有效帧要求：`required_valid_frames = 2`
  - 节拍检测显式使用 `hop_length = 512`
  - 停止分析时重置 `buffer_duration` 和有效帧计数

### 来自 `303` 的语音命令解析点

- `utils/helpers.py`
  - 新增 `extract_duration_from_text()`，支持阿拉伯数字与中文数字秒数解析。
- `dance/robot_controller.py`
  - 支持 `"跳5秒"`、`"跳五秒"`、`"要二十秒"` 等时长表达
  - 支持 `"舞蹈"` 默认按 5 秒启动
  - 增加 5-60 秒范围校验

### 整理中补强的主线稳定性

- `utils/logger.py`
  - 当当前终端编码不支持 emoji 时，自动降级为纯文本日志，避免 Windows/GBK 环境下的日志编码报错。

## 明确不吸收

- `302/303` 的整文件覆盖方案
  - 原因：实验目录与主线文件形态已经分叉，直接覆盖风险高。
- `303` 的长时间音乐就绪等待与失败日志系统
  - 原因：等待窗口被拉长到 10 秒，不适合作为当前主线默认行为。
- `304` 的阿里云语音替换
  - 原因：当前主线默认继续使用百度 ASR/TTS，暂无明确迁移需求。

## 已补充测试

- 新增 `tests/test_command_parsing.py`
  - 覆盖数字秒数、中文秒数、别名触发、默认时长和越界时长。
