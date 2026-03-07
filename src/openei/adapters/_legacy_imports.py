from __future__ import annotations

import sys
from pathlib import Path


def ensure_legacy_project_root_on_path() -> None:
    project_root = Path(__file__).resolve().parents[3]
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
