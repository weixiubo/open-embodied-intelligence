"""
语音合成模块。
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

from config import api_config
from utils.logger import logger


class TextToSpeech:
    """百度语音合成封装。"""

    VOICES = {
        0: "度小美",
        1: "度小宇",
        3: "度逍遥",
        4: "度丫丫",
        5: "度小娇",
    }

    def __init__(self, volume: int = None, voice_id: int = None):
        self.baidu_config = api_config.baidu
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self.volume = volume or self.baidu_config.tts_default_volume
        self.voice_id = voice_id or self.baidu_config.tts_default_voice

    @property
    def is_available(self) -> bool:
        return self.baidu_config.is_configured

    def _get_access_token(self) -> Optional[str]:
        import time as _time

        if self._access_token and _time.time() < self._token_expires:
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
            self._access_token = response.json().get("access_token")
            self._token_expires = _time.time() + 29 * 24 * 3600
            return self._access_token
        except Exception as exc:
            logger.error(f"获取 TTS 访问令牌失败: {exc}")
            return None

    def synthesize(self, text: str) -> Optional[bytes]:
        if not self.is_available:
            return None
        if not text:
            return None

        token = self._get_access_token()
        if not token:
            return None

        try:
            response = requests.post(
                self.baidu_config.tts_url,
                params={
                    "tex": text[:2048],
                    "tok": token,
                    "cuid": "dance_robot",
                    "ctp": 1,
                    "lan": "zh",
                    "spd": 5,
                    "pit": 5,
                    "vol": self.volume,
                    "per": self.voice_id,
                    "aue": 3,
                },
                timeout=self.baidu_config.tts_timeout,
            )
            if "audio" in response.headers.get("Content-Type", ""):
                return response.content
            logger.warning(f"语音合成失败: {response.text}")
            return None
        except Exception as exc:
            logger.error(f"语音合成异常: {exc}")
            return None

    def speak(self, text: str) -> bool:
        payload = self.synthesize(text)
        if not payload:
            logger.info(f"TTS 降级输出: {text}")
            return False

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
                handle.write(payload)
                temp_file = Path(handle.name)
            self._play_audio(temp_file)
            temp_file.unlink(missing_ok=True)
            return True
        except Exception as exc:
            logger.error(f"播放语音失败: {exc}")
            return False

    def _resolve_output_device(self) -> Optional[str]:
        """优先用名称关键字自动查找 ALSA hw 地址，回退到 AUDIO_OUTPUT_DEVICE 固定值。"""
        import os as _os
        import subprocess as _sp
        name_keyword = _os.getenv("AUDIO_OUTPUT_DEVICE_NAME")
        if name_keyword:
            try:
                result = _sp.run(["aplay", "-l"], capture_output=True, text=True, check=False)
                for line in result.stdout.splitlines():
                    if name_keyword.lower() in line.lower() and line.startswith("card"):
                        parts = line.split(":")
                        card_num = parts[0].replace("card", "").strip()
                        dev_num = parts[1].strip().split()[1].rstrip(",")
                        hw_addr = f"hw:{card_num},{dev_num}"
                        logger.info("按名称匹配到输出设备: %s -> %s", name_keyword, hw_addr)
                        return hw_addr
                logger.warning("未找到名称含 '%s' 的输出设备，回退到 AUDIO_OUTPUT_DEVICE", name_keyword)
            except Exception as exc:
                logger.warning("自动查找输出设备失败: %s", exc)
        return _os.getenv("AUDIO_OUTPUT_DEVICE")

    def _play_audio(self, file_path: Path) -> None:
        system = platform.system()
        if system == "Linux":
            out_dev = self._resolve_output_device()
            for player in ("mpg123", "mpv", "ffplay", "aplay"):
                if not shutil.which(player):
                    continue
                command = [player, str(file_path)]
                if player == "mpg123":
                    command.insert(1, "-q")
                    if out_dev:
                        command[1:1] = ["-a", out_dev]
                elif player == "ffplay":
                    command[1:1] = ["-nodisp", "-autoexit", "-loglevel", "quiet"]
                elif player == "aplay":
                    if out_dev:
                        command[1:1] = ["-D", out_dev]
                subprocess.run(command, capture_output=True, check=False)
                return
            raise RuntimeError("未找到可用播放器")

        if system == "Windows":
            import os

            os.startfile(str(file_path))
            time.sleep(1.5)
            return

        subprocess.run(["afplay", str(file_path)], capture_output=True, check=False)
