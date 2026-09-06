---
id: META-STACK-PY-TOOLING
title: Python tooling
---
# Python tooling (defaults; override by ADR)
- Env & packaging: `uv` (or poetry); `pyproject.toml` single source; lockfile committed.
- Lint/format: `ruff` (lint + format); types: `mypy` (strict on inner layers); imports: `import-linter` contracts enforcing the dependency rule (`layering.md`) — contracts file lives in `backend/importlinter.toml`.
- Tests: `pytest` + `pytest-asyncio` + `hypothesis` for value objects; `testcontainers` for integration; `pytest-cov` with thresholds per layer.
- Security: `pip-audit`, `bandit`, `detect-secrets` in pre-commit and CI.
- Migrations: Alembic (SQLAlchemy) or Django migrations.
- Pre-commit: ruff, mypy (changed files), detect-secrets, `aix docs validate`.
- Run everything through `Makefile` targets or `uv run` so agents don't guess commands; document them in `infra/README.md`.

## Readability limits in the linter (same numbers as `aix code style`, `conventions/readability.md`)
- ruff: `C901` (mccabe, `max-complexity = 10`), `PLR0913` (too many arguments, `max-args = 5`), `PLR0912`/`PLR0915`
  (branches/statements), `N8xx` naming, `D1xx` missing docstrings; `flake8-cognitive-complexity` for cognitive ≤ 15.
- radon `cc` / `mi` for a code-base-wide view; `aix code style` for the ranked, cross-language report.
