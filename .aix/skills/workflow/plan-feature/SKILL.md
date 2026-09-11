---
name: workflow-plan-feature
description: Plan multi-step work by searching the existing code first, naming reuse candidates, then defining ordered steps with acceptance checks; use before implementing anything larger than one function.
---
# workflow-plan-feature

Reading budget: the FR/API/DM docs of the feature, `aix code graph` on the domain, `aix code clones` (reuse), ≤ 3 source files.

## Procedure
1. Requirements first: `core-find-doc` the FR ids; missing → `spec-write-requirement` before any plan.
2. Reuse search: `grep -rn` for the domain nouns and `aix code clones`; list what exists (ports, services, components) and what is new.
3. Steps: ordered, each ≤ one session, each with a verifiable check (a test, a command); dependencies stated.
4. Risks and unknowns: one line each with how the step resolves them (spike, question to the user).
5. Record as a task (`core-roadmap-task`) with `context_files`; ask approval when the plan changes an ADR.

## Outputs
A task file with the ordered steps and checks; questions for the user listed at the top.
