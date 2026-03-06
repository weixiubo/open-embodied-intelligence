"""
启动自检测试。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RecordingMode, RuntimeProfile, TransportMode, build_runtime_profile


def test_startup_report_contains_transport_item():
    from utils.startup_checks import run_startup_checks

    report = run_startup_checks(
        build_runtime_profile(
            RuntimeProfile.DEMO,
            TransportMode.SIM,
            RecordingMode.SMART_VAD,
        )
    )

    assert any(item.name == "传输模式" for item in report.items)


def test_startup_report_render_has_status_lines():
    from utils.startup_checks import StartupCheckReport

    report = StartupCheckReport()
    report.add("示例", "pass", "正常")
    rendered = report.render()
    assert "启动自检结果" in rendered
    assert "示例" in rendered
