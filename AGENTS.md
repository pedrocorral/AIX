# AGENTS.md — read first (all agents, all runtimes)

Project built on **AIX**. Keep this file in context; load everything else on demand via `INDEX.md` files.

## Authority order (higher wins)
1. Accepted ADRs (`docs/requirements/decisions/`)  2. Approved requirements & contracts (`docs/requirements/`)
3. Accepted test & security specs (`docs/tests/`, `docs/security/`)  4. Source code  5. Generated artefacts

## Rules
1. **Requirements are ground truth.** Code ≠ requirement → STOP, record `docs/conflicts/open/CONFLICT-*`, run `core-conflict-resolution`, ask the user. Never silently reconcile either side.
2. **Navigate, never scan.** No `ls -R` / `find .` / "read all". Path: `docs/INDEX.md` → folder `INDEX.md` → file; or `grep -rln "<ID>"`. See `docs/meta-docs/conventions/token-economy.md`.
3. **All work is a road-map task** in `docs/road-map/going-on/` with `context_files`; `STATE.md` kept current.
4. **Trace everything.** IDs `FR/NFR/API/DM/ADR/TS/VUL/TASK/CONFLICT`; code markers `@implements`, `@tests`, `@mitigates`.
5. **No test without a `TS-*`, no `TS-*` without a requirement.** New attack surface → `VUL-*` rows as `expected`; status changes need an audit report.
6. **Ask before destructive/irreversible actions.**
7. Prefer one precise file over three broad ones, but never skip a file an INDEX marks as required.

## Navigation
| Need | Go to |
|---|---|
| How to build (arch, persistence, tests, security, stacks) | `docs/meta-docs/INDEX.md` |
| What the app must do | `docs/requirements/INDEX.md` |
| What to test / coverage | `docs/tests/INDEX.md` |
| Vulnerabilities & audits | `docs/security/INDEX.md` |
| Open conflicts | `docs/conflicts/INDEX.md` |
| Work state | `docs/road-map/going-on/STATE.md` |
| Runbooks, deploy, recovery | `docs/operations/INDEX.md` |
| Where code goes | `docs/meta-docs/architecture/project-layout.md` |
| Skills | `skills/INDEX.md` |
| Kit commands (`aix validate/coverage/task/skills`) | `docs/meta-docs/conventions/cli.md` |

## Session
Start: `core-session-resume`. Work: `core-sdd-workflow`. `core-session-handoff` after every completed task or workflow step, on stop/save, or at ~60 % context used, whichever first.

## Output
Docs use the front-matter in `docs/meta-docs/conventions/document-format.md`. Commits: `<type>(<scope>): <summary> [IDs]`.
Task report: what changed · IDs touched · tests · security rows still open · next step.

