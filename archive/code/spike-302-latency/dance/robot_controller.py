"""
机器人控制器

集成编舞器和串口驱动，提供完整的舞蹈控制功能。
【增强版】增加详细的音乐就绪检查日志，降低音乐判断阈值，失败时自动保存日志。
【优化版】降低音乐就绪检查的最小分析时长，配合music_analyzer的低延迟参数。
"""

import time
import threading
from typing import Optional, Callable

from config import dance_config
from utils.logger import logger, save_failure_log
from core.beat_tracker import BeatTracker
from core.music_analyzer import MusicAnalyzer, MusicFeatures
from core.choreographer import Choreographer
from .action_library import ActionLibrary
from .serial_driver import SerialDriver


class RobotController:
    """
    舞蹈机器人控制器
    
    功能：
    - 集成音乐分析、编舞、硬件控制
    - 节拍同步执行舞蹈动作
    - 语音命令处理
    """
    
    def __init__(self, actions_file: str = None):
        """
        初始化机器人控制器
        
        Args:
            actions_file: 动作库文件路径
        """
        # 加载动作库
        self.action_library = ActionLibrary(actions_file or dance_config.actions_file)
        
        # 初始化组件
        self.beat_tracker = BeatTracker()
        self.music_analyzer = MusicAnalyzer()
        self.choreographer = Choreographer(self.action_library, self.beat_tracker)
        self.serial_driver = SerialDriver()
        
        # 状态
        self.is_dancing = False
        self.dance_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 回调
        self.voice_assistant = None
        
        # 设置音乐分析回调
        self.music_analyzer.set_feature_callback(self._on_music_features)
        
        logger.info("机器人控制器初始化完成")
        logger.info(f"  动作库: {len(self.action_library)}个动作")
        logger.info(f"  串口: {'已连接' if self.serial_driver.is_connected else '模拟模式'}")
    
    def _on_music_features(self, features: MusicFeatures) -> None:
        """音乐特征更新回调"""
        logger.debug(f"【回调】_on_music_features: energy={features.energy:.6f}, tempo={features.tempo:.1f}")
        # 更新节拍跟踪器
        if features.beat_times:
            self.beat_tracker.add_beats(features.beat_times)
        self.beat_tracker.update_tempo(features.tempo)

    def _is_music_ready(self, features: MusicFeatures, wait_start_time: float) -> tuple:
        """
        判断音乐分析是否已就绪（避免无音乐时立即开始编舞）
        
        【问题5】提升判断标准：足够beat_count、稳定energy、连续有效帧
        【优化】降低最小分析时长，与低延迟参数配合
        
        返回: (是否就绪, 诊断信息)
        """
        analyzed = features.timestamp > wait_start_time
        has_energy = features.energy > 0.00001  # 【降低】从0.001改为0.00001
        
        # 【问题5】更严格的节拍判断：需要至少2个beat或onset_strength足够高
        has_sufficient_beats = len(features.beat_times) >= 2
        has_strong_onset = features.onset_strength > 0.001
        has_rhythm = has_sufficient_beats or has_strong_onset
        
        # 【修改4】检查分析时长是否足够
        # 【优化】降低最小分析时长: 3.0s → 2.0s
        # 配合 music_analyzer 降低的噪声阈值和buffer窗口，可更快触发
        elapsed = features.timestamp - wait_start_time if analyzed else 0
        min_analysis_duration = 2.0  # 【修改】3.0 → 2.0 秒
        duration_sufficient = elapsed >= min_analysis_duration
        
        diagnostics = {
            "analyzed": analyzed,
            "has_energy": has_energy,
            "has_rhythm": has_rhythm,
            "has_sufficient_beats": has_sufficient_beats,
            "has_strong_onset": has_strong_onset,
            "duration_sufficient": duration_sufficient,
            "elapsed": elapsed,
            "energy_value": features.energy,
            "onset_strength": features.onset_strength,
            "beat_count": len(features.beat_times),
        }
        
        is_ready = analyzed and has_energy and has_rhythm and duration_sufficient
        
        logger.debug(
            f"【音乐就绪检查】 "
            f"elapsed={elapsed:.1f}s, "
            f"analyzed={analyzed}, "
            f"duration_ok={duration_sufficient}, "
            f"has_energy={has_energy}(E={features.energy:.6f}), "
            f"has_rhythm={has_rhythm}(beats={len(features.beat_times)}, onset={features.onset_strength:.6f}), "
            f"→ ready={is_ready}"
        )
        
        return is_ready, diagnostics

    def _wait_for_music_ready(self, timeout_seconds: float = 6.0) -> bool:
        """
        等待音乐分析结果就绪（单行进度条显示）
        """
        min_window = 10.0
        timeout_seconds = max(timeout_seconds, min_window)
        
        logger.debug(f"【等待音乐】进入: 超时时间={timeout_seconds}秒")
        print("\n---开始采集环境音乐---\n")
        
        wait_start_time = time.time()
        deadline = wait_start_time + timeout_seconds
        check_count = 0
        last_progress_time = wait_start_time

        while not self.stop_event.is_set() and time.time() < deadline:
            features = self.music_analyzer.get_current_features()
            is_ready, diagnostics = self._is_music_ready(features, wait_start_time)
            check_count += 1
            
            elapsed = time.time() - wait_start_time
            current_time = time.time()
            
            # 单行进度条显示（每 0.5s 更新一次）
            if current_time - last_progress_time >= 0.5:
                import sys
                progress_pct = min(elapsed / min_window, 1.0)
                bar_len = 20
                filled = int(bar_len * progress_pct)
                bar = '█' * filled + '░' * (bar_len - filled)
                sys.stdout.write(f"\r 音乐分析中 [{bar}] {elapsed:.1f} / {min_window:.1f}s | beats={len(features.beat_times)} | energy={features.energy:.5f}")
                sys.stdout.flush()
                last_progress_time = current_time
            
            logger.debug(f"【等待音乐】检查#{check_count} @ {elapsed:.1f}s: {diagnostics}")
            
            if is_ready:
                import sys
                bar = '█' * 20
                sys.stdout.write(f"\r 音乐分析中 [{bar}] {min_window:.1f} / {min_window:.1f}s | beats={len(features.beat_times)} | energy={features.energy:.5f}\n")
                sys.stdout.flush()
                print(f" 情感识别完成: mood={features.mood} | rhythm={features.rhythm_pattern} | tempo={features.tempo:.1f} BPM\n")
                return True
            time.sleep(0.1)
        
        import sys
        sys.stdout.write(f"\r 音乐分析失败 (超时 {timeout_seconds}s)\n")
        sys.stdout.flush()
        
        final_features = self.music_analyzer.get_current_features()
        logger.warning(
            f"未检测到有效音乐: energy={final_features.energy:.6f}, beats={len(final_features.beat_times)}"
        )
        
        save_failure_log("未检测到有效音乐输入")
        return False
    
    def set_voice_assistant(self, assistant) -> None:
        """设置语音助手实例"""
        self.voice_assistant = assistant
        logger.debug("语音助手已连接")
    
    def start_dance(self, duration_seconds: int) -> bool:
        """
        开始跳舞
        
        Args:
            duration_seconds: 跳舞时长（秒）
        
        Returns:
            是否成功启动
        """
        if self.is_dancing:
            logger.warning("机器人正在跳舞中")
            return False
        
        mode = "硬件控制" if self.serial_driver.is_connected else "模拟模式"
        logger.info(f"开始跳舞 {duration_seconds}秒 ({mode})")
        
        # 重置状态
        self.choreographer.reset()
        self.beat_tracker.reset()
        
        # 通知语音助手进入舞蹈模式
        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(True)
        
        # 启动跳舞线程
        self.stop_event.clear()
        self.dance_thread = threading.Thread(
            target=self._dance_loop,
            args=(duration_seconds,),
            daemon=True,
        )
        self.dance_thread.start()
        
        return True
    
    def stop_dance(self) -> None:
        """停止跳舞"""
        if not self.is_dancing:
            return
        
        logger.info("停止跳舞")
        self.stop_event.set()
        
        if self.dance_thread and self.dance_thread.is_alive():
            self.dance_thread.join(timeout=2)
        
        self.is_dancing = False
        
        # 恢复语音助手
        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(False)

    def _dance_loop(self, duration_seconds: int) -> None:
        """舞蹈主循环"""
        self.is_dancing = True
        start_time = time.time()

        # 启动音乐分析
        music_analysis_active = self.music_analyzer.start()
        if music_analysis_active:
            wait_timeout = max(12.0, min(15.0, duration_seconds * 0.6))
            logger.debug(f"【舞蹈循环】等待音乐就绪，超时={wait_timeout}s")
            if not self._wait_for_music_ready(timeout_seconds=wait_timeout):
                logger.warning("已取消本次跳舞")
                self.stop_event.set()
        else:
            logger.warning("音乐分析不可用，使用基础编舞模式")

        action_count = 0
        total_action_duration = 0.0
        target_duration = float(duration_seconds)

        print(f" 目标时长: {target_duration:.0f}秒\n 动作:\n")

        while not self.stop_event.is_set():
            # 基于累计动作时长结束（而非墙时间）
            if total_action_duration >= target_duration:
                print(f" 跳舞完成 | 总时长={total_action_duration:.1f}s | 动作数={action_count}\n")
                break

            music_features = self.music_analyzer.get_current_features()
            remaining_ms = (target_duration - total_action_duration) * 1000
            
            logger.debug(
                f"【舞蹈循环】当前: energy={music_features.energy:.6f}, "
                f"mood={music_features.mood}, remaining={remaining_ms/1000:.1f}s"
            )

            result = self.choreographer.select_action(
                music_features,
                remaining_ms,
            )

            if result:
                action_count += 1
                action_label, action_data, reason = result
                duration_ms = action_data['time']
                duration_s = duration_ms / 1000.0

                total_action_duration += duration_s

                print(f" #{action_count} {action_label} ({duration_s:.1f}s)")
                logger.debug(f"【动作选择】{action_label} - 理由: {reason}")

                # 等待节拍（如果启用节拍同步）
                if dance_config.choreography.beat_sync_enabled and music_analysis_active:
                    time_to_beat = self.beat_tracker.time_to_next_beat()
                    if 0 < time_to_beat < 200:
                        logger.debug(f"【节拍同步】等待{time_to_beat:.0f}ms")
                        time.sleep(time_to_beat / 1000)

                self.serial_driver.send_action_command(action_data['seq'])
                time.sleep(duration_s)
            else:
                logger.debug("未找到合适动作，等待0.5s")
                time.sleep(0.5)

        if music_analysis_active:
            logger.debug("【舞蹈循环】停止音乐分析...")
            self.music_analyzer.stop()

        self.is_dancing = False

        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(False)

        logger.debug(f"【舞蹈循环】退出: 总耗时={(time.time() - start_time):.1f}s, 动作数={action_count}")

        status = self.choreographer.get_status()
        if status['recent_actions']:
            logger.debug(f"动作序列: {' -> '.join(status['recent_actions'])}")
    
    def execute_single_action(self, action_label: str) -> bool:
        """
        执行单个动作
        
        Args:
            action_label: 动作标签
        
        Returns:
            是否执行成功
        """
        if self.is_dancing:
            logger.warning("机器人正在跳舞中，无法执行单个动作")
            return False
        
        action = self.action_library.get_action(action_label)
        if not action:
            logger.error(f"动作未找到: {action_label}")
            return False
        
        mode = "硬件控制" if self.serial_driver.is_connected else "模拟模式"
        logger.info(f"执行动作: {action.label} (Seq: {action.seq}, {action.duration_seconds:.1f}s, {mode})")
        
        # 发送命令并等待
        self.serial_driver.send_action_command(action.seq)
        time.sleep(action.duration_seconds)
        
        logger.info("动作执行完成")
        return True
    
    def list_actions(self) -> None:
        """列出所有可用动作"""
        print("\n🎭 可用动作:")
        for action in self.action_library:
            print(f"  {action.label} - {action.title} ({action.duration_seconds:.1f}s)")
    
    def get_status(self) -> dict:
        """获取控制器状态"""
        return {
            "is_dancing": self.is_dancing,
            "serial": self.serial_driver.get_status(),
            "action_count": len(self.action_library),
            "choreographer": self.choreographer.get_status(),
            "beat_tracker": self.beat_tracker.get_status(),
        }
    
    def handle_voice_command(self, text: str) -> bool:
        """
        处理语音命令
        
        【问题2】增加数值解析校验机制
        
        Args:
            text: 语音识别文本
        
        Returns:
            是否处理了命令
        """
        import re
        
        # 跳舞命令 - 【问题2】增强数值解析
        if "跳" in text:
            # 尝试多种匹配模式
            patterns = [
                r'(\d+)秒',           # "跳舞20秒"
                r'跳.*?(\d+)',        # "跳舞20"
                r'(\d+)\s*s',         # "跳舞20 s" (英文秒)
            ]
            
            duration = None
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        parsed_duration = int(match.group(1))
                        
                        # 【问题2】数值范围校验（5-60秒）
                        if 5 <= parsed_duration <= 60:
                            duration = parsed_duration
                            logger.info(
                                f"🎤 【语音解析】识别成功: "
                                f"原文=\"{text}\", "
                                f"提取时长={duration}秒 "
                                f"(范围校验通过)"
                            )
                            break
                        else:
                            logger.warning(
                                f"⚠️ 【语音解析】数值超出范围: "
                                f"原文=\"{text}\", "
                                f"提取值={parsed_duration}秒, "
                                f"有效范围=[5, 60]秒"
                            )
                    except ValueError:
                        continue
            
            if duration:
                logger.info(f"收到跳舞命令: {duration}秒")
                self.start_dance(duration)
                return True
            else:
                logger.warning(
                    f"❌ 【语音解析】无法解析有效时长: "
                    f"原文=\"{text}\", "
                    f"请说：跳舞[5-60]秒"
                )
                return False
        
        # 停止跳舞
        if any(cmd in text for cmd in dance_config.dance_stop_commands):
            logger.info("收到停止跳舞命令")
            self.stop_dance()
            return True
        
        # 执行单个动作
        if "执行动作" in text or "做动作" in text:
            for action in self.action_library:
                if action.label in text:
                    logger.info(f"收到执行动作命令: {action.label}")
                    self.execute_single_action(action.label)
                    return True
        
        # 动作列表
        if any(cmd in text for cmd in dance_config.dance_list_commands):
            self.list_actions()
            return True
        
        # 状态查询
        if "机器人状态" in text or "舞蹈状态" in text:
            status = self.get_status()
            print(f"\n🤖 状态: {'跳舞中' if status['is_dancing'] else '待机'}")
            print(f"   串口: {status['serial']['mode']}")
            print(f"   动作库: {status['action_count']}个动作")
            return True
        
        return False
