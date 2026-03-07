# OpenEI Architecture

## Runtime Layers

OpenEI Phase 1 uses a strict inward-facing architecture:

1. `perception`
   - converts external input into normalized `PerceptionEvent`
2. `brain`
   - converts perception events into `StructuredIntent` and `TaskPlan`
3. `safety`
   - decides whether a plan should be allowed, confirmed, rejected, or modified
4. `skills`
   - turns task steps into `SkillResult` and typed `ControlCommand`
5. `control`
   - executes typed commands in simulation or through legacy hardware adapters

The runtime orchestrator is responsible for wiring these layers together and nothing else.

## Runtime Profiles And Inspect Surface

Phase 1 exposes two runtime profiles:

- `demo`
  - confirmation stays enabled for high-risk dance requests
  - startup messages and prompts are presentation-oriented
- `dev`
  - confirmation can be relaxed for faster iteration
  - prompt and greeting make the environment explicit

The stable inspect surface is:

- `source`
- `settings`
- `skills`
- `control`
- `pending_plan`
- `event_count`

CLI consumers should prefer `openei inspect --format json`.

## Dependency Rules

- `runtime` may depend on contracts, ports, skills, control, perception, brain, and safety
- `brain`, `safety`, `skills`, and `control` may depend on contracts and ports
- `adapters` may depend on legacy project modules
- new platform code outside `adapters` must not import legacy `voice`, `dance`, `core`, or `serial` modules directly

## Temporary Legacy Boundaries

OpenEI Phase 1 reuses legacy capabilities through adapters only:

- `LegacyDanceCatalog`
- `LegacyDanceControlAdapter`
- `LegacyLiveSpeechSource`

This allows the new runtime to stay modular while avoiding a full hardware rewrite in the first milestone.
