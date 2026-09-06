---
updated: 2026-09-05T19:55
active_task: none
agent_runtime: claude-code
---
# Session state — read this first when resuming

## Where we are (3 lines max)
- Kit work: TASK-0002 (Antigravity + Gemini CLI support via `GEMINI.md` pointer) completed 2026-09-05; changes uncommitted in the working tree.
- Kit changelog has a growing `Unreleased` section; version still 1.3.0.
## Files to load for the active task (nothing else)
-
## Last verified facts (tests green? migrations applied? env?)
- 2026-09-05: `aix install`, `aix validate` (0/0), `aix doctor` (healthy), `aix coverage`, `--into` scratch install all green.
## Immediate next action
- Review and commit TASK-0002; decide where kit-development tasks live (they ship in the `--into` payload with `docs/`).
## Blockers / questions for the user
- `aix skills always NAME` rejects built-in skills (extern.py `known_skill`); follow-up flagged.
