---
name: spec-write-adr
description: Record an ADR for stack, library, persistence, mapping, API-style choices, conflict rulings, accepted risks or deprecations — anything someone will later ask why about.
---
# spec-write-adr
1. Next ID from `decisions/INDEX.md`. Copy `.aix/templates/adr.md`.
2. Context in ≤ 8 lines; options with one-line trade-offs; decision; consequences listing FR/TS/files to update (`affects:`).
3. If superseding: set `supersedes:` and mark the old ADR `status: superseded`.
4. Add row to `decisions/INDEX.md`; reference the ADR in affected FR `related:` and in the task's progress log.
