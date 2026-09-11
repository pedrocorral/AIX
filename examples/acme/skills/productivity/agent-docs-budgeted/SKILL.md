---
name: spec-write-for-agents
class: spec/write-for-agents
id: "@acme/agent-docs-budgeted"
version: 1.0.0
description: Write or edit documents meant for agents (AGENTS.md sections, instruction blocks, INDEX rows, hand-off notes) so they are short, navigable and unambiguous; use when touching any agent-facing text.
---
# @acme/agent-docs-budgeted

ACME agent documents carry a token budget in their front matter (`budget: 400`) and are rejected by review when over it.
1. State the budget; count it (`wc -w` × 1.3).
2. Imperatives, tables, pointers to INDEX rows; no prose paragraphs longer than three lines.
