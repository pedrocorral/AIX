# AGENTS.md — read first (all agents, all runtimes)

Project built on **AIX**. Keep this file in context; load everything else on demand via `INDEX.md` files.

## Authority order (higher wins)
1. Accepted ADRs (`docs/requirements/decisions/`)  2. Approved requirements & contracts (`docs/requirements/`)
3. Accepted test & security specs (`docs/tests/`, `docs/security/`)  4. Source code  5. Generated artefacts

## Rules
1. **Requirements are ground truth.** Code ≠ requirement → STOP, record `docs/conflicts/open/CONFLICT-*`, run `core-conflict-resolution`, ask the user. Never silently reconcile either side.
2. **Navigate, never scan.** No `ls -R` / `find .` / "read all". Path: `docs/INDEX.md` → folder `INDEX.md` → file; or `grep -rln "<ID>"`. See `.aix/meta-docs/conventions/token-economy.md`.
3. **All work is a road-map task** in `docs/road-map/going-on/` with `context_files`; `STATE.md` kept current.
4. **Trace everything.** IDs `FR/NFR/API/DM/ADR/TS/VUL/TASK/CONFLICT`; code markers `@implements`, `@tests`, `@mitigates`. No marker → the doc may not say `implemented`/`automated`/`mitigated` (`aix docs validate` fails).
5. **No test without a `TS-*`, no `TS-*` without a requirement.** New attack surface → `VUL-*` rows as `expected`; status changes need an audit report.
6. **Ask before destructive/irreversible actions.**
7. Prefer one precise file over three broad ones, but never skip a file an INDEX marks as required.
8. **Modularity.** One job per node; dependency graph acyclic, one-directional, sparse; reuse leaves (pure, no upward deps), never hubs. `.aix/meta-docs/architecture/modularity.md`. Inside a function: `conventions/readability.md` limits (`aix code style`).
9. **`.aix/` is the kit, not the project.** Never edit it except `config.yaml` and `skills/extern/`; a fix to a kit script or skill belongs in the kit repository (`aix doctor` lists local edits; `aix upgrade` overwrites them).

## Navigation
| Need | Go to |
|---|---|
| How to build (arch, persistence, tests, security, stacks) | `.aix/meta-docs/INDEX.md` |
| What the app must do | `docs/requirements/INDEX.md` |
| What to test / coverage | `docs/tests/INDEX.md` |
| Vulnerabilities & audits | `docs/security/INDEX.md` |
| Open conflicts | `docs/conflicts/INDEX.md` |
| Work state | `docs/road-map/going-on/STATE.md` |
| Runbooks, deploy, recovery | `docs/operations/INDEX.md` |
| Where code goes | `.aix/meta-docs/architecture/project-layout.md` |
| Skills | `.aix/skills/INDEX.md` |
| Kit commands (`aix docs validate/coverage/task/skills`) | `.aix/meta-docs/conventions/cli.md` |

## Session
Start: `core-session-resume`. Work: `core-sdd-workflow`. `core-session-handoff` after every completed task or workflow step, on stop/save, or at ~60 % context used, whichever first.
Several agents may share this repository: a task is taken with `aix task start ID`, which signs it with your seat (agent-NNN) and refuses a task another live seat holds; then pick another. Never change files inside another going-on task's `scope:`. Your own state file is `docs/road-map/going-on/STATE-<seat>.md` when the table has more than one seat; `STATE.md` is then the overview. `aix agent release` when you stop.

## Output
Docs use the front-matter in `.aix/meta-docs/conventions/document-format.md`. Commits: `<type>(<scope>): <summary> [IDs]`.
Task report: what changed · IDs touched · tests · security rows still open · next step.

## Cycle
Policy `minimal` (config). Follow these steps in order; `aix check` runs the checks and `aix task done` refuses to close a task while a required one fails.
- implement (advised): skill `implement-feature` — the code carries @implements markers
- style (required): `aix code style --gate` — no function over a readability limit
- docs (required): `aix docs validate` — IDs, links, indexes and statuses are consistent

