# docs/ — the project's brain. Navigate, never scan.

| Folder | What | Read when |
|---|---|---|
| `../.aix/meta-docs/` | How to build software with this kit (architecture, persistence, testing, security, stacks, conventions, workflow). Language-agnostic core + `stacks/`. | Any "how should I…" question. Start at `.aix/meta-docs/INDEX.md`. |
| `requirements/` | **Ground truth** for this application. IDs `FR/NFR/API/DM/ADR`. | Before implementing or testing anything. |
| `tests/` | Test specifications (`TS-*`) + generated coverage matrix. | Before writing or reviewing tests. |
| `security/` | Vulnerability register (`VUL-*`) + audit reports. | Before touching auth, input, data, deps, LLM calls; during audits. |
| `conflicts/` | Open and resolved spec-vs-code conflicts (`CONFLICT-*`); open ones freeze their scope. | Session start; on any mismatch. |
| `operations/` | Runbooks, deployment, recovery, incident notes. | Deploying, on-call, recovery. |
| `road-map/` | Tasks (`pending/ → going-on/ → completed/`) and `going-on/STATE.md`. | Session start, session end, picking work. |

Rules for every folder: has an `INDEX.md`; files ≤ ~300 lines (split otherwise); YAML front-matter with `id`
where an ID applies (`.aix/meta-docs/conventions/document-format.md`).
