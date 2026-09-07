---
id: META-CONV-TOKENS
title: Token economy — find, don't scan
---
# Token economy

The kit is large by design; your context is small. These recipes keep reads to a minimum.

## Decision ladder (stop at the first that answers)
1. `AGENTS.md` navigation table (already in context).
2. The folder `INDEX.md` for the area (≤ 40 lines).
3. `grep -rln "<ID>" docs` — the file list *is* the answer.
4. `grep -n "^## " <file>` — read only the heading you need with a line-range read.
5. Open the file.

## Recipes
| Need | Command |
|---|---|
| Where is requirement X? | `grep -rl "^id: FR-AUTH-003" docs/requirements` |
| Which tests cover X? | `grep -rl "FR-AUTH-003" docs/tests` |
| Where is X implemented? | `grep -rn "@implements .*FR-AUTH-003" backend frontend shared` |
| Which files touch entity User? | `grep -rln "DM-User" docs backend` |
| What is in progress? | `cat docs/road-map/going-on/STATE.md` |
| Open vulnerabilities for auth? | `grep -n "VUL-AUTH" docs/security/vulnerability-register.md` |
| Code layout for this stack? | `.aix/meta-docs/architecture/project-layout.md` + `stacks/<lang>/…` |

## Code navigation
The mandated layout (`architecture/project-layout.md`) makes paths predictable:
`backend/app/<domain>/{controllers,services,repositories,models,schemas}/` — so "where is the user repository"
is a path guess (`backend/app/users/repositories/`), not a search. Guess first, `ls` that folder only, then grep.

## Budget hints for skills
Each skill states its reading budget. If you exceed it, you are probably scanning; go back to the ladder.
Never read `coverage-matrix.md` whole — grep the ID row.
