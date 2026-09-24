---
id: ADR-0007
title: The development cycle as an opt-in policy, anarchy by default
status: accepted
date: 2026-09-24
supersedes: []
affects: [.aix/scripts/policy.py, .aix/policies, roadmap.py, AGENTS.md]
---
# ADR-0007 — The development cycle as an opt-in policy, anarchy by default
## Context
The workflow skill told agents to spec, test, implement, audit and review, but no step named the scan commands and
nothing checked that any step ran; agents skipped the audits. A rule nobody checks is the same as no rule.
## Decision
A policy is an ordered list of steps, checks the tool runs and skills the agent performs, each required or advised,
in `policies/<name>.yaml` of any layer. `aix check` runs the checks; `aix task done` refuses to close while a
required one fails. The active steps are the `## Cycle` section of AGENTS.md. The default is `anarchy` (synonyms
`none`, `nothing`, `freedom`), a state with no file: nothing imposed. Precedence: anarchy < a layer's `defaults.yaml`
< the project's config < the task's line.
## Consequences
The cycle is one list for the agent and the tool. Organisations set their default once. A single command shows
where a task stands. Skill steps remain the agent's word: only checks are verified.
