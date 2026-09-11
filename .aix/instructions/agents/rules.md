---
id: aix/agents/rules
description: "The kit's standing rules for every agent: ground truth, navigation, tasks, traceability, tests, destructive actions, modularity, the kit folder."
block: true
order: 20
section: "Rules"
---
1. **Requirements are ground truth.** Code ≠ requirement → STOP, record `docs/conflicts/open/CONFLICT-*`, run `core-conflict-resolution`, ask the user. Never silently reconcile either side.
2. **Navigate, never scan.** No `ls -R` / `find .` / "read all". Path: `docs/INDEX.md` → folder `INDEX.md` → file; or `grep -rln "<ID>"`. See `.aix/meta-docs/conventions/token-economy.md`.
3. **All work is a road-map task** in `docs/road-map/going-on/` with `context_files`; `STATE.md` kept current.
4. **Trace everything.** IDs `FR/NFR/API/DM/ADR/TS/VUL/TASK/CONFLICT`; code markers `@implements`, `@tests`, `@mitigates`. No marker → the doc may not say `implemented`/`automated`/`mitigated` (`aix docs validate` fails).
5. **No test without a `TS-*`, no `TS-*` without a requirement.** New attack surface → `VUL-*` rows as `expected`; status changes need an audit report.
6. **Ask before destructive/irreversible actions.**
7. Prefer one precise file over three broad ones, but never skip a file an INDEX marks as required.
8. **Modularity.** One job per node; dependency graph acyclic, one-directional, sparse; reuse leaves (pure, no upward deps), never hubs. `.aix/meta-docs/architecture/modularity.md`. Inside a function: `conventions/readability.md` limits (`aix code style`).
9. **`.aix/` is the kit, not the project.** Never edit it except `config.yaml` and `skills/extern/`; a fix to a kit script or skill belongs in the kit repository (`aix doctor` lists local edits; `aix upgrade` overwrites them).
