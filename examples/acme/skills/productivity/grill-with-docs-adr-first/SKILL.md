---
name: coach-grill-with-docs
class: coach/grill-with-docs
id: "@acme/grill-with-docs-adr-first"
version: 1.0.0
description: Interview to sharpen a plan or design and produce the documents it implies (ADRs, glossary rows, requirement drafts) as the answers land; manual only.
disable-model-invocation: true
---
# @acme/grill-with-docs-adr-first

ACME grilling that produces documents starts every answer as an ADR line.
1. Each decided answer → an ADR draft immediately (`spec-write-adr`), status draft.
2. Terms → glossary; behaviours → requirement drafts.
3. The user approves the set at the end; `aix docs validate`.
