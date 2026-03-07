from __future__ import annotations

from openei.cli.main import main


def test_cli_lists_skills(capsys) -> None:
    exit_code = main(["skills", "list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "dance:" in captured.out
    assert "system:" in captured.out


def test_cli_runs_scripted_command(capsys) -> None:
    exit_code = main(["run", "--transport", "sim", "--text", "跳舞50秒", "--once"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "请确认" in captured.out

