# OpenEI Repository

This repository currently contains two lines of work:

- `main`
  - competition-stable branch for the existing robot demo
- `openei-next`
  - platform branch for OpenEI, a speech-first embodied intelligence runtime

## OpenEI Positioning

OpenEI is not a larger dance demo.
It is the platform line that aims to become an open runtime for embodied intelligence with:

- multimodal perception inputs
- structured intent and task planning
- a dedicated safety review layer
- reusable skills and hardware adapters
- simulation and real hardware sharing the same upper-layer logic

## Phase 1 Status

The current `openei-next` branch contains the Phase 1 runtime kernel:

- `src/openei/`
  - platform package with `perception`, `brain`, `safety`, `skills`, `control`, `runtime`, `adapters`, and `cli`
- `docs/openei/`
  - architecture and extension guidance
- `examples/dance_demo/`
  - example app running the legacy dance capability on top of OpenEI

## Quick Start

Install the package in editable mode:

```bash
python -m pip install -e .[dev]
```

Inspect the runtime:

```bash
openei inspect --profile demo --brain deterministic --transport sim --format json
```

Run a one-shot scripted dance command:

```bash
openei run --profile demo --transport sim --text "dance 10 seconds" --once
```

Run a one-shot non-motion command:

```bash
openei run --profile demo --transport sim --text "announce OpenEI is ready" --once
```

## Engineering Baseline

OpenEI Phase 1 uses:

- `pyproject.toml` as the packaging and tooling source of truth
- `src/` layout for the platform package
- `ruff`, `mypy`, and `pytest` for quality gates
- adapter-only reuse of legacy `dance` and `voice` code

## Branch Rules

- do not merge platform refactors into `main` during the competition period
- all OpenEI platform work belongs on `openei-next`
- useful fixes from `main` may be cherry-picked or merged into `openei-next`

## Current Phase 1 Focus

The current OpenEI milestone is not "full multi-agent robotics" yet.
The active focus is:

- close the Phase 1 runtime loop
- harden `perception -> brain -> safety -> skill -> control`
- keep high-risk execution decisions centralized in `safety`
- reduce legacy coupling behind adapters
