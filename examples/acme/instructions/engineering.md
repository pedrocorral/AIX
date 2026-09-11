---
id: acme/engineering
name: "Engineering Discipline"
description: "Use when implementing, refactoring, testing, reviewing, committing or opening a merge request in any ACME repository: tests with code, small commits, explicit ownership, readable control flow."
always: true
---
# Engineering discipline (always on)
- Tests travel with the code they prove, in the same commit; a commit without tests states why in its message.
- Commits are small and named `type(scope): summary [ids]`; a merge request maps to one task.
- Control flow readable at a glance: guard clauses, no nesting beyond three, functions under the `aix code style` limits.
- Docstrings say what and when, comments say why; no commented-out code.
- Every file has an owner in `CODEOWNERS`; every decision that will be asked about has an ADR.
