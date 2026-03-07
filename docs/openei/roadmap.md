# OpenEI Roadmap

## Positioning

OpenEI is the future platform line for this repository.

It is not a larger dance demo. It is intended to become an embodied intelligence runtime with:

- multimodal perception
- structured intent and planning
- safety review before execution
- reusable skills and hardware adapters
- an open contribution surface for new skills, devices, and agents

One-line positioning:

`OpenEI = an OpenClaw-class open foundation for embodied intelligence`

## Branch Strategy

- `main`: competition-stable line and public default branch
- `competition-v1`: stable tag for the current competition baseline
- `openei-next`: platform incubation branch

Rules:

- Only bug fixes, competition-critical patches, and light docs updates go to `main`
- All platform refactors, agent architecture work, and subsystem redesign happen on `openei-next`
- Useful fixes from `main` may be merged or cherry-picked into `openei-next`
- `openei-next` must not be merged back into `main` during the competition period

## Phase 1 Target

Phase 1 focuses on a single-robot, single-runtime, extensible platform skeleton.

Required subsystem boundaries:

1. `Perception`: speech, vision, and sensor inputs
2. `Intent/Brain`: convert inputs into structured intents and task plans
3. `Safety`: confirmation, policy checks, constraints, and rollback decisions
4. `Skills`: dance, motion, dialogue, status, and device-facing capabilities
5. `Control`: serial, actuator, base, and hardware adapters

## Phase 1 Success Criteria

- Spoken input can be converted into structured intent objects
- High-risk actions are intercepted by a dedicated safety layer
- Skills do not directly own low-level serial control
- Simulation and real hardware share the same upper-layer behavior
- A new example skill can be added without rewriting the main control loop
