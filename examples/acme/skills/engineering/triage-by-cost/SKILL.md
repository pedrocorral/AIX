---
name: workflow-triage
class: workflow/triage
id: "@acme/triage-by-cost"
version: 1.0.0
description: Move incoming issues and external pull requests through triage: categorise, verify reproducibility, ask the missing questions, label, and route to a task or a rejection; use on "triage the inbox".
disable-model-invocation: true
---
# @acme/triage-by-cost

ACME triage puts a cost on every item before a category.
1. Cost of not doing it (who is blocked, how often) in one line; cost of doing it (size, risk) in one line.
2. Security items skip the queue (`security-threat-model`, private).
3. Accept when the first cost exceeds the second; reject with both lines cited; `needs-info` when either is unknown.
4. Labels from `references/labels.md` of the kit's triage skill; tasks via `aix task new`.
