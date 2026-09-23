---
id: ADR-0002
title: The two layers follow one rule and keep their names
status: accepted
date: 2026-09-22
supersedes: []
affects: [.aix/scripts/source.py, payload.py]
---
# ADR-0002 — The two layers follow one rule and keep their names
## Context
The organisation's material lived in `.aix/custom/` of the fork and was renamed to `.aix/org/` on the way into projects; a colleague editing the fork's `org/` saw nothing propagate.
## Decision
`.aix/org/` and `.aix/custom/` are one payload mode (`layer`): copied at install when the origin has the folder, replaced at upgrade when it has it, left alone when it does not. Same name in the fork and in every project. `--from-org SRC` / `--from-custom SRC` take one layer from elsewhere.
## Consequences
An organisation fills `.aix/org/` in its fork; an edit there reaches projects at the next `aix upgrade`. A fork's `custom/` travels too.
