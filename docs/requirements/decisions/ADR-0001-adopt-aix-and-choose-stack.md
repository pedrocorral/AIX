---
id: ADR-0001
title: Adopt AIX and choose the technology stack
status: proposed
date: 2026-09-04
supersedes: []
affects: [.aix/meta-docs/stacks, backend, frontend]
---
# ADR-0001 — Adopt AIX and choose the stack
## Context
New project. Documentation is the ground truth; agents do most implementation; token budget matters.
## Options considered
Stack: _(e.g. Python/FastAPI + SQLAlchemy/Postgres + React; or …)_. Persistence default and alternates. Frontend style (SPA vs server-rendered).
## Decision
_(fill in; then set `status: accepted`)_
- Language/framework:
- Persistence backends (default / test / alternates):
- Frontend:
- Mapping strategy for ORM (see `.aix/meta-docs/persistence/orm-guidelines.md`):
## Consequences
- Read `.aix/meta-docs/stacks/<lang>/` for all implementation work.
- Initialise `backend/`, `frontend/` per `.aix/meta-docs/architecture/project-layout.md`.
