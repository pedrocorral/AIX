---
id: aix/stacks/fastapi-backend
name: "FastAPI Backend Standards"
description: "Use when creating or changing a FastAPI backend: routers, Pydantic models, dependencies, services, repositories, settings, migrations, backend tests, Ruff or mypy configuration."
applyTo: "backend/**/*.py,backend/**/*.toml,backend/**/*.yml,backend/**/*.yaml"
optional: true
---
# FastAPI backend standards

## Shape
- One `APIRouter` per domain under `backend/app/<domain>/controllers/`; the app factory in `main.py` includes routers, nothing else lives there.
- Layers: controller (≤ 20 lines: parse, one service call, respond) → service (transaction, authorisation, domain events) → repository port (Protocol) → adapter. No ORM/driver import outside adapters; `aix code graph --gate` enforces the direction.
- Composition root (`composition.py`) builds adapters and services once; controllers receive them through `Depends()`; controllers never import the composition root (an UPWARD edge).

## Contracts
- Request/response models are Pydantic v2 `BaseModel`s in `schemas/`, generated OpenAPI is the API-* contract; field names only from `docs/requirements/data-model/field-dictionary.md`.
- Validation of shape in the schema; business rules in the service raising `core.errors`; one exception handler module maps them to the error envelope.
- Pagination, idempotency keys and versioning per `.aix/meta-docs/architecture/api-design.md`.

## Runtime
- `async def` handlers; blocking work (CPU, sync drivers) goes to a worker or `run_in_threadpool`; never a sync DB call inside an async handler.
- Settings via `pydantic-settings` from the environment; startup validates them; secrets never in code (`aix code security` fails otherwise).
- Structured logging with a request id; no PII in logs.

## Tests and quality gates
- `pytest` + `httpx.AsyncClient` against the app factory for every API-* contract; service tests with memory adapters for every FR acceptance criterion; contract test suite for each repository adapter.
- `ruff` (`C901 max-complexity 10`, `PLR0913 max-args 5`, `N8xx`, `D1xx`), `mypy --strict` on `app/`; `aix code style`, `aix code graph --gate`, `aix code security --gate` in CI.
