"""
语音识别模块

使用阿里云一句话识别 API 进行语音转文字（AK/SK Token 模式）。
"""

import wave
import os
import json
import time
from pathlib import Path
from typing import Optional, Tuple

from config import api_config, audio_config
from utils.logger import logger

# 导入 requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests 库未安装，请运行: pip install requests")

# 导入阿里云 SDK
try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    ALIYUN_SDK_AVAILABLE = True
except ImportError:
    ALIYUN_SDK_AVAILABLE = False
    logger.warning("阿里云 SDK 未安装，请运行: pip install aliyun-python-sdk-core")



class SpeechRecognizer:
    """
    语音识别器
    
    使用阿里云一句话识别 API（AK/SK Token 模式）将音频转换为文字。
    """
    
    def __init__(self):
        """初始化语音识别器"""
        self.aliyun_config = api_config.aliyun
        self.baidu_config = api_config.baidu
        
        # 阿里云一句话识别 API 端点
        self.aliyun_api_url = "https://nls-gateway-cn-hangzhou.aliyuncs.com/stream/v1/FlashRecognizer"
        
        # Token 缓存
        self._aliyun_token: Optional[str] = None
        self._token_expires: float = 0
        
        if not self.aliyun_config.is_configured:
            logger.warning("阿里云 NLS API 未配置")
        
        if not REQUESTS_AVAILABLE:
            logger.warning("requests 库未安装，语音识别功能将不可用")
        elif not ALIYUN_SDK_AVAILABLE:
            logger.warning("阿里云 SDK 未安装，语音识别功能将不可用")
        else:
            logger.info("语音识别器初始化完成（使用阿里云一句话识别 - AK/SK Token 模式）")
    
    def _get_aliyun_token(self) -> Optional[str]:
        """获取阿里云访问令牌（使用 AK/SK）"""
        # 检查缓存的令牌是否有效
        if self._aliyun_token and time.time() < self._token_expires:
            return self._aliyun_token
        
        if not ALIYUN_SDK_AVAILABLE:
            logger.error("阿里云 SDK 未安装，无法获取 Token")
            return None
        
        try:
            # 创建 AcsClient（从配置读取 AK/SK）
            client = AcsClient(
                self.aliyun_config.access_key_id,
                self.aliyun_config.access_key_secret,
                "cn-hangzhou"
            )
            
            # 创建 Token 请求
            request = CommonRequest()
            request.set_method("POST")
            request.set_domain("nls-meta.cn-hangzhou.aliyuncs.com")
            request.set_version("2019-02-28")
            request.set_action_name("CreateToken")
            
            # 发送请求
            response = client.do_action_with_exception(request)
            
            # 解析响应
            token_data = json.loads(response)
            self._aliyun_token = token_data['Token']['Id']
            expire_time = token_data['Token']['ExpireTime']
            
            # 设置缓存过期时间（提前 1 小时过期）
            self._token_expires = expire_time - 3600
            
            logger.debug(f"获取阿里云访问令牌成功，有效期至: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expire_time))}")
            return self._aliyun_token
            
        except Exception as e:
            logger.error(f"获取阿里云令牌异常: {e}")
            return None
    
    
    def recognize(self, audio_data: bytes, sample_rate: int = None) -> Tuple[bool, str]:
        """
        识别音频数据（使用阿里云一句话识别 - AK/SK Token 模式）
        
        Args:
            audio_data: 音频数据（PCM 格式）
            sample_rate: 采样率
        
        Returns:
            (是否成功, 识别结果或错误信息)
        """
        if not REQUESTS_AVAILABLE:
            return False, "requests 库未安装"
        
        if not self.aliyun_config.is_configured:
            return False, "阿里云 NLS API 未配置"
        
        sample_rate = sample_rate or audio_config.recording.sample_rate
        
        # 检查音频大小
        if len(audio_data) < self.aliyun_config.asr_min_file_size:
            return False, "音频数据太短"
        
        # 获取访问令牌
        token = self._get_aliyun_token()
        if not token:
            return False, "获取阿里云访问令牌失败"
        
        try:
            # 构建请求参数（必须包含 token）
            params = {
                "appkey": self.aliyun_config.app_key,
                "token": token,
                "format": "pcm",
                "sample_rate": sample_rate,
            }
            
            # 发送 POST 请求（直接发送 PCM 音频数据）
            response = requests.post(
                self.aliyun_api_url,
                params=params,
                headers={
                    "Content-Type": "application/octet-stream"
                },
                data=audio_data,
                timeout=self.aliyun_config.asr_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 阿里云返回格式：{"status": 20000000, "message": "SUCCESS", "result": "识别文本"}
                status_code = result.get("status")
                if status_code == 20000000:
                    text = result.get("result", "")
                    if text:
                        logger.info(f"语音识别成功（阿里云）: {text}")
                        return True, text
                    else:
                        logger.warning("阿里云识别结果为空")
                        return False, "识别结果为空"
                else:
                    error_msg = result.get("message", "未知错误")
                    logger.warning(f"阿里云识别失败: {error_msg} (status={status_code})")
                    return False, error_msg
            else:
                # 记录详细错误信息
                error_msg = f"HTTP 错误: {response.status_code}"
                try:
                    error_detail = response.json()
                    logger.error(f"阿里云 API 调用失败: {error_msg}, 详情: {error_detail}")
                except:
                    logger.error(f"阿里云 API 调用失败: {error_msg}, 响应: {response.text[:200]}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"阿里云语音识别异常: {e}")
            return False, str(e)
    
    def recognize_file(self, file_path: str) -> Tuple[bool, str]:
        """
        识别音频文件
        
        Args:
            file_path: 音频文件路径（WAV 格式）
        
        Returns:
            (是否成功, 识别结果或错误信息)
        """
        try:
            with wave.open(file_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                audio_data = wav_file.readframes(wav_file.getnframes())
            
            return self.recognize(audio_data, sample_rate)
            
        except Exception as e:
            logger.error(f"读取音频文件失败: {e}")
            return False, str(e)