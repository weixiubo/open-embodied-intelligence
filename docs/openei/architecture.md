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

## Brain Modes

Phase 1 exposes two interchangeable brain strategies behind the same `Brain` port:

- `deterministic`
  - rule-driven command planning
  - current default for all runtime profiles
  - owns the stable speech-first command set
- `llm-assisted`
  - wraps the deterministic planner
  - annotates the runtime plan with LLM-assistance metadata
  - does not take over execution authority in Phase 1

This keeps the execution boundary stable while allowing later upgrades to planning logic.

## Runtime Profiles, Inputs, And Transport

The runtime configuration boundary is:

- `profile`
  - `demo`
  - `dev`
- `brain_mode`
  - `deterministic`
  - `llm-assisted`
- `input_mode`
  - `text`
  - `scripted`
  - `live-speech`
- `transport`
  - `sim`
  - `auto`
  - `real`

The settings object is the only supported bridge from environment variables and CLI arguments into the runtime.

## Inspect Surface

The stable inspect surface is:

- `source`
- `settings`
- `state`
- `skills`
- `control`
- `pending_plan`
- `event_count`

CLI consumers should prefer `openei inspect --format json`.

The current `state` snapshot contains:

- `session_id`
- `history_size`
- `last_event_text`
- `last_intent`
- `last_plan_summary`
- `last_result`

This is the Phase 1 compatibility surface for scripts, dashboards, and example apps.

## Safety Ownership

High-risk execution decisions belong to the safety layer, not to skills or control adapters.

Current centralized policy responsibilities are:

- confirmation and cancellation of pending plans
- dance-duration bounds checking
- rejecting start requests while already dancing
- rejecting single-action execution while the robot is already dancing
- profile-driven confirmation for high-risk dance tasks

Skills may describe actions, but they must not implement their own hidden confirmation logic.

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
