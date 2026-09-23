---
id: ROADMAP-RULES
title: Road-map rules
---
# Road-map rules
- A task is the unit of agent work; ≤ 1 day of effort; has `requirements`, `tests`, `security`, `context_files`.
- `context_files` is the contract for token economy: an agent resuming the task reads those and nothing else first.
- Lifecycle: `pending/ideas → pending/backlog → pending/next → going-on ⇄ blocked → completed/YYYY-MM`. Only `aix task` (or equivalent edits) moves files; status field must match folder.
- `going-on/` holds at most one task per agent. `STATE.md` is rewritten (not appended) at every hand-off.
- Blocked: move to `blocked/` (`roadmap.py block TASK-… "reason"`), question in "Decisions / open questions" + `STATE.md` blockers; unblock with `start`.
- Completed tasks are never edited; follow-ups become new tasks referencing the old ID.
- Each `pending/*/` folder has an `INDEX.md` ordered by priority (top = next).
