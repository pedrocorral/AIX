---
name: testing-coverage-audit
description: Audit FR → TS → code coverage and prune duplicate or orphan tests via the coverage matrix; use before releases, when closing features, or on "are we covered / redundant tests".
---
# testing-coverage-audit
1. `aix coverage`; then grep the rows for the domains in scope (never read the whole file).
2. Gaps: `no test spec` → `testing-plan-tests`; `spec not automated` → `testing-write-*`; `no code` → task or conflict.
3. Orphans (tests without TS / TS without FR): propose deletion or a new FR; never delete silently.
4. Duplicates: same AC proven at two levels without distinct concerns → remove the higher one, update *Not covered here*.
5. Report table with counts and the tasks created.
