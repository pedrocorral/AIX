---
name: workflow-wizard
description: Generate an interactive shell wizard that walks a human through the steps only they can perform (accounts, secrets, approvals), checking each step before moving on; use when a procedure needs a person.
---
# workflow-wizard

Reading budget: the runbook or the task listing the manual steps.

## Procedure
1. List the steps a person must do; for each, the check that proves it was done (a file exists, a command succeeds, a URL answers).
2. Generate `scripts/wizard-<name>.sh`: bash, `set -euo pipefail`, one function per step, prints the instruction, waits for Enter, runs the check, repeats on failure, never stores a secret.
3. Idempotent: re-running skips steps whose check passes.
4. Test it on a machine where nothing is done yet; then record it in `docs/operations/`.

## Outputs
The wizard script and its runbook entry.
