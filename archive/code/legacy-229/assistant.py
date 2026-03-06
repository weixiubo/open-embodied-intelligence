"""
语音助手

集成语音识别、语音合成、AI对话和舞蹈控制。
"""

import threading
import time
import tempfile
import wave
from typing import Optional, Callable
from pathlib import Path

from config import api_config, audio_config
from utils.logger import logger
from .speech_recognition import SpeechRecognizer
from .text_to_speech import TextToSpeech

# 尝试导入 OpenAI 客户端（用于 DeepSeek）
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai 库未安装，AI 对话功能将不可用")

# 尝试导入 PyAudio
try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    np = None


class VoiceAssistant:
    """
    语音助手
    
    功能：
    - 语音录制和识别
    - AI 对话（DeepSeek）
    - 语音合成播放
    - 舞蹈控制集成
    """
    
    def __init__(
        self,
        use_tts: bool = True,
        initial_volume: int = None,
        voice_id: int = None,
    ):
        """
        初始化语音助手
        
        Args:
            use_tts: 是否启用语音合成
            initial_volume: TTS 音量
            voice_id: TTS 语音 ID
        """
        # 组件
        self.recognizer = SpeechRecognizer()
        self.tts = TextToSpeech(volume=initial_volume, voice_id=voice_id) if use_tts else None
        
        # AI 对话
        self.ai_client = None
        self.conversation_history = []
        self._init_ai_client()
        
        # 舞蹈控制器
        self.dance_handler = None
        
        # 状态
        self.is_running = False
        self.is_dance_mode = False
        self.stop_event = threading.Event()
        
        # 音频配置
        self.audio_config = audio_config.recording
        
        logger.info("语音助手初始化完成")
    
    def _init_ai_client(self) -> None:
        """初始化 AI 客户端"""
        if not OPENAI_AVAILABLE:
            return
        
        deepseek_config = api_config.deepseek
        if not deepseek_config.is_configured:
            logger.warning("DeepSeek API 未配置，AI 对话功能不可用")
            return
        
        try:
            self.ai_client = OpenAI(
                api_key=deepseek_config.api_key,
                base_url=deepseek_config.base_url,
            )
            logger.info("AI 对话功能已启用")
        except Exception as e:
            logger.error(f"初始化 AI 客户端失败: {e}")
    
    def set_dance_handler(self, handler) -> None:
        """设置舞蹈控制器"""
        self.dance_handler = handler
        logger.debug("舞蹈控制器已连接")
    
    def set_dance_mode(self, enabled: bool) -> None:
        """设置舞蹈模式（暂停/恢复语音识别）"""
        self.is_dance_mode = enabled
        logger.debug(f"舞蹈模式: {'开启' if enabled else '关闭'}")
    
    def run_voice_chat(self) -> None:
        """启动语音对话主循环"""
        if not PYAUDIO_AVAILABLE:
            logger.error("pyaudio 不可用，无法启动语音对话")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        logger.info("语音助手已启动，开始监听...")
        
        audio = pyaudio.PyAudio()
        try:
            input_info = audio.get_default_input_device_info()
            logger.info(
                "默认输入设备: "
                f"{input_info.get('name', 'unknown')} "
                f"(index={input_info.get('index')}, "
                f"maxInputChannels={input_info.get('maxInputChannels')}, "
                f"defaultSampleRate={input_info.get('defaultSampleRate')})"
            )
        except Exception:
            logger.warning("无法获取默认输入设备信息，请检查麦克风是否可用")
        
        try:
            # 打开音频流
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.audio_config.channels,
                rate=self.audio_config.sample_rate,
                input=True,
                frames_per_buffer=self.audio_config.chunk_size,
            )
            
            while self.is_running and not self.stop_event.is_set():
                # 如果在舞蹈模式，暂停语音识别
                if self.is_dance_mode:
                    time.sleep(0.5)
                    continue
                
                # 录制音频
                audio_data = self._record_audio(stream)
                
                if audio_data:
                    # 语音识别
                    success, text = self.recognizer.recognize(audio_data)
                    
                    if success and text:
                        # 处理识别结果
                        self._handle_voice_input(text)
            
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            logger.error(f"语音对话异常: {e}", exc_info=True)
        finally:
            audio.terminate()
            self.is_running = False
        
        logger.info("语音助手已停止")
    
    def _record_audio(self, stream, max_duration: float = None) -> Optional[bytes]:
        """
        录制音频（简化版，固定时长）
        
        实际项目中应使用 VAD（语音活动检测）来自动判断录音结束。
        """
        max_duration = max_duration or self.audio_config.max_recording_duration
        
        frames = []
        chunk_size = self.audio_config.chunk_size
        sample_rate = self.audio_config.sample_rate
        num_chunks = int(sample_rate / chunk_size * max_duration)
        
        # 简单的能量检测
        silence_threshold = 500
        silence_count = 0
        max_silence = int(sample_rate / chunk_size * 1.5)  # 1.5秒静音停止
        recording_started = False
        
        for _ in range(num_chunks):
            if self.stop_event.is_set():
                break
            
            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                
                # 计算能量
                audio_array = np.frombuffer(data, dtype=np.int16)
                energy = np.abs(audio_array).mean()
                
                if energy > silence_threshold:
                    recording_started = True
                    silence_count = 0
                    frames.append(data)
                elif recording_started:
                    frames.append(data)
                    silence_count += 1
                    
                    if silence_count >= max_silence:
                        break
                        
            except Exception:
                break
        
        if len(frames) < 10:  # 太短，忽略
            return None
        
        return b"".join(frames)
    
    def _handle_voice_input(self, text: str) -> None:
        """处理语音输入"""
        logger.info(f"收到语音: {text}")
        
        # 检查退出命令
        if any(cmd in text for cmd in ["退出对话", "结束对话", "再见"]):
            logger.info("收到退出命令")
            self.stop()
            return
        
        # 检查舞蹈命令
        if self.dance_handler:
            if self.dance_handler.handle_voice_command(text):
                return
        
        # AI 对话
        response = self._get_ai_response(text)
        if response:
            logger.info(f"AI 回复: {response}")
            if self.tts:
                self.tts.speak(response)
    
    def _get_ai_response(self, text: str) -> Optional[str]:
        """获取 AI 回复"""
        if not self.ai_client:
            return "AI 对话功能未启用"
        
        try:
            # 添加用户消息到历史
            self.conversation_history.append({
                "role": "user",
                "content": text,
            })
            
            # 保持历史长度
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一个智能舞蹈机器人的语音助手。请用简洁友好的方式回答问题，控制在100字以内。",
                }
            ] + self.conversation_history
            
            # 调用 API
            deepseek_config = api_config.deepseek
            response = self.ai_client.chat.completions.create(
                model=deepseek_config.model,
                messages=messages,
                temperature=deepseek_config.temperature,
                max_tokens=deepseek_config.max_tokens,
            )
            
            reply = response.choices[0].message.content
            
            # 添加到历史
            self.conversation_history.append({
                "role": "assistant",
                "content": reply,
            })
            
            return reply
            
        except Exception as e:
            logger.error(f"AI 对话失败: {e}")
            return "抱歉，我无法处理这个请求"
    
    def stop(self) -> None:
        """停止语音助手"""
        self.is_running = False
        self.stop_event.set()
        logger.info("正在停止语音助手...")
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.conversation_history.clear()
        logger.info("对话历史已清空")
