---
id: META-PERSIST-SWITCH
title: Switching persistence backends
---
# Switching persistence backends

## Selection by configuration
`PERSISTENCE_BACKEND` (per domain overrides allowed: `PERSISTENCE_BACKEND_USERS=mongo`). `composition` reads it and
binds `UnitOfWork` + repositories to the matching adapter package. Nothing else changes.

## Adding a backend (checklist, skill `implement-repository`)
1. Create `adapters/<tech>/` with `uow.<ext>`, `<aggregate>_repository.<ext>`, `mapper.<ext>`.
2. Implement every port method; unsupported operations raise `NotSupported` with a reason (and an ADR if permanent).
3. Run the **contract test suite** `backend/tests/integration/<domain>/test_repository_contract.*` parametrised by backend. Green = done.
4. Add migrations/bootstrap for the backend under `backend/migrations/<tech>/`.
5. Document in `infra/` how to run it locally (container, env vars). Add `VUL-DATA-*` rows if new exposure.

## Contract test suite (definition of the port)
Covers: add/get round-trip with all field types; update via UoW; remove; list with each specification; pagination
stability; uniqueness conflicts → `Conflict`; rollback discards changes; concurrent update → optimistic lock error
(if the aggregate declares `version`); domain events collected and cleared on commit.

## Backend notes
| Backend | Gotchas to encode in adapter |
|---|---|
| SQL (Postgres/MySQL/SQLite) | transactions, dialect differences, JSON columns, migrations tool |
| Document (Mongo, Firestore) | no cross-document transactions by default → aggregate = document; specification → query translation |
| Key-value / DynamoDB | single-table design belongs in adapter; specifications limited → read-model ports |
| Files (JSON/Parquet/CSV) | atomic writes (temp + rename), locking, good for data-science apps and prototypes |
| Memory | must behave like a real store (copy on read/write) to catch aliasing bugs |
| Remote API as storage | idempotency, retries, timeouts, circuit breaker decorators |
