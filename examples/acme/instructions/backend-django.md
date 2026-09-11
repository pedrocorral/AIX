---
id: acme/backend-django
name: "Django Backend Standards"
description: "Use when creating or changing Django or DRF backend code: models, serializers, views, services, migrations, settings, backend tests, ruff or mypy configuration."
applyTo: "backend/**/*.py,backend/**/*.toml,backend/**/*.yml,backend/**/*.yaml"
---
# Django backend standards
- Layers: `views/` (DRF views, ≤ 20 lines) → `services/` (transactions, authorisation) → `repositories/` (ORM access) → `models/`. No ORM query outside repositories.
- Serializers validate shape only; business rules live in services and raise `core.errors`.
- One app per domain; settings split by environment; secrets from the environment only (`aix code security` enforces).
- Migrations reviewed like code: reversible, no data migration inside a schema migration.
- Tests: pytest-django, factories, a request test per API-* contract, a service test per FR acceptance criterion.
