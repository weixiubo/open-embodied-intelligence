from __future__ import annotations

from openei.config import InputMode, OpenEISettings, RuntimeProfile, TransportMode
from openei.runtime import build_runtime_bundle


def main() -> int:
    settings = OpenEISettings.default_for_profile(RuntimeProfile.DEMO).with_overrides(
        input_mode=InputMode.TEXT,
        transport=TransportMode.SIM,
    )
    bundle = build_runtime_bundle(settings=settings)
    return bundle.runtime.run()


if __name__ == "__main__":
    raise SystemExit(main())
