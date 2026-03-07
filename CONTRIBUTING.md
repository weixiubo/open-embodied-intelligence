# Contributing to OpenEI

## Branch Policy

- `main` is the competition-stable line
- `openei-next` is the platform incubation line

Do not merge platform refactors into `main` during the competition period.

## Engineering Expectations

- keep modules cohesive and focused
- prefer typed contracts over ad-hoc dictionaries between layers
- avoid direct cross-layer imports that bypass runtime ports
- add tests for new skills, safety logic, and runtime behavior
- prefer adapters when temporary legacy reuse is necessary

## Pull Requests

- target `openei-next` for platform work
- include tests for the new behavior
- describe whether the change touches perception, brain, safety, skills, control, or adapters

