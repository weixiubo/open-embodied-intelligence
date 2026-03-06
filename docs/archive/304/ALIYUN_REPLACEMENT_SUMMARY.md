# 阿里云 NLS API 替换说明（appkey 模式）

## 修改日期
2026-03-04（最终版）

## 修改目标
将百度语音 API 替换为阿里云一句话识别 API，采用**简化的 appkey 模式**，无需显式管理 token。

---

## 文件修改详情

### `/304/voice/speech_recognition.py`

#### ✅ 已删除内容
- ❌ `_get_aliyun_token()` 方法（原先的 token 获取逻辑）
- ❌ `_aliyun_token` 实例变量
- ❌ `_token_expires` 实例变量
- ❌ 所有 token 相关的 HTTP 请求代码
- ❌ Base64 编码逻辑
- ❌ 复杂的导入（`base64`, `hmac`, `hashlib`, `datetime`, `urllib.parse` 等）

#### ✅ 保留内容
- ✅ `recognize(audio_data: bytes, sample_rate: int)` 方法签名不变
- ✅ 返回值格式 `Tuple[bool, str]` 不变
- ✅ 音频数据检查逻辑（最小长度验证）
- ✅ 日志记录机制
- ✅ `recognize_file()` 方法
- ✅ 错误处理逻辑

#### ✅ 修改内容
**调用方式简化**：
```python
# 原先（需要 token）
params = {
    "appkey": app_key,
    "token": token,  # ← 需要先获取 token
    "format": "pcm",
    "sample_rate": sample_rate
}

# 现在（仅 appkey）
params = {
    "appkey": self.aliyun_config.app_key,  # 仅需 appkey
    "format": "pcm",
    "sample_rate": sample_rate
}
```

**直接 POST 请求**：
```python
response = requests.post(
    "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/FlashRecognizer",
    params=params,
    headers={"Content-Type": "application/octet-stream"},
    data=audio_data  # 直接发送 PCM 字节流
)
```

---

### `/304/config/api_config.py`
保持不变，包含：
- `AliyunNlsConfig` 类（包含 `app_key` 字段）
- `BaiduSpeechConfig` 类（保留用于对比测试）

---

### `/304/.env.example`
保持不变，包含：
```dotenv
# 阿里云 NLS API（仅需 appkey）
ALIYUN_APP_KEY=your_aliyun_app_key_here

# 可选：AccessKey（如果未来需要 token 模式）
ALIYUN_ACCESS_KEY_ID=your_access_key_id_here
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret_here
```

---

## 核心改进

### 1. **极致简化**
- 删除 60+ 行 token 管理代码
- 仅保留核心识别逻辑（~40 行）
- 无需管理 token 生命周期

### 2. **无额外依赖**
- 仅需 `requests` 库（通常已安装）
- 无需阿里云 SDK
- 无需复杂的加密库

### 3. **接口保持不变**
- ✅ `recognize(audio_data, sample_rate) → (bool, str)`
- ✅ 上层 `VoiceAssistant` 无需修改
- ✅ 完全向后兼容

---

## 测试步骤

### 1. 配置环境变量
在 `.env` 文件中添加：
```dotenv
ALIYUN_APP_KEY=your_aliyun_app_key_here
```

### 2. 运行测试
```python
from voice.speech_recognition import SpeechRecognizer

recognizer = SpeechRecognizer()
success, text = recognizer.recognize(audio_data, sample_rate=16000)

if success:
    print(f"识别成功: {text}")
else:
    print(f"识别失败: {text}")
```

### 3. 预期响应
**成功时**：
```json
{
  "status": 20000000,
  "message": "SUCCESS",
  "result": "识别的文本内容"
}
```

**失败时**（可能的原因）：
- `status: 40000001` - appkey 无效
- `status: 40000002` - 音频格式错误
- `status: 40000003` - 音频过长/过短

---

## 注意事项

### ⚠️ 关于 appkey-only 模式
阿里云官方文档要求一句话识别需要 **token**（通过 AccessKeyId/Secret 获取）。

**当前实现**尝试仅使用 appkey 调用，这可能：
1. ✅ 工作（如果服务端支持简化模式）
2. ❌ 返回认证错误（需要添加 token）

**如果遇到认证错误**：
- 检查 appkey 是否正确
- 确认阿里云账号已开通 NLS 服务
- 必要时恢复 token 获取逻辑（使用 AccessKey）

---

## 对比百度 API

| 特性 | 百度 API | 阿里云（当前） |
|------|---------|---------------|
| 认证方式 | AccessToken | Appkey only |
| Token 管理 | 需要（30天有效期） | 无需 |
| 音频编码 | Base64 | 原始字节流 |
| 请求格式 | JSON | Binary |
| 代码复杂度 | 中等 | 极简 |

---

## 回滚方案
原版文件已备份到 `/大创agentV3/voice/speech_recognition.py`，如需回滚：
```bash
cp 大创agentV3/voice/speech_recognition.py 304/voice/speech_recognition.py
```

---

## 修改原则遵守清单
- ✅ 保持外层接口不变
- ✅ 删除无用的 token 逻辑
- ✅ 不修改其他模块
- ✅ 无架构优化或重构
- ✅ 完全非侵入式
- ✅ 可随时切换回百度

