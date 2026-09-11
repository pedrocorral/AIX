---
name: debug-diagnose
class: debug/diagnose
id: "@acme/diagnose-bisect-first"
version: 1.0.0
description: Diagnosis loop for hard bugs and performance regressions: reproduce, hypothesise, test one hypothesis at a time, fix the root cause, add the regression test; use on "diagnose / debug / why is this slow".
---
# @acme/diagnose-bisect-first

ACME diagnoses regressions by bisecting before hypothesising.
1. Reproduce with one command; `git bisect run <command>` when the bug is a regression.
2. The culprit commit narrows the hypotheses to one file; then the hypothesis loop (`scripts/loop.sh`) with one change at a time.
3. Fix the root cause; regression test; re-run bisect's command on HEAD.
4. Performance: `hyperfine` or the project's benchmark before and after; numbers in the task.
