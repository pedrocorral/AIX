---
name: spec-plain-language
class: spec/plain-language
id: "@acme/plain-language-glossary-locked"
version: 1.0.0
description: Write, edit or review technical documentation in plain, controlled language (one idea per sentence, active voice, defined terms, no ambiguity); use for READMEs, guides, runbooks and any Markdown for humans.
---
# @acme/plain-language-glossary-locked

ACME writing is glossary-locked: a term not in the glossary may not appear in a document.
1. Run the glossary check (`grep` of capitalised terms against the glossary) before editing.
2. One idea per sentence, ≤ 18 words, active voice, present tense.
3. Missing terms are added to the glossary first, then used.
