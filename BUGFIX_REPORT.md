# Bugfix Report

## 1) 输入设备枚举检测已注入
- 文件: `voice/recording.py`
- 函数: `VoiceRecorder._resolve_input_device_index`
- 变更: 在函数开头增加“可用输入设备列表”日志，打印所有 `maxInputChannels > 0` 的设备 `index/name`。

关键代码:

```python
logger.info("=== 系统可用输入设备列表 ===")
for i in range(audio.get_device_count()):
		info = audio.get_device_info_by_index(i)
		if info.get("maxInputChannels", 0) > 0:
				logger.info("[检测] Index: %d, Name: %s", i, info.get("name", ""))
logger.info("============================")
```

同时保留了既有的外接设备过滤:

```python
if "usb2.0 device" in name_lower:
		logger.debug("忽略外接输出设备: %s", name)
		continue
```

## 2) TTS 底层减音量参数与播放器结果
- 文件: `voice/text_to_speech.py`
- 函数: `_play_audio(self, file_path: Path)`
- 减音量参数:
	- `mpg123`: `-q -f 6000`
	- `mpv`: `--volume=30`
	- `ffplay`: `-volume 30`
	- `aplay`: 仅路由设备，不支持直接音量参数

为满足“最终发现哪种播放器”，已新增运行时日志:

```python
logger.info("TTS 选择播放器: %s", player)
```

说明:
- 代码按顺序检测播放器: `mpg123 -> mpv -> ffplay -> aplay`。
- 实际本机最终命中哪一个，以终端日志 `TTS 选择播放器: ...` 为准。
