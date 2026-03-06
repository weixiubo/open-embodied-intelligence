"""
API 配置模块

管理所有外部 API 的配置，从环境变量安全加载密钥。
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""
    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 200
    timeout: int = 30
    
    def __post_init__(self) -> None:
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.api_key is not None and len(self.api_key) > 0


@dataclass
class BaiduSpeechConfig:
    """百度语音 API 配置"""
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    
    # API 端点
    token_url: str = "https://aip.baidubce.com/oauth/2.0/token"
    asr_url: str = "https://vop.baidu.com/server_api"
    tts_url: str = "https://tsn.baidu.com/text2audio"
    
    # TTS 设置
    tts_default_volume: int = 8  # 1-10
    tts_default_voice: int = 5  # 度小娇
    tts_timeout: float = 60.0
    
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


@dataclass
class AliyunNlsConfig:
    """阿里云 NLS API 配置"""
    access_key_id: Optional[str] = None
    access_key_secret: Optional[str] = None
    app_key: Optional[str] = None
    
    # API 端点
    region_id: str = "cn-hangzhou"
    
    # ASR 设置
    asr_timeout: int = 30
    asr_min_file_size: int = 5000  # 最小音频文件大小(bytes)
    
    def __post_init__(self) -> None:
        self.access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID")
        self.access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        self.app_key = os.getenv("ALIYUN_APP_KEY")
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return (
            self.access_key_id is not None and len(self.access_key_id) > 0 and
            self.access_key_secret is not None and len(self.access_key_secret) > 0 and
            self.app_key is not None and len(self.app_key) > 0
        )


@dataclass
class APIConfig:
    """API 配置汇总"""
    deepseek: DeepSeekConfig = None
    baidu: BaiduSpeechConfig = None
    aliyun: AliyunNlsConfig = None
    
    def __post_init__(self) -> None:
        self.deepseek = DeepSeekConfig()
        self.baidu = BaiduSpeechConfig()
        self.aliyun = AliyunNlsConfig()
    
    def validate(self) -> tuple[bool, str]:
        """验证 API 配置"""
        if not self.deepseek.is_configured:
            return False, "请在 .env 文件中设置 DEEPSEEK_API_KEY"
        
        if not self.baidu.is_configured:
            return False, "请在 .env 文件中设置 BAIDU_API_KEY 和 BAIDU_SECRET_KEY"
        
        if not self.aliyun.is_configured:
            return False, "请在 .env 文件中设置 ALIYUN_ACCESS_KEY_ID、ALIYUN_ACCESS_KEY_SECRET 和 ALIYUN_APP_KEY"
        
        return True, "API 配置正确"


# 全局 API 配置实例
api_config = APIConfig()
