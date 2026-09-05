---
id: CONFLICT-RULES
title: Conflict record rules
---
# Conflict record rules
- One record per conflict: `open/CONFLICT-NNNN-<title>.md` from `templates/conflict.md`; ids never reused.
- Recording a conflict freezes its scope (listed files/IDs) for every agent until resolved. Unrelated work may continue.
- The record holds the 3-column diff, options with consequences, the agent's recommendation, and later the human decision.
- Resolution: user decides → ADR written (`affects:` filled) → FR/TS/code updated → record gets `decision`, `adr`, `status: resolved` and moves to `resolved/`.
- `open/` must be empty for a release (`definition-of-done.md`).
