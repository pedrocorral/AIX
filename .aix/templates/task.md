---
id: TASK-0000
title: Task title
status: pending             # pending | going-on | blocked | completed
created: YYYY-MM-DD
completed:
requirements: []            # FR-*/NFR-* this task delivers or touches
tests: []                   # TS-* to automate
security: []                # VUL-* to address
context_files: []           # THE ONLY files an agent must read to work on this task
scope: []                   # paths/globs this task will change (aix task start warns when two going-on tasks overlap)
owner:                      # the seat that holds it (agent-001 ...), signed by aix task start
claimed:
claimed_by:                 # tool user@host behind the seat at that moment (stays after the seat is released)
---
# TASK-0000 — Title

## Goal (one sentence)
## Plan
- [ ] step
## Progress log (append-only, newest last)
- YYYY-MM-DD: …
## Files changed (keep current)
-
## Verification performed (command → result, newest last)
-
## Exact next actions
1.
## Decisions / open questions
## Definition of done checklist
- [ ] requirements referenced are `implemented`  - [ ] tests automated & green
- [ ] security entries updated  - [ ] docs INDEX updated  - [ ] coverage matrix regenerated
