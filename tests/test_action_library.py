"""
动作库单元测试
"""

import sys
import tempfile
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestDanceAction:
    """测试 DanceAction 数据类"""
    
    def test_creation(self):
        """测试创建 DanceAction"""
        from dance.action_library import DanceAction
        
        action = DanceAction(
            seq="001",
            title="立正",
            label="立正",
            time_ms=1000,
            beats=1,
            type="stand",
            energy="low",
            tempo_match="slow",
        )
        
        assert action.seq == "001"
        assert action.title == "立正"
        assert action.label == "立正"
        assert action.time_ms == 1000
        assert action.beats == 1
        assert action.type == "stand"
        assert action.energy == "low"
        assert action.tempo_match == "slow"
    
    def test_default_values(self):
        """测试默认值"""
        from dance.action_library import DanceAction
        
        action = DanceAction(
            seq="000",
            title="测试",
            label="test",
            time_ms=2000,
        )
        
        assert action.beats == 1
        assert action.type == "general"
        assert action.energy == "medium"
        assert action.tempo_match == "any"
    
    def test_duration_seconds(self):
        """测试时长转换"""
        from dance.action_library import DanceAction
        
        action = DanceAction(
            seq="000",
            title="测试",
            label="test",
            time_ms=5500,
        )
        
        assert action.duration_seconds == 5.5
    
    def test_str_representation(self):
        """测试字符串表示"""
        from dance.action_library import DanceAction
        
        action = DanceAction(
            seq="001",
            title="立正",
            label="立正",
            time_ms=1000,
            beats=1,
            type="stand",
        )
        
        s = str(action)
        assert "立正" in s
        assert "1.0s" in s
        assert "1拍" in s


class TestActionLibrary:
    """测试 ActionLibrary"""
    
    @pytest.fixture
    def sample_csv(self):
        """创建测试用的 CSV 文件"""
        import csv
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['seq', 'title', 'label', 'time_ms', 'beats', 'type', 'energy', 'tempo_match'])
            writer.writerow(['000', '招左手', '招左手', '4000', '4', 'gesture', 'low', 'any'])
            writer.writerow(['001', '立正', '立正', '1000', '1', 'stand', 'low', 'slow'])
            writer.writerow(['002', '前进', '前进', '7500', '8', 'forward', 'high', 'fast'])
            return f.name
    
    def test_load_actions(self, sample_csv):
        """测试加载动作"""
        from dance.action_library import ActionLibrary
        from config import settings
        
        # 临时修改数据目录
        original_root = settings.project_root
        settings.project_root = Path(sample_csv).parent
        
        try:
            library = ActionLibrary(Path(sample_csv).name)
            assert len(library) == 3
        finally:
            settings.project_root = original_root
            Path(sample_csv).unlink()
    
    def test_get_action(self, sample_csv):
        """测试获取单个动作"""
        from dance.action_library import ActionLibrary
        from config import settings
        
        original_root = settings.project_root
        settings.project_root = Path(sample_csv).parent
        
        try:
            library = ActionLibrary(Path(sample_csv).name)
            
            action = library.get_action("立正")
            assert action is not None
            assert action.seq == "001"
            
            action = library.get_action("不存在")
            assert action is None
        finally:
            settings.project_root = original_root
            Path(sample_csv).unlink()
    
    def test_filter_by_time(self, sample_csv):
        """测试按时间筛选"""
        from dance.action_library import ActionLibrary
        from config import settings
        
        original_root = settings.project_root
        settings.project_root = Path(sample_csv).parent
        
        try:
            library = ActionLibrary(Path(sample_csv).name)
            
            # 筛选 5000ms 以内的动作
            filtered = library.filter_by_time(5000)
            assert len(filtered) == 2
            
            # 筛选 1000ms 以内的动作
            filtered = library.filter_by_time(1000)
            assert len(filtered) == 1
        finally:
            settings.project_root = original_root
            Path(sample_csv).unlink()
    
    def test_filter_by_type(self, sample_csv):
        """测试按类型筛选"""
        from dance.action_library import ActionLibrary
        from config import settings
        
        original_root = settings.project_root
        settings.project_root = Path(sample_csv).parent
        
        try:
            library = ActionLibrary(Path(sample_csv).name)
            
            # 筛选 stand 类型
            filtered = library.filter_by_type("stand")
            assert len(filtered) == 1
            assert filtered[0].label == "立正"
        finally:
            settings.project_root = original_root
            Path(sample_csv).unlink()
    
    def test_get_labels(self, sample_csv):
        """测试获取所有标签"""
        from dance.action_library import ActionLibrary
        from config import settings
        
        original_root = settings.project_root
        settings.project_root = Path(sample_csv).parent
        
        try:
            library = ActionLibrary(Path(sample_csv).name)
            
            labels = library.get_labels()
            assert len(labels) == 3
            assert "立正" in labels
            assert "前进" in labels
        finally:
            settings.project_root = original_root
            Path(sample_csv).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
