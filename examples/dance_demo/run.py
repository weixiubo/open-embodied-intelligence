from __future__ import annotations

from openei.config import InputMode, OpenEISettings, TransportMode
from openei.runtime import build_runtime_bundle


def main() -> int:
    settings = OpenEISettings(
        input_mode=InputMode.TEXT,
        transport=TransportMode.SIM,
    )
    bundle = build_runtime_bundle(settings=settings)
    return bundle.runtime.run()


if __name__ == "__main__":
    raise SystemExit(main())

