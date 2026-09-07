---
name: implement-repository
description: Add or change repository ports, specifications, unit of work and adapters (memory, SQL, document, file, HTTP), or add a new backend; use for any data-access, query, find-by, list/filter or switch-database work.
---
# implement-repository
Read: `.aix/meta-docs/persistence/abstraction-layer.md`, `switching-backends.md`; the domain's `repositories/` port file.

## Procedure
1. Port: add method or specification class to `repositories/`; domain types only in signatures.
2. Memory adapter first (reference semantics: copy on read/write).
3. Production adapter(s): translate specification → query in `adapters/<tech>/`; parameterised only (`@mitigates VUL-INJ-001`); tenancy filter applied centrally (`@mitigates VUL-AUTHZ-002`).
4. UoW: transaction + event collection; no commits inside repositories.
5. Contract test suite: extend `tests/integration/<domain>/test_repository_contract.*` parametrised over all adapters; new TS via `testing-plan-tests` if a new behaviour.
6. Wiring in `composition` keyed by `PERSISTENCE_BACKEND`.
7. New backend → follow the checklist in `switching-backends.md` fully, add infra docs and `VUL-DATA-*` rows.
