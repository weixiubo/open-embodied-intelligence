# 百度 token 获取逻辑分析报告

---

## 1. 涉及文件列表

| 文件路径 | 涉及 token 的内容 |
|---|---|
| `大创agentV3/voice/speech_recognition.py` | `_get_access_token()` 方法，ASR 调用前获取并缓存 token |
| `大创agentV3/voice/text_to_speech.py` | `_get_access_token()` 方法，TTS 调用前获取并缓存 token（与 ASR 完全独立的一份副本） |
| `大创agentV3/config/api_config.py` | `BaiduSpeechConfig` 数据类，持有 `token_url`、`api_key`、`secret_key` 字段 |
| `大创agentV3/.env.example` | 声明环境变量 `BAIDU_API_KEY`、`BAIDU_SECRET_KEY` |

---

## 2. token 获取函数及流程

### 2.1 `speech_recognition.py` — `SpeechRecognizer._get_access_token()`

**完整代码片段：**

```python
def _get_access_token(self) -> Optional[str]:
    """获取百度 API 访问令牌"""
    import time

    # 检查缓存的令牌是否有效
    if self._access_token and time.time() < self._token_expires:
        return self._access_token

    try:
        response = requests.post(
            self.baidu_config.token_url,          # https://aip.baidubce.com/oauth/2.0/token
            params={
                "grant_type": "client_credentials",
                "client_id": self.baidu_config.api_key,        # 来自 BAIDU_API_KEY
                "client_secret": self.baidu_config.secret_key, # 来自 BAIDU_SECRET_KEY
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            self._access_token = data.get("access_token")
            # 令牌有效期通常是 30 天，这里设置为 29 天
            self._token_expires = time.time() + 29 * 24 * 3600
            logger.debug("获取百度访问令牌成功")
            return self._access_token
        else:
            logger.error(f"获取访问令牌失败: {response.text}")
            return None

    except Exception as e:
        logger.error(f"获取访问令牌异常: {e}")
        return None
```

**流程说明：**

| 步骤 | 内容 |
|---|---|
| **请求 URL** | `https://aip.baidubce.com/oauth/2.0/token` |
| **HTTP 方法** | `POST` |
| **请求参数（Query String）** | `grant_type=client_credentials`、`client_id=<BAIDU_API_KEY>`、`client_secret=<BAIDU_SECRET_KEY>` |
| **返回数据解析** | `response.json()` 取 `data["access_token"]` 字段 |
| **缓存逻辑** | 实例变量 `_access_token`（str）和 `_token_expires`（float，Unix 时间戳），有效期硬编码为 **29 天**；下次调用时先比较 `time.time() < _token_expires`，命中则直接返回缓存值，不再发起网络请求 |
| **失败处理** | HTTP 非 200 或抛异常时均返回 `None`，调用方据此判断是否终止识别 |

---

### 2.2 `text_to_speech.py` — `TextToSpeech._get_access_token()`

**完整代码片段（与 ASR 独立，逻辑完全相同）：**

```python
def _get_access_token(self) -> Optional[str]:
    """获取百度 API 访问令牌"""
    import time

    if self._access_token and time.time() < self._token_expires:
        return self._access_token

    try:
        response = requests.post(
            self.baidu_config.token_url,
            params={
                "grant_type": "client_credentials",
                "client_id": self.baidu_config.api_key,
                "client_secret": self.baidu_config.secret_key,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            self._access_token = data.get("access_token")
            self._token_expires = time.time() + 29 * 24 * 3600
            return self._access_token

        return None

    except Exception as e:
        logger.error(f"获取访问令牌异常: {e}")
        return None
```

> **注意**：`SpeechRecognizer` 和 `TextToSpeech` 各自持有独立的 `_access_token` 和 `_token_expires` 实例变量，因此同一个 API Key 对同一个 token 服务会发起两次独立的 token 请求+缓存，两者互不共享。

---

### 2.3 `api_config.py` — `BaiduSpeechConfig` 配置类

**token 相关字段：**

```python
@dataclass
class BaiduSpeechConfig:
    """百度语音 API 配置"""
    api_key: Optional[str] = None
    secret_key: Optional[str] = None

    # API 端点
    token_url: str = "https://aip.baidubce.com/oauth/2.0/token"
    asr_url:   str = "https://vop.baidu.com/server_api"
    tts_url:   str = "https://tsn.baidu.com/text2audio"

    # ASR 设置
    asr_timeout: int = 30
    asr_min_file_size: int = 5000  # 最小音频文件大小(bytes)

    def __post_init__(self) -> None:
        self.api_key = os.getenv("BAIDU_API_KEY")
        self.secret_key = os.getenv("BAIDU_SECRET_KEY")

    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return (
            self.api_key is not None and len(self.api_key) > 0 and
            self.secret_key is not None and len(self.secret_key) > 0
        )
```

`token_url` 硬编码在类字段默认值中，不从环境变量读取。

---

## 3. 环境变量情况

### 3.1 .env.example 声明的变量

```dotenv
# 百度语音 API（用于语音识别和合成）
BAIDU_API_KEY=your_baidu_api_key_here
BAIDU_SECRET_KEY=your_baidu_secret_key_here
```

| 变量名 | 对应字段 | 说明 |
|---|---|---|
| `BAIDU_API_KEY` | `BaiduSpeechConfig.api_key` | 百度 AI 开放平台的 API Key，用作 `client_id` |
| `BAIDU_SECRET_KEY` | `BaiduSpeechConfig.secret_key` | 百度 AI 开放平台的 Secret Key，用作 `client_secret` |

> 无 `BAIDU_APP_ID`；`ACCESS_TOKEN` 不写入 .env，运行时动态获取后仅存于内存。

### 3.2 引用链路

```
.env 文件
  └─ os.getenv("BAIDU_API_KEY")
  └─ os.getenv("BAIDU_SECRET_KEY")
        ↓ 读取于
  config/api_config.py  BaiduSpeechConfig.__post_init__()
        ↓ 实例化为
  api_config.baidu  （全局单例）
        ↓ 被引用于
  ├─ voice/speech_recognition.py  →  self.baidu_config = api_config.baidu
  │      → _get_access_token() 使用 self.baidu_config.api_key / secret_key
  │      → recognize() 使用 self.baidu_config.asr_url / asr_timeout
  │
  └─ voice/text_to_speech.py      →  self.baidu_config = api_config.baidu
         → _get_access_token() 使用 self.baidu_config.api_key / secret_key
         → synthesize() 使用 self.baidu_config.tts_url / tts_timeout
```

---

## 4. 调用链分析

```
[麦克风硬件]
      │
      │  PyAudio 采集 PCM（paInt16, 16000Hz, 单声道, chunk=1024）
      ▼
[voice/assistant.py]  VoiceAssistant.run_voice_chat()
      │
      │  调用 self._record_audio(stream)
      ▼
[voice/assistant.py]  VoiceAssistant._record_audio()
      │  ┌─ 简单能量 VAD：np.abs(audio_array).mean() > 500
      │  ├─ 帧积累（frames.append(data)）
      │  └─ 静音超过 1.5s 或达到最大时长则停止
      │  返回：bytes（原始 PCM 数据）
      ▼
[voice/assistant.py]  run_voice_chat() 继续
      │  调用 self.recognizer.recognize(audio_data)
      ▼
[voice/speech_recognition.py]  SpeechRecognizer.recognize(audio_data)
      │
      ├─── 步骤1：检查音频长度 ≥ 5000 bytes，否则返回失败
      │
      ├─── 步骤2：调用 self._get_access_token()
      │           ┌─ 缓存命中？→ 直接返回 _access_token
      │           └─ 缓存未命中：
      │               POST https://aip.baidubce.com/oauth/2.0/token
      │               参数: grant_type=client_credentials
      │                     client_id=BAIDU_API_KEY
      │                     client_secret=BAIDU_SECRET_KEY
      │               解析: data["access_token"]
      │               缓存: _access_token, _token_expires = now + 29d
      │
      ├─── 步骤3：Base64 编码 audio_data
      │           audio_base64 = base64.b64encode(audio_data).decode("utf-8")
      │
      ├─── 步骤4：POST https://vop.baidu.com/server_api
      │           JSON Body:
      │             format   = "pcm"
      │             rate     = 16000
      │             channel  = 1
      │             cuid     = "dance_robot"
      │             token    = <access_token>
      │             speech   = <audio_base64>
      │             len      = len(audio_data)
      │           timeout: 30s
      │
      └─── 步骤5：解析响应
                  result["err_no"] == 0  → 成功
                  text = result["result"][0]
                  返回: Tuple[bool, str]
      ▼
[voice/assistant.py]  VoiceAssistant._handle_voice_input(text)
      │
      ├─ "退出"/"再见" → self.stop()
      │
      ├─ 舞蹈命令 → self.dance_handler.handle_voice_command(text)
      │                   ↓
      │             [dance/robot_controller.py]
      │             extract_duration_from_text(text) → duration
      │             self.start_dance(duration)
      │
      └─ 普通对话 → self._get_ai_response(text)
                        ↓
                  [DeepSeek API] → reply
                        ↓
                  self.tts.speak(reply)
                        ↓
                  [voice/text_to_speech.py]
                  同样调用 _get_access_token()（独立缓存）
                  POST https://tsn.baidu.com/text2audio → MP3 → 播放
```

---

## 5. 替换为阿里云 SDK 的影响评估

### 5.1 token / 认证机制（高影响）

| 对比项 | 百度现有实现 | 阿里云智能语音 SDK |
|---|---|---|
| 认证方式 | OAuth2 `client_credentials`，HTTP POST 换取 `access_token` | 使用 `AccessKeyId` + `AccessKeySecret`（或 RAM STS Token），由 SDK 内部签名，**无需手动获取 token** |
| token 缓存 | 代码内手写 29 天内存缓存 | SDK 自动管理，开发者无需关心 |
| 初始化凭证 | `api_key` + `secret_key` → POST → `access_token` | 直接传入 `AccessKeyId` 和 `AccessKeySecret` 初始化 `NlsClient` |

**影响：**
- `_get_access_token()` 方法在**两个文件中均可完整删除**（`speech_recognition.py` 和 `text_to_speech.py`）
- `_access_token`、`_token_expires` 两个实例变量可随之删除
- `api_config.py` 中的 `token_url` 字段可删除，`api_key`/`secret_key` 需替换为 `access_key_id`/`access_key_secret`

---

### 5.2 通信协议（高影响）

| 对比项 | 百度现有实现 | 阿里云 NLS SDK |
|---|---|---|
| 协议 | HTTP REST，同步阻塞 POST | **WebSocket 长连接**（SDK 封装），实时流式传输 |
| 调用范式 | `requests.post(...)` 一次性发送 | 创建 `SpeechRecognizer` 对象，调用 `start()`→`send_audio()`→`stop()`，通过回调获取结果 |
| 并发模型 | 同步阻塞 | 事件驱动（回调函数：`on_sentence_end`、`on_result_changed` 等） |

**影响：**
- `recognize()` 方法整体需重写，从同步 POST 改为 SDK 异步回调模式
- `assistant.py` 中 `success, text = self.recognizer.recognize(audio_data)` 的同步调用方式需改造（可用线程 `Event` 等待回调结果，保持外层接口不变）

---

### 5.3 音频传输方式（中影响）

| 对比项 | 百度现有实现 | 阿里云 NLS SDK |
|---|---|---|
| 编码方式 | PCM 数据 → Base64 字符串 → JSON body | 原始 PCM 二进制直接传入 `send_audio(bytes)` |
| 发送时机 | 录音完成后一次性发送 | 可边录边发（流式），也可录完后一次性 `send_audio` |

**影响：**
- `base64.b64encode(audio_data)` 编码逻辑可直接删除
- 阿里云 SDK 的 `send_audio()` 直接接收 `bytes`，与 `_record_audio()` 返回值类型兼容，**音频采集层（`audio_config.py`、采样率 16000Hz）无需修改**

---

### 5.4 请求参数结构（中影响）

| 百度 JSON 参数 | 阿里云 SDK 对应处理方式 |
|---|---|
| `"format": "pcm"` | 初始化时配置 `set_format("pcm")`（或 SDK 默认） |
| `"rate": 16000` | 初始化时配置 `set_sample_rate(16000)` |
| `"channel": 1` | SDK 默认单声道，通常无需显式设置 |
| `"cuid": "dance_robot"` | 无对应字段，可省略 |
| `"token": token` | 不存在，认证已在 SDK 初始化时完成 |
| `"speech": base64_str` | 替换为 `recognizer.send_audio(pcm_bytes)` |
| `"len": int` | 不需要，SDK 自行处理数据长度 |

---

### 5.5 返回数据结构解析（中影响）

| 对比项 | 百度现有实现 | 阿里云 NLS SDK |
|---|---|---|
| 获取方式 | `response.json()["result"][0]` | 通过回调 `on_sentence_end(message)` 接收 JSON，取 `payload["result"]` |
| 成功判断 | `result["err_no"] == 0` | 回调参数中取 `header["status"] == 20000000`（或直接判断回调类型） |
| 中间结果 | 无（仅最终结果） | 有（`on_result_changed` 回调提供中间识别文本） |

**影响：**
- `speech_recognition.py` 中 `err_no`、`err_msg`、`result[0]` 的解析逻辑需完全替换
- 可选：利用中间结果回调实现更低延迟的交互体验

---

### 5.6 配置与环境变量（低影响）

| 当前变量 | 替换为 |
|---|---|
| `BAIDU_API_KEY` | `ALIYUN_ACCESS_KEY_ID` |
| `BAIDU_SECRET_KEY` | `ALIYUN_ACCESS_KEY_SECRET` |
| —— | `ALIYUN_APP_KEY`（阿里云 NLS 项目的 AppKey） |

`.env.example` 新增 3 个变量，删除 2 个百度变量。`audio_config.py` 中的 16000Hz 采样率与阿里云 NLS 兼容，**无需修改**。

---

### 5.7 影响范围汇总

```
需完整重写（核心）：
  voice/speech_recognition.py
    - 删除 _get_access_token()、_access_token、_token_expires
    - 删除 base64 编码逻辑
    - 将 requests.post() 替换为阿里云 NlsClient + SpeechRecognizer 回调模式
    - 替换返回数据解析逻辑

需部分修改：
  config/api_config.py
    - BaiduSpeechConfig 替换为阿里云配置类
    - 删除 token_url 字段
    - api_key/secret_key → access_key_id/access_key_secret + app_key
  voice/assistant.py
    - recognize() 调用方式保持同步接口（可用 threading.Event 封装回调），
      若 recognizer 接口签名不变则此文件改动最小

需修改配置：
  .env.example / .env
    - 替换 BAIDU_API_KEY → ALIYUN_ACCESS_KEY_ID
    - 替换 BAIDU_SECRET_KEY → ALIYUN_ACCESS_KEY_SECRET
    - 新增 ALIYUN_APP_KEY

无需修改：
  config/audio_config.py      （16000Hz 与阿里云 NLS 兼容）
  voice/text_to_speech.py     （TTS 独立模块，与 ASR 替换无关）
  dance/robot_controller.py   （仅接收识别后的文字字符串，不感知底层 ASR 实现）
  utils/                      （工具模块不涉及语音 API）
  main.py                     （入口逻辑不受影响）
```

---

## 附：关键缓存变量速查

| 变量名 | 所在类 | 所在文件 | 作用 |
|---|---|---|---|
| `_access_token` | `SpeechRecognizer` | `speech_recognition.py` | 缓存 ASR 用 token 字符串 |
| `_token_expires` | `SpeechRecognizer` | `speech_recognition.py` | 缓存 ASR token 的过期时间戳（Unix float） |
| `_access_token` | `TextToSpeech` | `text_to_speech.py` | 缓存 TTS 用 token 字符串（独立副本） |
| `_token_expires` | `TextToSpeech` | `text_to_speech.py` | 缓存 TTS token 的过期时间戳（独立副本） |
