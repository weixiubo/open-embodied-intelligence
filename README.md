# 智能舞蹈机器人 V5 / OpenEI Platform Line

`main` 分支仍然服务于比赛稳定线。

`openei-next` 分支开始承载 OpenEI Phase 1 平台化工作：

- `src/openei/`：新的具身智能 runtime 内核
- `docs/openei/`：平台架构与扩展文档
- `examples/dance_demo/`：基于 OpenEI runtime 的替代示例应用

OpenEI 当前定位为：

`OpenEI = 面向机器人身体的 OpenClaw 级开源底座`

这是当前唯一继续演进的主线工程，目标是交付一版适合现场演示的机器人控制系统。

## 这版做了什么

- 单一项目根目录，保留历史代码归档但不再并列开发
- `demo/dev` 运行配置
- `auto/real/sim` 传输模式
- 统一的语音流水线：录音 -> ASR -> 意图解析 -> 风险确认 -> 执行 -> TTS/降级反馈
- 真实音乐分析失败时自动切到演示节拍源
- 启动自检和一键演示脚本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入 API 密钥和串口配置。

### 3. 启动

Linux/Orange Pi 推荐：

```bash
bash scripts/run_demo.sh
```

Windows 本地排练：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_demo.ps1
```

手动启动：

```bash
python main.py --profile demo --transport auto --recording-mode smart_vad
```

## 运行模式

- `--profile demo`：默认演示模式，启用启动自检、状态面板和命令确认
- `--profile dev`：开发模式，保留调试便利性
- `--transport auto`：优先连真机，失败自动切模拟
- `--transport real`：强制真机
- `--transport sim`：强制模拟
- `--recording-mode smart_vad`：默认智能录音

## 常用口令

- `跳舞10秒`
- `跳五秒`
- `停止跳舞`
- `动作列表`
- `机器人状态`
- `再见`

## 目录说明

- `config/`：运行配置、音频/串口参数、运行档位
- `core/`：节拍跟踪、音乐分析、编舞
- `dance/`：动作库、机器人控制器、串口驱动
- `voice/`：录音、ASR/TTS、意图解析、语音助手
- `tests/`：单元测试和回归测试
- `docs/`：演示文档和历史整理说明
- `archive/`：历史代码快照

## 演示建议

- 先用 `--transport sim` 跑一遍完整流程
- 再切 `--transport auto` 检查串口是否被识别
- 现场网络不稳时，AI 对话会自动降级为固定提示，不影响主流程
- 现场如果音乐输入不稳定，系统会切到演示节拍源，不会直接中断整场跳舞
