---
name: coach-grill-with-docs
description: Interview to sharpen a plan or design and produce the documents it implies (ADRs, glossary rows, requirement drafts) as the answers land; manual only.
disable-model-invocation: true
---
# coach-grill-with-docs

## Procedure
1. `coach-grill` rules for the questions.
2. After every concrete answer that is a decision → `spec-write-adr` draft; a new term → glossary row; a behaviour → `spec-write-requirement` draft.
3. Drafts are marked `status: draft`; the user approves at the end; `aix docs validate`.

## Outputs
The drafts and the assumptions table.
