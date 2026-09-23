# docs/ — the kit's own ground truth (AIX is an AIX project). Navigate, never scan.
Read this when: working on the kit itself. Projects receive `.aix/templates/docs/` instead, never this folder.

| Folder | What | Read when |
|---|---|---|
| `../.aix/meta-docs/` | The conventions the kit ships (architecture, testing, security, CLI, readability) | Any "how should the kit…" question |
| `requirements/` | What the kit must do: the CLI's requirements and the decisions behind it (`ADR-*`) | Before changing a command or a layout rule |
| `tests/` | The test suite map (`tests/` at the repo root) and the generated coverage matrix | Before changing a command; releasing |
| `security/` | The kit's own vulnerability register (downloads, shell profiles, git pulls) | Touching `extern.py`, `selfinstall.py`, `source.py` |
| `conflicts/` | Spec-vs-code conflicts of the kit | On any mismatch |
| `road-map/` | Kit tasks (`pending/ → going-on/ → completed/`) and `going-on/STATE.md` | Session start and end |

Contributor entry point: `../AIX-DEVELOPMENT.md` (layout, conventions, release policy). Change log: `../CHANGELOG.md`.
