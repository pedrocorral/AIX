---
id: ADR-0004
title: Projects ignore the whole .aix/ folder
status: accepted, under discussion
date: 2026-09-22
supersedes: []
affects: [.aix/scripts/gitignore.py]
---
# ADR-0004 — Projects ignore the whole .aix/ folder
## Context
AIX generates per-machine files (agent links, rendered instructions, index, manifest, reports). The user decided to ignore the whole `.aix/` rather than only those.
## Decision
`aix install`, `aix upgrade` and `aix agents` offer to add `.aix/`, the selected agents' skills folders, rendered `aix-*` files and the reports to `.gitignore` (y/N; `upgrade --yes` answers yes).
## Consequences
The kit copy, `.aix/custom/` and `.aix/org/` are not versioned with the project: every teammate and CI job runs `aix install --into .` first; doctor cannot compare a teammate's copy with the project's. Reversal is one edit to `gitignore.wanted()`. Under discussion with the team.
