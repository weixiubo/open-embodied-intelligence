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

## Add a New Perception Source

Implement `PerceptionSource` and return normalized `PerceptionEvent`.

Examples:

- scripted speech source
- live speech source through legacy adapters
- future camera or sensor inputs

## Add a New Control Adapter

Implement `ControlAdapter` and keep the command surface typed.

Do not let skills call hardware libraries directly.
