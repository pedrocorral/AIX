---
name: workflow-triage
description: Move incoming issues and external pull requests through triage: categorise, verify reproducibility, ask the missing questions, label, and route to a task or a rejection; use on "triage the inbox".
disable-model-invocation: true
---
# workflow-triage

Reading budget: the issue text; the labels in `references/labels.md`; nothing else until step 3.

## Procedure
1. Categorise: bug / feature / question / security (route security to `security-threat-model` immediately, privately).
2. Verify: a bug needs a reproduction; a feature needs the requirement it changes (`core-find-doc`). Missing → one precise question back, label `needs-info`.
3. Duplicate check: search the road-map and closed items by nouns; link and close duplicates.
4. Accepted → `aix task new` in the right bucket with the ids; rejected → a two-line reason citing the requirement or ADR.
5. Never fix inside triage; never merge an external PR without `review-code-review`.

## Outputs
Labelled issues, tasks created, a triage log line per item.
