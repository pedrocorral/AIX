---
name: review-code-review
class: review/code-review
id: "@acme/review-three-lenses"
version: 1.0.0
description: Review a diff against AIX rules: layering, MVC placement, persistence abstraction, markers, requirement fidelity, tests, security baseline; use before closing tasks, on PRs, or "review this".
---
# @acme/review-three-lenses

ACME reviews a change through three lenses, in this order, and stops at the first that fails.
1. **Behaviour**: does the diff do what its FR/TS ids say and nothing else? Run the TS tests; read the ids in the task.
2. **Blast radius**: `aix code graph` on the touched folders: a new CUT = request changes; a new SPLIT = ask why.
3. **Evidence**: tests changed with the code, `@tests` markers present, docs rows updated, `aix code security` clean on the diff.
Verdict in ≤ 8 lines: lens, finding, file:line, the fix. Approve only when all three lenses pass.
