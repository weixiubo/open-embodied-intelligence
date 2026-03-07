# OpenEI Status, Gap Map, And Build Order

## Current Position

OpenEI on `openei-next` is now a real Phase 1 platform skeleton rather than an empty concept.

Approximate completion levels:

- `Phase 1 platform skeleton`: `65%-70%`
- `single-robot usable runtime`: `30%-35%`
- `long-term OpenClaw-class embodied platform`: `15%-20%`

What already exists:

- layered package under `src/openei/`
- typed contracts and runtime ports
- speech-first planning pipeline
- centralized safety policy
- declarative skill registration
- CLI, inspect surface, tests, and CI

## Gap Map

### Brain / Intent

Current state:

- mostly a typed, deterministic command router
- no session-level planner or memory-backed task progression
- no production LLM-planning contract yet

Needed next:

- swappable planning strategies
- richer task decomposition
- memory-aware plan generation

### Perception

Current state:

- `text`
- `scripted`
- `legacy live-speech`

Needed next:

- first-class event model for future camera and sensor inputs
- better source metadata, timestamps, and normalization guarantees

### Safety

Current state:

- centralized allow / confirm / reject
- pending confirmation handling
- duration bounds and state preconditions

Needed next:

- action budgets
- rollback policy
- execution watchdogs
- capability-aware safety rules

### Skills

Current state:

- built-in skills with declarative registration
- no runtime-loop edits required for new skills

Needed next:

- plugin discovery
- manifests
- capability metadata
- versioned extension surfaces

### Control

Current state:

- simulation-first adapter
- legacy-backed real control path

Needed next:

- device-neutral hardware interface
- non-legacy real adapter
- explicit capability discovery

### Runtime / Ops

Current state:

- CLI runtime
- stable inspect output
- bounded event history
- runtime state snapshot

Needed next:

- session memory
- multi-step task execution
- recovery flow
- observability and service surface

## Build Order

### Milestone A: Close Phase 1

Objective:

- finish the single-robot, single-runtime closed loop

Priority items:

- keep UTF-8-safe repository content and avoid terminal-hostile examples
- preserve brain swappability without giving execution authority to LLM planning
- keep safety centralized
- use `examples/dance_demo` as the reference OpenEI app

### Milestone B: Single-Robot Embodied Runtime

Objective:

- move from command routing to task runtime

Priority items:

- session state and memory store
- multi-step `TaskPlan`
- first non-legacy real control adapter
- capability model for skills and adapters

### Milestone C: Contributor Platform

Objective:

- make OpenEI extensible without core edits

Priority items:

- plugin loading
- manifests and templates
- benchmark and example matrix
- release discipline and contribution templates

### Milestone D: Long-Term Foundation

Objective:

- grow into a broader embodied intelligence foundation

Priority items:

- multimodal fusion
- multi-agent delegation
- long-horizon memory
- simulation and evaluation loops
- remote service and observability surfaces

## Non-Negotiable Engineering Rules

- `main` stays competition-stable
- `openei-next` is the only platform branch
- no direct legacy imports outside `src/openei/adapters/`
- new skills must not require runtime-orchestrator edits
- high-risk execution review belongs to `safety`
