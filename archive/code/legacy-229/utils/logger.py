"""
统一日志系统

提供彩色控制台输出和标准化的日志格式。
增加自动失败日志保存功能。
"""

import logging
import sys
import time
from typing import Optional
from pathlib import Path
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"
    
    # 日志级别对应的 emoji
    EMOJIS = {
        "DEBUG": "🔍",
        "INFO": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取颜色和 emoji
        color = self.COLORS.get(record.levelname, "")
        emoji = self.EMOJIS.get(record.levelname, "")
        reset = self.RESET
        
        # 格式化时间（简短格式）
        time_str = self.formatTime(record, "%H:%M:%S")
        
        # 构建日志消息
        message = f"{color}{emoji} [{time_str}] [{record.name}] {record.getMessage()}{reset}"
        
        # 如果有异常信息，添加到消息中
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


class SimpleFormatter(logging.Formatter):
    """简单日志格式化器（用于文件输出）"""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


class FailureLogHandler:
    """失败日志管理器 - 自动保存失败信息到文件"""
    
    def __init__(self, log_dir: Path = None):
        """
        初始化失败日志处理器
        
        Args:
            log_dir: 日志目录路径（默认为 "./logs"）
        """
        if log_dir is None:
            # 查找项目根目录下的logs文件夹
            current = Path.cwd()
            # 优先在大创agentV5\229\logs 或 大创agentV3\logs 寻找
            if (current / "logs").exists():
                log_dir = current / "logs"
            else:
                log_dir = Path(__file__).parent.parent.parent / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志缓冲区
        self.log_buffer = []
        self.failure_reasons = []
    
    def add_log(self, level: str, message: str) -> None:
        """添加日志到缓冲区"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_buffer.append(f"[{timestamp}] [{level}] {message}")
        
        # 如果是警告或错误，记录失败原因
        if level in ["WARNING", "ERROR"]:
            self.failure_reasons.append(message)
    
    def save_failure_log(self, primary_reason: str = None) -> None:
        """
        保存失败日志到文件
        
        Args:
            primary_reason: 主要失败原因（如果为None，使用最后记录的警告/错误）
        """
        if not self.log_buffer:
            return
        
        # 确定失败原因
        reason = primary_reason or self.failure_reasons[-1] if self.failure_reasons else "未知原因"
        
        # 清理文件名中的非法字符
        safe_reason = reason.replace(" ", "_").replace(":", "").replace(".", "")[:50]
        
        # 生成文件名：HHMMSS_失败原因.txt
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_{safe_reason}.txt"
        log_file = self.log_dir / filename
        
        # 写入日志
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                # 写入头部
                f.write("=" * 80 + "\n")
                f.write(f"失败诊断报告\n")
                f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"主要失败原因: {reason}\n")
                f.write("=" * 80 + "\n\n")
                
                # 写入日志缓冲区
                f.write("完整日志:\n")
                f.write("-" * 80 + "\n")
                for log_entry in self.log_buffer:
                    f.write(log_entry + "\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("诊断建议:\n")
                f.write("-" * 80 + "\n")
                f.write(self._generate_diagnostic_suggestions(reason))
            
            print(f"\n📋 失败日志已保存: {log_file}")
        except Exception as e:
            print(f"❌ 保存失败日志失败: {e}")
    
    def _generate_diagnostic_suggestions(self, reason: str) -> str:
        """根据失败原因生成诊断建议"""
        suggestions = []
        
        if "音乐" in reason and "未检测" in reason:
            suggestions.extend([
                "1. 检查麦克风是否正常工作:",
                "   - 使用 arecord -l 列出音频设备",
                "   - 使用 arecord -d 5 test.wav 录制5秒音频",
                "   - 使用 aplay test.wav 播放测试音频",
                "",
                "2. 检查音量是否足够:",
                "   - 确认环境音乐音量 > 麦克风的静音阈值（当前: 35.0）",
                "   - 尝试更靠近麦克风播放音乐",
                "",
                "3. 检查音频采样率是否匹配:",
                "   - 麦克风采样率: 22050 Hz",
                "   - 系统采样率应与之一致",
                "",
                "4. 检查librosa是否正确安装:",
                "   - 运行: python -c 'import librosa; print(librosa.__version__)'",
            ])
        elif "无法识别" in reason or "语音识别" in reason:
            suggestions.extend([
                "1. 检查语音识别API配置:",
                "   - 确认 .env 文件中的 BAIDU_API_KEY 和 BAIDU_SECRET_KEY 正确",
                "",
                "2. 检查网络连接:",
                "   - 确认能够访问百度语音API服务",
                "",
                "3. 检查录音输入:",
                "   - 确认麦克风正常功能",
                "   - 增加说话音量",
            ])
        else:
            suggestions.extend([
                "1. 查看完整日志找出错误堆栈信息",
                "2. 检查所有必要的依赖库是否已安装",
                "3. 确认配置文件格式正确",
            ])
        
        return "\n".join(suggestions) + "\n"
    
    def clear(self) -> None:
        """清空缓冲区"""
        self.log_buffer.clear()
        self.failure_reasons.clear()


# 全局失败日志处理器
_failure_logger: Optional[FailureLogHandler] = None


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_file: Optional[Path] = None,
    enable_failure_log: bool = True,
) -> logging.Logger:
    """
    创建标准化的日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_to_file: 是否输出到文件
        log_file: 日志文件路径
        enable_failure_log: 是否启用失败日志自动保存
    
    Returns:
        配置好的日志器
    """
    global _failure_logger
    
    # 初始化失败日志处理器
    if enable_failure_log and _failure_logger is None:
        _failure_logger = FailureLogHandler()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_to_file and log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(SimpleFormatter())
        logger.addHandler(file_handler)
    
    return logger


# 全局日志器
logger = setup_logger("dance_robot", level=logging.INFO, enable_failure_log=True)


# 便捷函数
def debug(msg: str, *args, **kwargs) -> None:
    """记录调试日志"""
    logger.debug(msg, *args, **kwargs)
    if _failure_logger:
        _failure_logger.add_log("DEBUG", msg)


def info(msg: str, *args, **kwargs) -> None:
    """记录信息日志"""
    logger.info(msg, *args, **kwargs)
    if _failure_logger:
        _failure_logger.add_log("INFO", msg)


def warning(msg: str, *args, **kwargs) -> None:
    """记录警告日志"""
    logger.warning(msg, *args, **kwargs)
    if _failure_logger:
        _failure_logger.add_log("WARNING", msg)


def error(msg: str, *args, **kwargs) -> None:
    """记录错误日志"""
    logger.error(msg, *args, **kwargs)
    if _failure_logger:
        _failure_logger.add_log("ERROR", msg)


def critical(msg: str, *args, **kwargs) -> None:
    """记录严重错误日志"""
    logger.critical(msg, *args, **kwargs)
    if _failure_logger:
        _failure_logger.add_log("CRITICAL", msg)


def save_failure_log(reason: str = None) -> None:
    """保存失败日志到文件"""
    global _failure_logger
    if _failure_logger:
        _failure_logger.save_failure_log(reason)


def clear_log_buffer() -> None:
    """清空日志缓冲区"""
    global _failure_logger
    if _failure_logger:
        _failure_logger.clear()
