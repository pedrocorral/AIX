---
updated: 2026-09-24T19:14
active_task: none
agent_runtime: claude-code
---
# Session state — read this first when resuming

## Where we are (3 lines max)
- Kit 2.21.14 (2026-09-25): `aix newie`. 2.21.13: precision review of every finding on the eight clean extended projects, 154 to 66, 22 root causes fixed and tested. 2.21.12: the kit's own graph at 0 edits at both levels; commands return a change and the root re-applies. 2.21.11: `aix code graph` builds B, the ideal graph on A's nodes, and lists the edits A -> B; shortcuts are gone. 2.21.10: hygiene findings in `aix code style` (leftovers, swallowed exceptions, known bugs), tuned on the extended projects. 2.21.9: tsconfig aliases and data folders in `aix code dead`. 2.21.8: nested roots collapse, dead-code conventions, test-only clones not gated. 2.21.7: `aix self-test --extended` on twelve real projects (cache outside the repo); install into a project with its own docs/ fixed. 2.21.6: assembled-then-used rule in `aix code security` (four languages). 2.21.5: JS/TS taint in `aix code vulnerabilities`. 2.21.4: pass-through wrappers gated by `aix code style` in five languages. 2.21.3: Java support in the code tools (same-package and wildcard edges, entry classes, two-line SQL). 2.21.2: the generated reports in docs/tests are committed at release time. 2.21.1: dogfooding done, TASK-0005: the kit's own scripts and tests pass every `aix code` gate and `aix check`; modules split under 400 lines; help pages are Markdown under `.aix/meta-docs/help/`; 110 tests. 2.21.0: policies (`aix policy`, `aix check`; anarchy by default). 2.20.0: seats for several agents (`aix agent`), task claims and scopes, one STATE per seat. 2.19.3: no GitHub Actions workflow at all. 2.19.2: the test workflow removed; tests put the launcher on PATH. 2.19.1: no .gitignore line under docs/; SDDK tagline. 2.19.0: `aix guide`, the user guide in eleven chapters. 2.18.1: doctor and validate flag layer files that override nothing (typos get "did you mean"). 2.18.0: `aix self-test`, the docs split (this folder is the kit's own; projects seeded from `.aix/templates/docs`), pointer templates, 84 tests.
- Decisions of 2026-09-22/23 recorded as ADR-0001..0005 in `requirements/decisions/`; ADR-0004 (ignore whole `.aix/`) is under discussion with the team.
- Release history lives in `../../../CHANGELOG.md`; contributor entry point `../../../AIX-DEVELOPMENT.md`.
## Files to load for the active task (nothing else)
-
## Last verified facts (tests green? migrations applied? env?)
- 2026-09-24: `aix self-test` 110 green on Linux/Python 3.13 (2 skipped: network); every code gate passes on `.aix/scripts` and `tests`; Windows and macOS never run.
## Immediate next action
- Team decision on ADR-0004; then the pending list in `pending/backlog/INDEX.md`.
## Blockers / questions for the user
- ADR-0004: keep ignoring the whole `.aix/`, or only `index.json` and `manifest.json`?
