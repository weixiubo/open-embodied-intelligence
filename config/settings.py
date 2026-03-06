"""
基础设置模块。

从环境变量加载通用设置，并统一项目目录。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """项目级基础设置。"""

    project_root: Path = PROJECT_ROOT
    env_file: Path = ENV_FILE
    data_dir: Path = PROJECT_ROOT / "data"
    docs_dir: Path = PROJECT_ROOT / "docs"
    logs_dir: Path = PROJECT_ROOT / "logs"

    debug: bool = _env_flag("DEBUG", False)
    production: bool = _env_flag("PRODUCTION", False)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_to_file: bool = _env_flag("LOG_TO_FILE", False)
    silent_startup: bool = _env_flag("SILENT_STARTUP", False)

    def __post_init__(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
