from __future__ import annotations

import argparse

from openei.config import BrainMode, InputMode, OpenEISettings, RuntimeProfile, TransportMode
from openei.runtime import build_runtime_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reference OpenEI dance demo application.")
    parser.add_argument(
        "--profile",
        choices=[item.value for item in RuntimeProfile],
        default=RuntimeProfile.DEMO.value,
    )
    parser.add_argument(
        "--brain",
        choices=[item.value for item in BrainMode],
        default=BrainMode.DETERMINISTIC.value,
    )
    parser.add_argument(
        "--input-mode",
        choices=[item.value for item in InputMode],
        default=InputMode.TEXT.value,
    )
    parser.add_argument(
        "--transport",
        choices=[item.value for item in TransportMode],
        default=TransportMode.SIM.value,
    )
    parser.add_argument("--recording-mode", default="smart_vad")
    parser.add_argument("--text", action="append", default=[], help="Scripted speech input.")
    parser.add_argument("--once", action="store_true", help="Process a single event and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_mode = InputMode.SCRIPTED if args.text else InputMode(args.input_mode)
    settings = OpenEISettings.default_for_profile(RuntimeProfile(args.profile)).with_overrides(
        brain_mode=BrainMode(args.brain),
        input_mode=input_mode,
        transport=TransportMode(args.transport),
        recording_mode=args.recording_mode,
    )
    bundle = build_runtime_bundle(settings=settings, scripted_inputs=args.text)
    return bundle.runtime.run(once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
