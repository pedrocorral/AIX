---
name: spec-write-for-agents
description: Write or edit documents meant for agents (AGENTS.md sections, instruction blocks, INDEX rows, hand-off notes) so they are short, navigable and unambiguous; use when touching any agent-facing text.
---
# spec-write-for-agents

Reading budget: `.aix/meta-docs/conventions/token-economy.md`, `document-format.md`.

## Procedure
1. **One purpose per document**; the first line says what it is and when to read it (`read_when:` in front matter).
2. **Budget**: every always-on text costs every turn. AGENTS.md sections stay ≤ 40 lines; anything longer becomes a scoped instruction (`applyTo`) or a linked file.
3. **Imperatives, no hedging**: "Run X, then Y" not "you may want to consider". Numbered steps; tables for enumerations.
4. **Navigation over content**: point to the INDEX and the file, never paste the file.
5. **Stable anchors**: keep H2 names; agents grep them.
6. Check: `aix docs validate`; read the text once as if you had 3k tokens and no memory.

## Outputs
The edited text; a one-line note in the task log if a budget was exceeded and why.
