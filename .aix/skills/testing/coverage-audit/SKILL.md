---
name: testing-coverage-audit
description: Audit FR → TS → code coverage and the modules and functions no test reaches (`aix code tests`), and prune duplicate or orphan tests; use before releases, when closing features, or on "are we covered / redundant tests".
---
# testing-coverage-audit
1. `aix docs coverage`; then grep the rows for the domains in scope (never read the whole file).
2. Gaps: `no test spec` → `testing-plan-tests`; `spec not automated` → `testing-write-*`; `no code` → task or conflict.
3. The code's side: `aix code tests --untested` lists the modules no test imports; `aix code tests --priority` the functions to test first (call paths ending in it x complexity). Each untested module or top-ranked untested function → `testing-plan-tests`.
4. Orphans (tests without TS / TS without FR): propose deletion or a new FR; never delete silently.
5. Duplicates: same AC proven at two levels without distinct concerns → remove the higher one, update *Not covered here*.
6. Report table with counts and the tasks created.
