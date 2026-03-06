"""
语音模块导出。
"""

from .assistant import VoiceAssistant
from .intents import VoiceIntent, VoiceIntentType, parse_voice_intent
from .speech_recognition import SpeechRecognizer
from .text_to_speech import TextToSpeech

__all__ = [
    "SpeechRecognizer",
    "TextToSpeech",
    "VoiceAssistant",
    "VoiceIntent",
    "VoiceIntentType",
    "parse_voice_intent",
]
