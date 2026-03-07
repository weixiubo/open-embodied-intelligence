from __future__ import annotations

import argparse
import json

from ..config import BrainMode, InputMode, OpenEISettings, RuntimeProfile, TransportMode
from ..runtime.builder import build_runtime_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenEI runtime CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the OpenEI runtime.")
    run_parser.add_argument(
        "--profile",
        choices=[item.value for item in RuntimeProfile],
        default=RuntimeProfile.DEMO.value,
    )
    run_parser.add_argument(
        "--brain",
        choices=[item.value for item in BrainMode],
        default=BrainMode.DETERMINISTIC.value,
    )
    run_parser.add_argument("--transport", choices=[item.value for item in TransportMode], default=TransportMode.SIM.value)
    run_parser.add_argument(
        "--input-mode",
        choices=[item.value for item in InputMode],
        default=InputMode.TEXT.value,
    )
    run_parser.add_argument("--recording-mode", default="smart_vad")
    run_parser.add_argument("--text", action="append", default=[], help="Scripted speech input.")
    run_parser.add_argument("--once", action="store_true", help="Process a single event and exit.")

    skills_parser = subparsers.add_parser("skills", help="Inspect registered skills.")
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", required=True)
    list_parser = skills_subparsers.add_parser("list", help="List registered skills.")
    list_parser.add_argument("--format", choices=("text", "json"), default="text")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect runtime configuration.")
    inspect_parser.add_argument(
        "--profile",
        choices=[item.value for item in RuntimeProfile],
        default=RuntimeProfile.DEMO.value,
    )
    inspect_parser.add_argument(
        "--brain",
        choices=[item.value for item in BrainMode],
        default=BrainMode.DETERMINISTIC.value,
    )
    inspect_parser.add_argument("--transport", choices=[item.value for item in TransportMode], default=TransportMode.SIM.value)
    inspect_parser.add_argument(
        "--input-mode",
        choices=[item.value for item in InputMode],
        default=InputMode.TEXT.value,
    )
    inspect_parser.add_argument("--recording-mode", default="smart_vad")
    inspect_parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        input_mode = InputMode.SCRIPTED if args.text else InputMode(args.input_mode)
        settings = OpenEISettings.default_for_profile(RuntimeProfile(args.profile)).with_overrides(
            brain_mode=BrainMode(args.brain),
            input_mode=input_mode,
            transport=TransportMode(args.transport),
            recording_mode=args.recording_mode,
        )
        bundle = build_runtime_bundle(settings=settings, scripted_inputs=args.text)
        return bundle.runtime.run(once=args.once)

    if args.command == "skills" and args.skills_command == "list":
        bundle = build_runtime_bundle()
        descriptors = bundle.skills.describe()
        if args.format == "json":
            print(json.dumps([descriptor.to_dict() for descriptor in descriptors], ensure_ascii=False, indent=2))
            return 0
        for descriptor in descriptors:
            print(f"{descriptor.name}: {descriptor.description}")
        return 0

    if args.command == "inspect":
        settings = OpenEISettings.default_for_profile(RuntimeProfile(args.profile)).with_overrides(
            brain_mode=BrainMode(args.brain),
            input_mode=InputMode(args.input_mode),
            transport=TransportMode(args.transport),
            recording_mode=args.recording_mode,
        )
        bundle = build_runtime_bundle(settings=settings)
        snapshot = bundle.runtime.inspect()
        if args.format == "json":
            print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))
            return 0
        for key, value in snapshot.to_dict().items():
            print(f"{key}: {value}")
        return 0

    parser.print_help()
    return 1
