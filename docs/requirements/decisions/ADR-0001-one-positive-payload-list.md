---
id: ADR-0001
title: One positive list of what the kit installs
status: accepted
date: 2026-09-22
supersedes: []
affects: [.aix/scripts/payload.py, install_skills.py, upgrade.py, doctor.py]
---
# ADR-0001 — One positive list of what the kit installs
## Context
Install, upgrade and the kit-file manifest each kept their own list of kit folders; twice in September a new folder (profiles, the registry) was never upgraded because one list was not updated.
## Decision
`.aix/scripts/payload.py` is the only list, with modes owned / merged / seeded / layer. Nothing is described by exclusion; anything unlisted never leaves the checkout (`tests/`, `examples/`, the developer doc).
## Consequences
A new kit folder is declared once. The kit's own `tests/` cannot reach a project. Upgrade, doctor and the manifest cannot disagree.
