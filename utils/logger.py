"""
统一日志系统

提供彩色控制台输出和标准化的日志格式。
"""

import logging
import sys
from typing import Optional
from pathlib import Path

from config.settings import settings


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

    def __init__(self, use_color: bool = True, use_emoji: bool = True):
        super().__init__()
        self.use_color = use_color
        self.use_emoji = use_emoji
    
    def format(self, record: logging.LogRecord) -> str:
        # 获取颜色和 emoji
        color = self.COLORS.get(record.levelname, "") if self.use_color else ""
        emoji = self.EMOJIS.get(record.levelname, "") if self.use_emoji else ""
        reset = self.RESET if self.use_color else ""
        
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


def _stream_supports_text(stream, text: str) -> bool:
    """检测输出流的编码是否支持指定文本。"""
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return True
    except Exception:
        return False


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = False,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    创建标准化的日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_to_file: 是否输出到文件
        log_file: 日志文件路径
    
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器（带颜色）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        ColoredFormatter(
            use_color=hasattr(sys.stdout, "isatty") and sys.stdout.isatty(),
            use_emoji=_stream_supports_text(sys.stdout, "✅"),
        )
    )
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_to_file and log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(SimpleFormatter())
        logger.addHandler(file_handler)
    
    return logger


_resolved_level = getattr(logging, settings.log_level, logging.INFO)
_log_file = settings.logs_dir / "runtime.log" if settings.log_to_file else None

# 全局日志器
logger = setup_logger(
    "dance_robot",
    level=_resolved_level,
    log_to_file=settings.log_to_file,
    log_file=_log_file,
)


# 便捷函数
def debug(msg: str, *args, **kwargs) -> None:
    """记录调试日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """记录信息日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """记录警告日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """记录错误日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """记录严重错误日志"""
    logger.critical(msg, *args, **kwargs)
