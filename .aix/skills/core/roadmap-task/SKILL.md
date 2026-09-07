---
name: core-roadmap-task
description: Create, start, block or complete TASK-* files and keep STATE.md consistent; use when work starts without a task or the user mentions backlog, roadmap, what's next, mark done.
---
# core-roadmap-task

Rules: `docs/road-map/rules.md`. Helper: `aix task {new|start|done|list}`.

## Procedure
- **new**: `aix task new "<title>" --bucket next|backlog|ideas` → fill `requirements`, `tests`, `security`, `context_files` (only files needed to do the work), Goal, Plan. Add a row to the bucket's `INDEX.md`.
- **start**: ensure `pending/next/` readiness (requirements approved, TS planned); `aix task start TASK-…`; update STATE.md "files to load" with `context_files`.
- **block**: `aix task block TASK-… "reason"` (moves to `blocked/`), question in the task and STATE.md blockers; ask the user. Unblock with `start`.
- **split**: create child tasks referencing the parent; parent's plan lists them.
- **done**: verify the DoD checklist in the task; `aix task done TASK-…`; add row to `completed/INDEX.md` if the month's INDEX exists (create from template otherwise).

## Outputs
Task file in the right folder, INDEX rows, STATE.md.
