---
id: META-STACK-PY-WEB
title: Python web apps
---
# Python web apps

## Framework mapping (choose via ADR)
| Kit role | FastAPI | Flask | Django |
|---|---|---|---|
| `controllers/` | `APIRouter` modules | Blueprints | `views.py` (thin) + `urls.py` |
| `schemas/` | Pydantic models | marshmallow/pydantic | DRF serializers / pydantic |
| `services/` | plain classes/functions with injected ports | same | same (not in `views`) |
| `models/` | plain dataclasses / pydantic-free domain classes | same | plain classes; Django ORM models live in `adapters/django/` |
| `repositories/` | `Protocol`/ABC ports | same | same |
| `adapters/sqlalchemy/` | SQLAlchemy 2.x imperative mapping + Alembic | same | `adapters/django/` models + migrations |
| `composition.py` | `Depends()` providers built from settings | app factory | `apps.py` ready() / explicit container |
| `core/` | middleware, exception handlers, auth deps | same | middleware |

## Rules
- App factory pattern (`create_app(settings)`), no import-time side effects; settings via `pydantic-settings`.
- Async: FastAPI handlers async only if every awaited dependency is async; never mix sync DB drivers into async handlers (use threadpool or async driver consistently). Flask/Django: sync unless ADR.
- Domain models: `@dataclass(frozen=True)` for value objects, `@dataclass` for entities with methods enforcing invariants; no pydantic in `models/` (pydantic is for `schemas/`).
- Exception handlers in `core/errors.py` map `DomainError` subclasses → error envelope.
- Templates (server-rendered): Jinja2 with autoescape; view-models are dicts/dataclasses built in `views/`.
- Type hints everywhere; `mypy --strict` for `models/`, `services/`, `repositories/`.

## Minimal example (FastAPI, users domain)
```
backend/app/users/controllers/users_router.py   # @implements API-USERS-001
backend/app/users/schemas/user_schemas.py
backend/app/users/services/register_user.py     # @implements FR-USERS-001
backend/app/users/models/user.py                # @implements DM-User
backend/app/users/repositories/user_repository.py  (Protocol)
backend/app/users/adapters/memory/user_repository.py
backend/app/users/adapters/sqlalchemy/{mapper.py,user_repository.py,uow.py}
backend/tests/unit/users/services/test_register_user.py  # @tests TS-USERS-001
```
