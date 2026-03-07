# OpenEI Extension Guide

## Add a New Skill

To add a new skill in Phase 1:

1. create a class under `src/openei/skills/`
2. implement the `Skill` port
3. return `SkillResult` with optional `ControlCommand`
4. register the skill through `build_builtin_skills()`
5. add tests under `tests/openei/`

The runtime loop must not be edited to support a new skill.

The `AnnounceSkill` is the reference non-motion example for this rule.

Use this checklist when adding a skill:

- keep all hardware access out of the skill body
- emit typed `ControlCommand` values instead of calling adapters directly
- put user-facing risk handling in `safety`, not in the skill
- add at least one unit test and one integration-path assertion if the skill is end-to-end visible

## Add a New Perception Source

Implement `PerceptionSource` and return normalized `PerceptionEvent`.

Examples:

- scripted speech source
- live speech source through legacy adapters
- future camera or sensor inputs

Perception sources should normalize timestamps, source names, and raw-vs-normalized text consistently so that `brain`, `safety`, and runtime state inspection remain stable.

## Add Or Replace A Brain

Implement the `Brain` port when introducing a new planning strategy.

Rules for Phase 1:

- return `TaskPlan` and `StructuredIntent` only
- do not directly execute skills or call control adapters
- preserve safety ownership by routing every actionable plan through the safety layer
- keep new brain implementations swappable through runtime settings instead of hard-coded imports

`DeterministicSpeechBrain` is the current reference implementation.
`LLMAssistedSpeechBrain` shows how to extend planning metadata without taking over execution authority.

## Add a New Control Adapter

Implement `ControlAdapter` and keep the command surface typed.

Do not let skills call hardware libraries directly.

Adapters are the only allowed place for temporary legacy reuse.
New platform code outside `src/openei/adapters/` must not import the old `voice`, `dance`, or `core` modules directly.

## Branch And Contribution Rules

- `main` stays competition-stable
- `openei-next` is the only platform branch
- new platform work should improve one of the five layer contracts: `perception`, `brain`, `safety`, `skills`, or `control`
- if adding a new skill requires editing the runtime orchestrator, the design is wrong and should be reworked
