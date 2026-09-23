---
updated: 2026-09-23T10:00
active_task: none
agent_runtime: claude-code
---
# Session state — read this first when resuming

## Where we are (3 lines max)
- Kit 2.19.0 (2026-09-23): `aix guide`, the user guide in eleven chapters. 2.18.1: doctor and validate flag layer files that override nothing (typos get "did you mean"). 2.18.0: `aix self-test`, the docs split (this folder is the kit's own; projects seeded from `.aix/templates/docs`), pointer templates, 84 tests.
- Decisions of 2026-09-22/23 recorded as ADR-0001..0005 in `requirements/decisions/`; ADR-0004 (ignore whole `.aix/`) is under discussion with the team.
- Release history lives in `../../../CHANGELOG.md`; contributor entry point `../../../AIX-DEVELOPMENT.md`.
## Files to load for the active task (nothing else)
-
## Last verified facts (tests green? migrations applied? env?)
- 2026-09-23: `aix self-test` 78 green on Linux/Python 3.13; Windows and macOS await the first CI run.
## Immediate next action
- Team decision on ADR-0004; then the pending list in `pending/backlog/INDEX.md`.
## Blockers / questions for the user
- ADR-0004: keep ignoring the whole `.aix/`, or only `index.json` and `manifest.json`?
