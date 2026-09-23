---
id: ADR-0005
title: The kit's docs/ is its own; projects are seeded from a template inside .aix/
status: accepted
date: 2026-09-23
supersedes: []
affects: [.aix/scripts/payload.py, install_skills.py, .aix/templates/docs, .aix/templates/pointers]
---
# ADR-0005 — The kit's docs/ is its own; projects are seeded from a template inside .aix/
## Context
The kit's `docs/` was the template copied into projects and, at the same time, where the kit's own state and tasks were written; kit history leaked into every project and the kit's own decisions had no validated home.
## Decision
`docs/` in the kit repository is the kit's ground truth (ADRs, tasks, state, test map), validated by the kit's own tools. Projects are seeded from `.aix/templates/docs/`; pointer texts come from `.aix/templates/pointers/`. Both are overlaid by `org/` and `custom/` at the same paths, because everything installable lives inside `.aix/` so a layer can override it.
## Consequences
The kit dogfoods its documentation rules. An organisation can ship its own documentation seed and pointer texts. Nothing from the kit's `docs/` travels.
