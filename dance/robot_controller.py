"""
机器人控制器。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

from config import (
    DemoProfileConfig,
    RecordingMode,
    RuntimeProfile,
    TransportMode,
    build_runtime_profile,
    dance_config,
)
from core.beat_tracker import BeatTracker
from core.choreographer import Choreographer
from core.music_analyzer import MusicAnalyzer, MusicFeatures
from utils.logger import logger
from voice.intents import VoiceIntent, VoiceIntentType, parse_voice_intent

from .action_library import ActionLibrary
from .serial_driver import SerialDriver


@dataclass
class PendingVoiceAction:
    intent: VoiceIntent
    created_at: float


class RobotController:
    """统一舞蹈控制入口。"""

    def __init__(
        self,
        actions_file: str = None,
        profile_config: DemoProfileConfig = None,
    ) -> None:
        self.profile_config = profile_config or build_runtime_profile(
            RuntimeProfile.DEV,
            TransportMode.AUTO,
            RecordingMode.SMART_VAD,
        )

        self.action_library = ActionLibrary(actions_file or dance_config.actions_file)
        self.beat_tracker = BeatTracker()
        self.music_analyzer = MusicAnalyzer()
        self.choreographer = Choreographer(self.action_library, self.beat_tracker)
        self.serial_driver = SerialDriver(transport=self.profile_config.transport)

        self.is_dancing = False
        self.dance_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.voice_assistant = None
        self.pending_confirmation: Optional[PendingVoiceAction] = None
        self._feedback_message: Optional[str] = None
        self._use_demo_music = False
        self._dance_started_at = 0.0

        self.music_analyzer.set_feature_callback(self._on_music_features)
        logger.info("机器人控制器初始化完成")
        logger.info(f"  动作库: {len(self.action_library)} 个动作")
        logger.info(f"  串口模式: {self.serial_driver.get_status()['mode']}")

    def _set_feedback(self, message: str) -> None:
        self._feedback_message = message
        logger.info(message)

    def pop_feedback_message(self) -> Optional[str]:
        message = self._feedback_message
        self._feedback_message = None
        return message

    def set_voice_assistant(self, assistant) -> None:
        self.voice_assistant = assistant

    def _on_music_features(self, features: MusicFeatures) -> None:
        if features.beat_times:
            self.beat_tracker.add_beats(features.beat_times)
        self.beat_tracker.update_tempo(features.tempo)

    def _wait_for_music_ready(self, timeout_seconds: float) -> bool:
        deadline = time.time() + timeout_seconds
        last_report_time = 0.0

        while not self.stop_event.is_set() and time.time() < deadline:
            features = self.music_analyzer.get_current_features()

            now = time.time()
            if now - last_report_time >= 5.0:  # 每 5 秒输出一次
                timestamp = features.timestamp or 0.0
                energy = features.energy or 0.0
                time_diff = now - timestamp
                logger.info(
                    f"[音乐分析状态] energy={energy:.4f}, timestamp={timestamp:.3f}, "
                    f"time_diff={time_diff:.3f}s"
                )
                last_report_time = now

            if features.timestamp and features.energy > 0.001:
                return True
            time.sleep(0.1)
        return False

    def _build_demo_features(self, elapsed_seconds: float) -> MusicFeatures:
        tempo = 118.0 if int(elapsed_seconds) % 8 < 4 else 132.0
        energy = 0.55 if int(elapsed_seconds) % 8 < 4 else 0.72
        beat_interval = 60.0 / tempo
        beat_times = [beat_interval * i for i in range(1, 5)]
        return MusicFeatures(
            tempo=tempo,
            beat_times=beat_times,
            beat_strength=0.7,
            energy=energy,
            onset_strength=0.6,
            rhythm_pattern="steady" if tempo < 130 else "fast",
            mood="energetic",
            timestamp=time.time(),
            confidence=0.6,
        )

    def start_dance(self, duration_seconds: int) -> bool:
        if self.is_dancing:
            self._set_feedback("机器人正在跳舞中，请稍后再试。")
            return False

        if duration_seconds < 5 or duration_seconds > 60:
            self._set_feedback("跳舞时长必须在 5 到 60 秒之间。")
            return False

        self.stop_event.clear()
        self.choreographer.reset()
        self.beat_tracker.reset()
        self._use_demo_music = False
        self._dance_started_at = time.time()

        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(True)

        self.dance_thread = threading.Thread(
            target=self._dance_loop,
            args=(duration_seconds,),
            daemon=True,
        )
        self.dance_thread.start()
        mode = self.serial_driver.get_status()["mode"]
        self._set_feedback(f"开始跳舞 {duration_seconds} 秒，当前模式为 {mode}。")
        return True

    def stop_dance(self) -> None:
        if not self.is_dancing:
            self._set_feedback("当前没有正在执行的舞蹈。")
            return

        self.stop_event.set()
        if self.dance_thread and self.dance_thread.is_alive():
            self.dance_thread.join(timeout=2)
        self.is_dancing = False
        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(False)
        self._set_feedback("已停止跳舞。")

    def _dance_loop(self, duration_seconds: int) -> None:
        self.is_dancing = True
        started_at = time.time()
        deadline = started_at + duration_seconds

        music_active = self.music_analyzer.start()
        if music_active:
            timeout = min(15, max(6, duration_seconds * 0.6))
            if not self._wait_for_music_ready(timeout):
                logger.warning("未检测到稳定音乐输入，切换到演示节拍源")
                self._use_demo_music = True
        else:
            self._use_demo_music = True

        try:
            while not self.stop_event.is_set():
                now = time.time()
                remaining_time = deadline - now
                if remaining_time <= 0:
                    break

                if self._use_demo_music:
                    music_features = self._build_demo_features(now - started_at)
                else:
                    music_features = self.music_analyzer.get_current_features()
                    if not self.music_analyzer.has_recent_features():
                        logger.warning("音乐分析长时间未更新，切换到演示节拍源")
                        self._use_demo_music = True
                        music_features = self._build_demo_features(now - started_at)

                result = self.choreographer.select_action(
                    music_features,
                    remaining_time_ms=remaining_time * 1000,
                )
                if not result:
                    shortest = self.action_library.get_shortest_action()
                    if shortest is None:
                        time.sleep(0.2)
                        continue
                    result = (
                        shortest.label,
                        self.action_library.get_action_data(shortest.label),
                        "回退到最短动作",
                    )

                action_label, action_data, reason = result
                logger.info(f"执行动作: {action_label} ({reason})")
                if music_active and not self._use_demo_music and dance_config.choreography.beat_sync_enabled:
                    wait_ms = self.beat_tracker.time_to_next_beat()
                    if 0 < wait_ms < 180:
                        time.sleep(wait_ms / 1000)

                self.serial_driver.send_action_command(action_data["seq"])
                time.sleep(action_data["time"] / 1000)
        finally:
            if music_active:
                self.music_analyzer.stop()
            self.is_dancing = False
            if self.voice_assistant:
                self.voice_assistant.set_dance_mode(False)
            logger.info("跳舞流程结束")

    def execute_single_action(self, action_label: str) -> bool:
        action = self.action_library.get_action(action_label)
        if not action:
            self._set_feedback(f"未找到动作 {action_label}。")
            return False
        if self.is_dancing:
            self._set_feedback("机器人正在跳舞中，无法执行单个动作。")
            return False
        ok = self.serial_driver.send_action_command(action.seq)
        if ok:
            time.sleep(action.duration_seconds)
            self._set_feedback(f"已执行动作 {action.label}。")
        else:
            self._set_feedback("动作发送失败，已切换为模拟模式。")
        return ok

    def list_actions(self) -> str:
        labels = "、".join(self.action_library.get_labels())
        message = f"当前可用动作有：{labels}"
        print(message)
        return message

    def get_status(self) -> dict:
        return {
            "is_dancing": self.is_dancing,
            "serial": self.serial_driver.get_status(),
            "action_count": len(self.action_library),
            "choreographer": self.choreographer.get_status(),
            "beat_tracker": self.beat_tracker.get_status(),
            "pending_confirmation": self.pending_confirmation.intent.normalized_text
            if self.pending_confirmation
            else None,
        }

    def get_status_summary(self) -> str:
        status = self.get_status()
        mode = status["serial"]["mode"]
        state = "跳舞中" if status["is_dancing"] else "待机"
        pending = (
            f"，等待确认：{status['pending_confirmation']}"
            if status["pending_confirmation"]
            else ""
        )
        return f"机器人当前处于{state}，串口模式为 {mode}{pending}。"

    def _handle_confirmation(self, intent: VoiceIntent) -> bool:
        if not self.pending_confirmation:
            return False

        pending = self.pending_confirmation.intent
        if intent.kind == VoiceIntentType.CANCEL:
            self.pending_confirmation = None
            self._set_feedback("已取消上一条待确认命令。")
            return True
        if intent.kind == VoiceIntentType.CONFIRM:
            self.pending_confirmation = None
            if pending.kind == VoiceIntentType.DANCE and pending.duration_seconds is not None:
                self.start_dance(pending.duration_seconds)
                return True
        return False

    def handle_voice_command(self, text: str) -> bool:
        intent = parse_voice_intent(
            text,
            action_labels=self.action_library.get_labels(),
            confirm_dance_commands=self.profile_config.confirm_dance_commands,
            confirm_high_risk_only=self.profile_config.confirm_high_risk_only,
        )
        logger.info(
            "语音命令解析: original=%s normalized=%s intent=%s risk=%s",
            intent.original_text,
            intent.normalized_text,
            intent.kind.value,
            ",".join(intent.risk_flags) if intent.risk_flags else "none",
        )

        if self.pending_confirmation and intent.kind in {VoiceIntentType.CONFIRM, VoiceIntentType.CANCEL}:
            return self._handle_confirmation(intent)

        if intent.kind == VoiceIntentType.DANCE:
            if intent.duration_seconds is None:
                self._set_feedback("请说“跳舞 10 秒”这样的命令。")
                return True
            if intent.duration_seconds < 5 or intent.duration_seconds > 60:
                self._set_feedback("跳舞时长超出范围，请说 5 到 60 秒。")
                return True
            if intent.requires_confirmation:
                self.pending_confirmation = PendingVoiceAction(intent=intent, created_at=time.time())
                self._set_feedback(f"请确认，是否执行跳舞 {intent.duration_seconds} 秒？")
                return True
            return self.start_dance(intent.duration_seconds)

        if intent.kind == VoiceIntentType.STOP:
            self.stop_dance()
            return True

        if intent.kind == VoiceIntentType.ACTION and intent.action_label:
            return self.execute_single_action(intent.action_label)

        if intent.kind == VoiceIntentType.LIST_ACTIONS:
            self._set_feedback(self.list_actions())
            return True

        if intent.kind == VoiceIntentType.STATUS:
            self._set_feedback(self.get_status_summary())
            return True

        return False
