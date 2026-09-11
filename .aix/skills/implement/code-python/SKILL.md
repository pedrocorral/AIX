---
name: implement-code-python
description: Implement, refactor or review production Python with the repository's layering, typing, error handling, logging and readability limits; use for any Python change outside tests.
---
# implement-code-python

Reading budget: `.aix/meta-docs/stacks/python/tooling.md`, `conventions/readability.md`, `architecture/layering.md`; `aix code style FILE` on the touched file.

## Procedure
1. Place the code in its layer (`architecture-structure-project` decides); no ORM/driver imports outside adapters.
2. Types on every public function; `X | None`, builtin generics, dataclasses for records; no `Any` without a comment.
3. Errors: raise the domain exception from `core/errors`; never swallow; log once at the boundary with ids, never secrets.
4. Functions under the limits (`aix code style FILE:FUNC` after writing): guard clauses, one job, ≤ 5 params.
5. Imports one-directional (`aix code graph --gate`); no sibling-domain import.
6. Docstring on every public function: what it does, when to call it.
7. Run ruff/mypy as configured; tests for the change (`testing-write-unit-tests`).

## Outputs
Code with `@implements` markers, green lint and tests, no style finding over a limit.
