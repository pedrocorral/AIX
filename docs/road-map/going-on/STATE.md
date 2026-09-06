---
updated: 2026-09-05T19:55
active_task: none
agent_runtime: claude-code
---
# Session state — read this first when resuming

## Where we are (3 lines max)
- Kit work: TASK-0002 (Antigravity + Gemini CLI support via `GEMINI.md` pointer) completed 2026-09-05; changes uncommitted in the working tree.
- Kit 1.6.0 (2026-09-06): command groups `aix code ...` / `aix docs ...`, old names aliased. 1.5.4: `aix code clones`. 1.5.3: `aix code dead`. 1.5.2: README modularity section, graph options in help. 1.5.1: `aix code graph` measurement fixed (stability, contracted cycles, upward deps, NCCD, Q, selftest). 1.5.0 on 2026-09-06: `aix code graph`/`complexity` (modularity metric), per-command help, kit scripts made acyclic. 1.4.0 earlier the same day: CLI, upgrade, security gate, modularity, Gemini/Antigravity.
## Files to load for the active task (nothing else)
-
## Last verified facts (tests green? migrations applied? env?)
- 2026-09-05: `aix install`, `aix docs validate` (0/0), `aix doctor` (healthy), `aix docs coverage`, `--into` scratch install all green.
## Immediate next action
- Review and commit TASK-0002; decide where kit-development tasks live (they ship in the `--into` payload with `docs/`).
## Blockers / questions for the user
- `aix skills always NAME` rejects built-in skills (extern.py `known_skill`); follow-up flagged.
