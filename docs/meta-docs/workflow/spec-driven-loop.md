---
id: META-WORKFLOW-LOOP
title: The spec-driven development loop
---
# The spec-driven loop

Code is a *derived artifact*. The loop keeps derivation explicit and auditable.

```
 requirement (FR/NFR/API/DM)  ──►  test spec (TS)  ──►  task (TASK)
        ▲                                                   │
        │  ADR (only via conflict-resolution)               ▼
        └──────────── audit (VUL) ◄──── code + tests ◄── implement
```

## Steps (every task, no exceptions)

| # | Step | Skill | Output |
|---|---|---|---|
| 1 | **Spec** — requirement exists, is `approved`, has acceptance criteria | `spec-write-requirement`, `spec-review` | `docs/requirements/**/FR-*.md` |
| 2 | **Test plan** — TS entries cover every AC, no duplicates | `testing-plan-tests` | `docs/tests/**/TS-*.md` |
| 3 | **Threat check** — new surface → `VUL-*` rows as `expected` | `security-threat-model` | `docs/security/vulnerability-register.md` |
| 4 | **Task** — plan + `context_files` listed | `core-roadmap-task` | `docs/road-map/going-on/TASK-*.md`, `STATE.md` |
| 5 | **Implement** — smallest change satisfying spec; markers `@implements` | `implement-*` | code |
| 6 | **Automate tests** — one test per TS, marker `@tests` | `testing-write-*` | test code; TS `status: automated` |
| 7 | **Audit** — run relevant `security-audit-*`; flip VULs | `security-audit` | `docs/security/audits/*.md` |
| 8 | **Close** — DoD checklist, coverage matrix, move task | `core-roadmap-task`, `core-session-handoff` | `completed/`, `STATE.md` |

## Vibe-coding mode (fast iteration) — still spec-driven
When the user wants to "just try things": create a **draft** requirement in one paragraph (statement + 2 ACs),
a **planned** TS stub, and a task. Iterate on code freely; before closing, upgrade the draft to a real
requirement reflecting what was actually decided. The kit tolerates speed, not amnesia.

## What agents must never do
- Implement behaviour that has no requirement (draft is fine) — ask first.
- "Fix" a failing test by changing the requirement.
- Mark a VUL `addressed` without an audit report.
