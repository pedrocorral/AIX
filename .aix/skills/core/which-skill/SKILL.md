---
name: core-which-skill
description: Ask which skill or flow fits the situation: a router over every installed skill, answering "what should I use for X" or "is there a skill for this".
disable-model-invocation: true
---
# core-which-skill

Reading budget: `aix skills` output only (never open SKILL.md files to answer).

## Procedure
1. Run `aix skills` (or `aix skills general` / `aix skills specific CAT`) and read the STATE and DESCRIPTION columns.
2. Match the user's situation to at most three candidates; for each, say in one line what it does and when it stops.
3. Prefer an orchestrator when the request spans several steps (`core-sdd-workflow`, `implement-feature`, `security-audit`, `testing-plan-tests`).
4. If nothing fits, say so and propose the closest skill plus what is missing; do not improvise a procedure.
5. Answer in ≤ 6 lines, then wait; the user picks. Never start the skill on their behalf.

## Outputs
A short ranked list of skills with one-line reasons. Nothing else changes.
