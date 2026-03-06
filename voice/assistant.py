"""
语音助手主流程。
"""

from __future__ import annotations

import threading
import time

from config import DemoProfileConfig, RuntimeProfile, api_config
from utils.logger import logger

from .intents import VoiceIntentType, parse_voice_intent
from .recording import VoiceRecorder
from .speech_recognition import SpeechRecognizer
from .text_to_speech import TextToSpeech

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


class VoiceAssistant:
    """统一语音交互入口。"""

    def __init__(
        self,
        runtime_config: DemoProfileConfig,
        use_tts: bool = True,
        initial_volume: int = None,
        voice_id: int = None,
    ) -> None:
        self.runtime_config = runtime_config
        self.recorder = VoiceRecorder()
        self.recognizer = SpeechRecognizer()
        self.tts = TextToSpeech(volume=initial_volume, voice_id=voice_id) if use_tts else None
        self.ai_client = None
        self.conversation_history = []
        self.dance_handler = None
        self.is_running = False
        self.is_dance_mode = False
        self.stop_event = threading.Event()

        self._init_ai_client()
        logger.info("语音助手初始化完成")

    def _init_ai_client(self) -> None:
        if not OPENAI_AVAILABLE or not api_config.deepseek.is_configured:
            logger.warning("DeepSeek 不可用，将使用脚本化回复")
            return
        try:
            self.ai_client = OpenAI(
                api_key=api_config.deepseek.api_key,
                base_url=api_config.deepseek.base_url,
            )
        except Exception as exc:
            logger.error(f"初始化 AI 客户端失败: {exc}")
            self.ai_client = None

    def set_dance_handler(self, handler) -> None:
        self.dance_handler = handler

    def set_dance_mode(self, enabled: bool) -> None:
        self.is_dance_mode = enabled
        if enabled:
            self.recorder.pause()
        else:
            self.recorder.resume()
        logger.info("舞蹈模式切换: %s", "on" if enabled else "off")

    def speak_feedback(self, text: str) -> None:
        if not text:
            return
        logger.info(f"系统反馈: {text}")
        if self.tts and self.tts.speak(text):
            return
        print(text)

    def process_text(self, text: str) -> None:
        if not text:
            return

        top_level_intent = parse_voice_intent(text)
        logger.info(
            "语音流水线: original=%s normalized=%s top_level=%s",
            text,
            top_level_intent.normalized_text,
            top_level_intent.kind.value,
        )

        if top_level_intent.kind == VoiceIntentType.EXIT:
            self.speak_feedback("正在退出语音助手。")
            self.stop()
            return

        if self.dance_handler and self.dance_handler.handle_voice_command(text):
            feedback = self.dance_handler.pop_feedback_message()
            if feedback:
                self.speak_feedback(feedback)
            return

        response = self._get_ai_response(text)
        self.speak_feedback(response)

    def _get_ai_response(self, text: str) -> str:
        if not self.ai_client:
            return "我现在优先负责跳舞演示，你可以直接说跳舞命令。"

        try:
            self.conversation_history.append({"role": "user", "content": text})
            self.conversation_history = self.conversation_history[-10:]
            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是智能舞蹈机器人的现场演示语音助手。"
                        "回答要简洁、稳定、友好，控制在 80 字以内。"
                    ),
                }
            ] + self.conversation_history
            response = self.ai_client.chat.completions.create(
                model=api_config.deepseek.model,
                messages=messages,
                temperature=api_config.deepseek.temperature,
                max_tokens=api_config.deepseek.max_tokens,
            )
            reply = response.choices[0].message.content.strip()
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as exc:
            logger.error(f"AI 对话失败: {exc}")
            return "AI 对话暂时不可用，你可以继续下达跳舞命令。"

    def run_voice_chat(self) -> None:
        if not self.recorder.is_available:
            logger.error("pyaudio 不可用，无法启动语音对话")
            self._run_text_fallback_loop()
            return

        self.is_running = True
        self.stop_event.clear()
        self.speak_feedback(self.runtime_config.startup_greeting)

        while self.is_running and not self.stop_event.is_set():
            if self.is_dance_mode:
                time.sleep(0.2)
                continue

            recorded = self.recorder.record(self.runtime_config.recording_mode)
            if not recorded:
                continue

            success, text = self.recognizer.recognize(
                recorded.payload,
                recorded.sample_rate,
            )
            if not success or not text:
                logger.warning("语音识别未得到有效文本: %s", self.recognizer.last_trace.error)
                if self.runtime_config.profile == RuntimeProfile.DEMO:
                    self.speak_feedback("我没有听清楚，请再说一遍。")
                continue

            self.process_text(text)

        logger.info("语音助手已停止")

    def stop(self) -> None:
        self.is_running = False
        self.stop_event.set()

    def clear_history(self) -> None:
        self.conversation_history.clear()

    def _run_text_fallback_loop(self) -> None:
        logger.warning("进入文本回退模式，可直接输入命令。")
        self.is_running = True
        while self.is_running and not self.stop_event.is_set():
            try:
                text = input("text> ").strip()
            except EOFError:
                break
            if not text:
                continue
            self.process_text(text)
