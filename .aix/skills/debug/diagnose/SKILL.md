---
name: debug-diagnose
description: Diagnosis loop for hard bugs and performance regressions: reproduce, hypothesise, test one hypothesis at a time, fix the root cause, add the regression test; use on "diagnose / debug / why is this slow".
---
# debug-diagnose

Reading budget: the failing test or report, `scripts/hypothesis-loop.sh`, the file the trace points at.

## Procedure
1. **Reproduce**: a command that fails deterministically (a test, a script); if it cannot be reproduced, stop and instrument first.
2. **Hypothesis**: one sentence, falsifiable ("the cache returns stale rows when TTL=0").
3. **Test it** with the smallest change that would prove or refute it (a print, an assert, a bisect); record the result in the loop log.
4. Refuted → next hypothesis; never stack two untested changes. Confirmed → find the root cause, not the symptom.
5. **Fix** at the root; **regression test** (`testing-write-unit-tests`, marker `@tests`); re-run the reproducer.
6. Performance: measure before and after with the same command; report numbers, not adjectives.

## Outputs
The fix, the regression test, and the loop log (hypotheses tried, results) in the task's progress entry.
