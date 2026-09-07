---
name: core-conflict-resolution
description: Use the moment code and requirements disagree, specs contradict, or behaviour has no requirement: freeze, record CONFLICT-*, present the 3-column table and options, ask the user, write the ADR.
---
# core-conflict-resolution

Reference: `.aix/meta-docs/workflow/conflict-resolution.md` (read it; ≤ 60 lines).

## Procedure
1. Stop editing. Create `docs/conflicts/open/CONFLICT-NNNN-<title>.md` from `.aix/templates/conflict.md` (next id from `docs/conflicts/*/INDEX.md`); list the frozen scope in `affects:`. Collect: requirement ID(s) + quoted statement/AC; code location(s) `file:line` + observed behaviour; any test IDs.
2. Produce the table:

| Requirement says | Code does | Impact if we follow the requirement |
|---|---|---|

3. Offer options **A** change code (default) / **B** change requirement (needs justification → ADR) / **C** split into two requirements, plus any genuinely different option. One line each with cost/risk.
4. Ask the user to choose. End your turn. Do not proceed on assumptions.
5. On answer: create `docs/requirements/decisions/ADR-NNNN-<title>.md` from `.aix/templates/adr.md` (`status: accepted`, `affects:` filled); update the FR (`status`, text) and TS accordingly; add the ADR to `decisions/INDEX.md`; complete the conflict record (decision, evidence, `adr:`, `status: resolved`), move it to `resolved/`, update INDEXes; log the ruling in the task's progress log.
6. Resume the interrupted skill.

## Outputs
CONFLICT record (open → resolved), ADR file, updated FR/TS, task log entry.
