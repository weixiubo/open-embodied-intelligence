"""
API 配置模块。

管理 DeepSeek 与百度语音配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip() or default


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置。"""

    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 200
    timeout: int = 30

    def __post_init__(self) -> None:
        self.api_key = _env("DEEPSEEK_API_KEY")
        self.base_url = _env("DEEPSEEK_BASE_URL", self.base_url) or self.base_url
        self.model = _env("DEEPSEEK_MODEL", self.model) or self.model
        self.temperature = float(_env("DEEPSEEK_TEMPERATURE", str(self.temperature)))
        self.max_tokens = int(_env("DEEPSEEK_MAX_TOKENS", str(self.max_tokens)))
        self.timeout = int(_env("DEEPSEEK_TIMEOUT", str(self.timeout)))

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class BaiduSpeechConfig:
    """百度语音 API 配置。"""

    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    token_url: str = "https://aip.baidubce.com/oauth/2.0/token"
    asr_url: str = "https://vop.baidu.com/server_api"
    tts_url: str = "https://tsn.baidu.com/text2audio"
    tts_default_volume: int = 2
    tts_default_voice: int = 5
    tts_timeout: float = 60.0
    asr_timeout: int = 30
    asr_min_file_size: int = 5000

    def __post_init__(self) -> None:
        self.api_key = _env("BAIDU_API_KEY")
        self.secret_key = _env("BAIDU_SECRET_KEY")
        self.tts_default_volume = int(_env("BAIDU_TTS_VOLUME", str(self.tts_default_volume)))
        self.tts_default_voice = int(_env("BAIDU_TTS_VOICE", str(self.tts_default_voice)))
        self.tts_timeout = float(_env("BAIDU_TTS_TIMEOUT", str(self.tts_timeout)))
        self.asr_timeout = int(_env("BAIDU_ASR_TIMEOUT", str(self.asr_timeout)))
        self.asr_min_file_size = int(
            _env("BAIDU_ASR_MIN_FILE_SIZE", str(self.asr_min_file_size))
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key)


@dataclass
class APIConfig:
    """API 配置汇总。"""

    deepseek: DeepSeekConfig = None
    baidu: BaiduSpeechConfig = None

    def __post_init__(self) -> None:
        self.deepseek = DeepSeekConfig()
        self.baidu = BaiduSpeechConfig()

    def validate(self) -> tuple[bool, str]:
        if not self.deepseek.is_configured:
            return False, "缺少 DEEPSEEK_API_KEY"
        if not self.baidu.is_configured:
            return False, "缺少 BAIDU_API_KEY 或 BAIDU_SECRET_KEY"
        return True, "API 配置完整"


api_config = APIConfig()
