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
