---
id: aix/languages/python
name: "Python Conventions"
description: "Use when writing or changing Python: version floor, toolchain (ruff, mypy, pytest), errors, logging, dependencies. Decisions, not a tutorial."
applyTo: "**/*.py,**/pyproject.toml"
optional: true
---
# Python conventions

Decisions this codebase has made. Replace this file in your organisation layer to state yours.

## Version and features
- Floor: the `requires-python` in `pyproject.toml` (`aix code style` reads it). Below 3.10 is not supported by the kit's advice.
- Use what the floor allows and nothing older: `match`, `X | None`, `dataclass(slots=True)`, `typing.Self`, `tomllib`, `ExceptionGroup`, f-strings everywhere. `aix code style --modernise` lists what is still written the old way.
- No `from __future__ import annotations` once the floor is 3.10+ unless a runtime tool needs string annotations.

## Toolchain (must pass before "done")
- Format and lint: `ruff format`, `ruff check` with `C901` (10), `PLR0913` (5), `N`, `D1`, `B`, `UP`, `S` (bandit rules) enabled.
- Types: `mypy --strict` on the package; `Any` only at the boundary with untyped libraries, with a comment saying which one.
- Tests: `pytest`; one test module per source module, `tests/` mirrors the package; `pytest-cov` threshold set in `pyproject.toml`.
- Packaging: `pyproject.toml` only (no `setup.py`, no `requirements.txt` as the source of truth); a lockfile (`uv.lock` or `poetry.lock`) committed.

## Errors and logging
- Raise the project's exception types from `core.errors`; never bare `except:` or `except Exception` without re-raise or logging with `exc_info`.
- `logging` (or `structlog`) with a module logger; no `print` outside CLIs; no secrets or PII in messages.
- Return values, not `None`-on-failure; `Optional` returns are for absence, not errors.

## Structure
- Modules under 400 lines, functions under 60 (`aix code style`); imports at the top, absolute, no star.
- Side effects only under `if __name__ == "__main__":` or an explicit `main()`.
- Data crossing a boundary is a `dataclass`, `TypedDict` or Pydantic model, never a bare dict.
