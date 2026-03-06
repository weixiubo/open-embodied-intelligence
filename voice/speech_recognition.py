"""
语音识别模块。
"""

from __future__ import annotations

import base64
import time
import wave
from dataclasses import dataclass
from typing import Optional, Tuple

import requests

from config import api_config, audio_config
from utils.logger import logger


@dataclass
class RecognitionTrace:
    text: str = ""
    error: str = ""
    elapsed_seconds: float = 0.0


class SpeechRecognizer:
    """百度语音识别封装。"""

    def __init__(self) -> None:
        self.baidu_config = api_config.baidu
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self.last_trace = RecognitionTrace()

        if not self.is_available:
            logger.warning("百度语音 API 未配置，语音识别将使用降级路径")

    @property
    def is_available(self) -> bool:
        return self.baidu_config.is_configured

    def _get_access_token(self) -> Optional[str]:
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
            response.raise_for_status()
            data = response.json()
            self._access_token = data.get("access_token")
            self._token_expires = time.time() + 29 * 24 * 3600
            return self._access_token
        except Exception as exc:
            logger.error(f"获取百度访问令牌失败: {exc}")
            return None

    def recognize(self, audio_data: bytes, sample_rate: int = None) -> Tuple[bool, str]:
        self.last_trace = RecognitionTrace()
        if not self.is_available:
            self.last_trace.error = "百度语音 API 未配置"
            return False, self.last_trace.error

        sample_rate = sample_rate or audio_config.recording.sample_rate
        if len(audio_data) < self.baidu_config.asr_min_file_size:
            self.last_trace.error = "音频数据太短"
            return False, self.last_trace.error

        token = self._get_access_token()
        if not token:
            self.last_trace.error = "获取访问令牌失败"
            return False, self.last_trace.error

        started_at = time.time()
        try:
            response = requests.post(
                self.baidu_config.asr_url,
                json={
                    "format": "pcm",
                    "rate": sample_rate,
                    "channel": 1,
                    "cuid": "dance_robot",
                    "token": token,
                    "speech": base64.b64encode(audio_data).decode("utf-8"),
                    "len": len(audio_data),
                },
                timeout=self.baidu_config.asr_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            self.last_trace.elapsed_seconds = time.time() - started_at

            if payload.get("err_no") != 0:
                error = payload.get("err_msg", "未知错误")
                self.last_trace.error = error
                logger.warning(f"语音识别失败: {error}")
                return False, error

            text = (payload.get("result") or [""])[0].strip()
            self.last_trace.text = text
            logger.info(f"语音识别成功: {text}")
            return True, text
        except Exception as exc:
            self.last_trace.error = str(exc)
            self.last_trace.elapsed_seconds = time.time() - started_at
            logger.error(f"语音识别异常: {exc}")
            return False, str(exc)

    def recognize_file(self, file_path: str) -> Tuple[bool, str]:
        try:
            with wave.open(file_path, "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                audio_data = wav_file.readframes(wav_file.getnframes())
            return self.recognize(audio_data, sample_rate)
        except Exception as exc:
            logger.error(f"读取音频文件失败: {exc}")
            return False, str(exc)
