"""
机器人控制器

集成编舞器和串口驱动，提供完整的舞蹈控制功能。
"""

import time
import threading
from typing import Optional, Callable

from config import dance_config
from utils.logger import logger
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
        # 更新节拍跟踪器
        if features.beat_times:
            self.beat_tracker.add_beats(features.beat_times)
        self.beat_tracker.update_tempo(features.tempo)

    def _is_music_ready(self, features: MusicFeatures, wait_start_time: float) -> bool:
        """判断音乐分析是否已就绪（避免无音乐时立即开始编舞）"""
        analyzed = features.timestamp > wait_start_time
        has_energy = features.energy > 0.001
        has_rhythm = bool(features.beat_times) or features.onset_strength > 0.05
        return analyzed and has_energy and has_rhythm

    def _wait_for_music_ready(self, timeout_seconds: float = 6.0) -> bool:
        """等待音乐分析结果就绪"""
        wait_start_time = time.time()
        deadline = wait_start_time + timeout_seconds

        while not self.stop_event.is_set() and time.time() < deadline:
            features = self.music_analyzer.get_current_features()
            if self._is_music_ready(features, wait_start_time):
                logger.info(
                    f"音乐就绪: tempo={features.tempo:.1f}, "
                    f"energy={features.energy:.4f}, mood={features.mood}"
                )
                return True
            time.sleep(0.1)

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
        end_time = start_time + duration_seconds
        
        # 启动音乐分析
        music_analysis_active = self.music_analyzer.start()
        if music_analysis_active:
            logger.info("音乐分析已启动，开始智能编舞")
            wait_timeout = min(8.0, max(3.0, duration_seconds * 0.4))
            if not self._wait_for_music_ready(timeout_seconds=wait_timeout):
                logger.warning("未检测到有效音乐输入，已取消本次跳舞")
                self.stop_event.set()
        else:
            logger.warning("音乐分析不可用，使用基础编舞模式")
        
        while not self.stop_event.is_set():
            current_time = time.time()
            remaining_time = end_time - current_time
            
            if remaining_time <= 0:
                logger.info(f"已达到目标时间 {duration_seconds}秒，结束跳舞")
                break
            
            # 获取当前音乐特征
            music_features = self.music_analyzer.get_current_features()
            
            # 选择动作
            result = self.choreographer.select_action(
                music_features,
                remaining_time * 1000,  # 转换为毫秒
            )
            
            if result:
                action_label, action_data, reason = result
                duration_ms = action_data['time']
                
                logger.info(f"执行动作: {action_label} (Seq: {action_data['seq']}, {duration_ms/1000:.1f}s)")
                logger.debug(f"选择理由: {reason}")
                
                # 等待节拍（如果启用节拍同步）
                if dance_config.choreography.beat_sync_enabled and music_analysis_active:
                    time_to_beat = self.beat_tracker.time_to_next_beat()
                    if time_to_beat > 0 and time_to_beat < 200:  # 200ms 内的节拍
                        time.sleep(time_to_beat / 1000)
                        logger.debug(f"节拍同步: 等待 {time_to_beat:.0f}ms")
                
                # 发送舵机命令
                self.serial_driver.send_action_command(action_data['seq'])
                
                # 等待动作完成
                time.sleep(duration_ms / 1000)
            else:
                # 没有合适的动作，等待一小段时间
                time.sleep(0.5)
        
        # 停止音乐分析
        if music_analysis_active:
            self.music_analyzer.stop()
        
        self.is_dancing = False
        
        # 恢复语音助手
        if self.voice_assistant:
            self.voice_assistant.set_dance_mode(False)
        
        logger.info("跳舞结束")
        
        # 打印编舞状态
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
        
        Args:
            text: 语音识别文本
        
        Returns:
            是否处理了命令
        """
        import re
        
        # 跳舞命令
        if "跳舞" in text:
            match = re.search(r'(\d+)秒', text)
            if match:
                duration = int(match.group(1))
                logger.info(f"收到跳舞命令: {duration}秒")
                self.start_dance(duration)
                return True
        
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
