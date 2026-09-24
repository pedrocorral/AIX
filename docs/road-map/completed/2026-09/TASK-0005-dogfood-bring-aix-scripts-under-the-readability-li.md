---
id: TASK-0005
title: Dogfood: bring .aix/scripts under the readability limits, remove the clones, review the taint findings
status: completed
created: 2026-09-24
completed: 2026-09-24
requirements: []            # FR-*/NFR-* this task delivers or touches
tests: []                   # TS-* to automate
security: []                # VUL-* to address
context_files: [.aix/meta-docs/conventions/readability.md, .aix/skills/refactor/readability/SKILL.md, .aix/skills/refactor/clone/SKILL.md]           # THE ONLY files an agent must read to work on this task
scope: [.aix/scripts/**, tests/**]                   # paths/globs this task will change (aix task start warns when two going-on tasks overlap)
owner: agent-001
claimed: 2026-09-24T17:14:40Z
claimed_by: claude claude@solarfall
policy:                     # a cycle for this task only (hotfix, release, ...); empty = the project's (aix policy)
---
# TASK-0005 — Dogfood the kit's own code

## Goal (one sentence)
The kit's own scripts and tests pass every gate the kit imposes on projects, on the `minimal` policy.
## Plan
- [x] every function under the readability limits (`aix code style .aix/scripts tests --gate`)
- [x] every file under 400 lines (module split, no behaviour change)
- [x] no clones (`aix code clones --gate`), no dead function (`aix code dead --functions --gate`), graph gate
- [x] the taint findings reviewed (`aix code vulnerabilities --gate`)
- [x] `aix check` passes on the kit
## Progress log (append-only, newest last)
- 2026-09-24: 110 offenders and 3 clone groups at the start; refactored in six batches of function extractions (helpers, small classes, dispatch tables).
- 2026-09-24: seven files over 400 lines split into leaves (graph, style, vulnerabilities, security, install, layers, the CLI); help texts moved to `.aix/meta-docs/help/*.md`.
- 2026-09-24: taint accepted markers implemented; the four `selfinstall.py` findings accepted against VUL-SECRET-001.
## Files changed (keep current)
- `.aix/scripts/*` (every module), `.aix/meta-docs/help/`, `tests/helpers.py`, `tests/test_help.py`, three pty tests, `AIX-DEVELOPMENT.md`, `CHANGELOG.md`
## Verification performed (command → result, newest last)
- `aix code style --gate` → GATE PASSED (856 functions, 0 over; 0 files over 400 lines)
- `aix code graph|dead --functions|clones|security|vulnerabilities .aix/scripts --gate` → GATE PASSED each
- `aix docs validate` → 0 errors, 0 warnings; `aix check` → cycle complete
- `aix self-test` → 110 tests OK (2 skipped: network)
## Exact next actions
1. Release when the user names the version.
## Decisions / open questions
- The kit's default code roots are `.aix/scripts` and `tests` (a project never measures `.aix/`): a special case in `codefiles.code_roots`, said in its docstring.
- VUL-SECRET-001 stays `expected` in the register until the audit skill moves it; the code markers are the evidence.
## Definition of done checklist
- [x] requirements referenced are `implemented` (none)  - [x] tests automated & green
- [x] security entries updated (code markers)  - [x] docs INDEX updated  - [ ] coverage matrix regenerated (no FR touched)
