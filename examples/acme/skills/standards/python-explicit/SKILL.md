---
name: implement-code-python
class: implement/code-python
id: "@acme/python-explicit"
version: 1.0.0
description: Implement, refactor or review production Python with the repository's layering, typing, error handling, logging and readability limits; use for any Python change outside tests.
---
# @acme/python-explicit

ACME Python: explicit over clever.
1. No decorators except the framework's; no metaclasses; no `**kwargs` in public functions.
2. Types everywhere; `Result`-style returns for expected failures, exceptions only for bugs.
3. Logging through the project logger with ids; no prints.
4. Ruff with the ACME ruleset (`ruff.toml` in the repo); `aix code style` limits are the ceiling, not the target.
