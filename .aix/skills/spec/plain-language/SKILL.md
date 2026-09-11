---
name: spec-plain-language
description: Write, edit or review technical documentation in plain, controlled language (one idea per sentence, active voice, defined terms, no ambiguity); use for READMEs, guides, runbooks and any Markdown for humans.
---
# spec-plain-language

Reading budget: the document; `docs/requirements/product/glossary.md` when it exists.

## Rules (a controlled style, in the spirit of Simplified Technical English)
- One instruction per sentence; ≤ 20 words; active voice; present tense.
- Use the glossary term, never a synonym; define a term the first time or link the glossary.
- Approved verbs for actions (run, open, set, check); no "should", "might", "basically".
- Lists for sequences, tables for options; no nested parentheses.
- Every procedure states the expected result of each step.

## Procedure
1. Identify the audience and the task the reader is doing; delete anything else.
2. Rewrite sentence by sentence against the rules; keep code and commands verbatim.
3. Check each term against the glossary; add missing ones.
4. Read once aloud; anything that needs a second reading is rewritten.

## Outputs
The document; new glossary rows if any.
