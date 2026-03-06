# 阿里云 NLS 测试脚本使用说明

## 目的
验证阿里云 AK/SK 凭证是否有效，测试 Token 获取和语音识别功能。

## 功能流程
1. **获取 Token** - 使用 AccessKey ID/Secret 从阿里云获取临时访问令牌
2. **生成测试音频** - 生成 1 秒的 16kHz 正弦波 PCM 数据
3. **识别音频** - 调用一句话识别 API，测试识别功能

## 运行前准备

### 1. 安装依赖
```bash
pip install aliyun-python-sdk-core requests python-dotenv
```

### 2. 配置凭证
在 `/304/` 目录创建 `.env` 文件，添加：
```dotenv
ALIYUN_ACCESS_KEY_ID=<你的 AccessKey ID>
ALIYUN_ACCESS_KEY_SECRET=<你的 AccessKey Secret>
ALIYUN_APP_KEY=your_aliyun_app_key_here
ALIYUN_REGION=cn-wuhan
```

**参数说明：**
- `ALIYUN_ACCESS_KEY_ID` - 阿里云账号的 AccessKey ID
- `ALIYUN_ACCESS_KEY_SECRET` - 对应的 Secret
- `ALIYUN_APP_KEY` - NLS 应用的 App Key
- `ALIYUN_REGION` - 部署区域（默认：cn-wuhan）

## 运行脚本

### 方式 1：自动读取 .env（推荐）
```bash
cd 304
python aliyun_nls_test.py
```

### 方式 2：命令行输入
```bash
python aliyun_nls_test.py
# 脚本会提示输入凭证
```

### 方式 3：环境变量
```bash
export ALIYUN_ACCESS_KEY_ID="<your-ak-id>"
export ALIYUN_ACCESS_KEY_SECRET="<your-ak-secret>"
export ALIYUN_APP_KEY="your_aliyun_app_key_here"
python aliyun_nls_test.py
```

## 预期输出

### 成功情况
```
============================================================
阿里云 NLS 测试脚本
============================================================

[准备] 读取阿里云凭证...
✓ ALIYUN_ACCESS_KEY_ID 已从环境/配置文件读取
✓ ALIYUN_ACCESS_KEY_SECRET 已从环境/配置文件读取
✓ ALIYUN_APP_KEY 已从环境/配置文件读取
✓ 区域设置为: cn-wuhan

[1/3] 正在获取阿里云访问令牌...
✅ Token 获取成功
   Token ID = xxxxxxxxxxxxxxxx...
   过期时间 = 2026-03-05 22:25:23

[2/3] 正在生成测试音频...
✅ 已生成 32000 字节的测试音频 (1000ms, 16000Hz, 1000Hz)

[3/3] 正在识别音频...
✅ 识别成功: "测试语音内容"

============================================================
✅ 测试通过！阿里云 NLS 服务正常使用
============================================================
```

### 失败情况

#### AccessKey 无效
```
❌ 获取 Token 失败: HTTP Status: 401 Error:InvalidAccessKeyId Specified access key is not found or invalid.
```
**解决：** 检查 `ALIYUN_ACCESS_KEY_ID` 和 `ALIYUN_ACCESS_KEY_SECRET` 是否正确

#### 免费试用已过期
```
❌ 识别失败 (status=40000010): Gateway:FREE_TRIAL_EXPIRED:The free trial has expired!
```
**解决：** 
- 需要开通阿里云 NLS 付费服务
- 或注册新账号获取试用额度

#### App Key 无效
```
❌ 识别失败 (status=40000001): ......
```
**解决：** 检查 `ALIYUN_APP_KEY` 是否正确

#### 网络错误
```
❌ 请求异常: Connection timeout
```
**解决：** 检查网络连接或阿里云服务可用性

## 输出日志说明

| 符号 | 含义 |
|------|------|
| ✅ | 操作成功 |
| ❌ | 操作失败 |
| ⚠️  | 警告/不确定 |
| ✓  | 已确认 |

## 常见问题

### Q1: 脚本找不到 .env 文件
**A:** 确保 `.env` 文件与脚本在同一目录 `/304/`

### Q2: "模块未找到" 错误
**A:** 运行 `pip install -r requirements.txt` 或逐个安装依赖

### Q3: Token 获取成功但识别失败
**可能原因：**
- App Key 无效
- 账户额度不足（FREE_TRIAL_EXPIRED）
- 该区域不支持 NLS 服务

### Q4: 如何测试本地音频文件？
修改脚本中的 `recognize_audio()` 调用，替换为：
```python
with open("test.pcm", "rb") as f:
    pcm_data = f.read()
result = recognize_audio(...)
```

## 与项目集成

测试通过后，确认以下配置已应用到项目：
1. `/大创agentV3/config/api_config.py` - 包含 `AliyunNlsConfig` 类
2. `/304/voice/speech_recognition.py` - 使用 AK/SK Token 模式
3. 项目根目录 `.env` - 包含凭证信息

## 清理
测试完成后，可以删除此脚本：
```bash
rm 304/aliyun_nls_test.py
```

