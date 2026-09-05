---
name: core-session-resume
description: Resume work at session start or on "continue / where were we / pick up": reads STATE.md, the active task and its context_files only.
---
# core-session-resume

Reading budget: ≤ 3 000 tokens before speaking.

## Procedure
1. `cat docs/road-map/going-on/STATE.md`; `cat docs/conflicts/open/INDEX.md` (any row = frozen scope; do not touch those files).
2. If `active_task` is set: open `docs/road-map/going-on/<TASK>.md`; read `context_files` list; open exactly those files.
   If `none`: `cat docs/road-map/pending/next/INDEX.md`; propose the top task to the user (one line) unless the user already stated what to do.
3. Verify cheaply: `git status --short`, and run the test command named in the task (or the domain's unit tests only).
4. Report in ≤ 6 lines: active task + goal, last progress entry, verified facts (tests/git), immediate next action, blockers. Then proceed with `core-sdd-workflow`.

## Rules
- If STATE.md is stale (older than the latest `completed/` entry or git log), say so and rebuild it from the task file + git log; do not guess.
- Never read `completed/` unless the task references it.
