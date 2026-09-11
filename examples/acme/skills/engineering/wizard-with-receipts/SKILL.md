---
name: workflow-wizard
class: workflow/wizard
id: "@acme/wizard-with-receipts"
version: 1.0.0
description: Generate an interactive shell wizard that walks a human through the steps only they can perform (accounts, secrets, approvals), checking each step before moving on; use when a procedure needs a person.
---
# @acme/wizard-with-receipts

ACME wizards leave receipts.
1. Steps as functions; each check writes a receipt line (`step, who, when, check output`) to `wizard-receipts.log`.
2. Re-runs skip steps with a receipt whose check still passes.
3. No secrets in receipts; the log is attached to the runbook entry.
