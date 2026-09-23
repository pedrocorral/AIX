---
id: META-GUIDE-DOCS
title: The documentation
---
# 8. The documentation

## The folder
`docs/` is your project's ground truth. The agent navigates it through `INDEX.md` files, one per folder, and never
scans it whole. Seeded at install with an EXAMPLE domain you replace.

| Folder | Holds | IDs |
|---|---|---|
| `requirements/functional/`, `non-functional/`, `api/`, `data-model/` | What the software must do | `FR-`, `NFR-`, `API-`, `DM-` |
| `requirements/decisions/` | Why it is the way it is | `ADR-` |
| `requirements/product/` | Vision, personas, glossary | |
| `tests/` | What must be proven, and the generated coverage matrix | `TS-` |
| `security/` | The vulnerability register and audit reports | `VUL-` |
| `conflicts/` | Spec-versus-code disagreements, open ones freeze their scope | `CONFLICT-` |
| `road-map/` | Tasks: `pending/ → going-on/ → completed/`, and `going-on/STATE.md` | `TASK-` |
| `operations/` | Runbooks, deployment, recovery | |

Every document starts with YAML front matter: `id`, `title`, `status`. Templates for each type live in
`.aix/templates/`. Files stay under 300 lines; a folder under 12 files; more means a sub-folder.

## Markers in code
Code says what it fulfils: a comment `@implements FR-001`, `@tests TS-001`, `@mitigates VUL-INJ-001`. The
documents then may claim `implemented`, `automated`, `mitigated`. Without the marker the claim is drift, and the
validator says so.

## The commands
```
aix docs validate          IDs, links, indexes, front matter, status claims against the markers; exit 1 on errors
aix docs coverage          writes tests/coverage-matrix.md: requirement -> test spec -> code -> gaps
aix docs security          the register: validated versus not, audits still to run, missing evidence
aix docs security --gate   the release check
aix task new "title" | start ID | block ID "reason" | done ID | list
```
`aix docs validate` also checks the skills and instructions of every layer and the near-miss rule of chapter 7.

## STATE.md
`docs/road-map/going-on/STATE.md` is the resume point: where we are, which files to load for the active task,
last verified facts, next action, blockers. The agent reads it first at every session start and rewrites it at every
hand-off. The skills `core-session-resume` and `core-session-handoff` do exactly that.

## The register
`docs/security/vulnerability-register.md` lists `VUL-*` rows with a status: `expected`, `unverified`,
`confirmed`, `mitigated`, `addressed`, `accepted`, `not-applicable`. A status moves only with evidence: an audit
report under `security/audits/`, written by an audit skill or by `aix code security --audit`. `aix docs security`
shows what is still unproven; `--gate` fails a release with unproven rows.
