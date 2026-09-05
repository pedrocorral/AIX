---
name: testing-write-integration-tests
description: Automate integration TS-*: repository contract suites on real databases, migrations, adapters, N+1 checks; use on adapter/backend changes or database/integration test requests.
---
# testing-write-integration-tests
Read: TS file(s); `docs/meta-docs/persistence/switching-backends.md` (contract list); `testing/fixtures-and-data.md`.
1. Contract suite `tests/integration/<domain>/test_repository_contract.*` parametrised over every adapter (memory + prod); add cases for new specifications.
2. DB per session via containers (or file/in-memory engine only if dialect-neutral); transaction rollback per test.
3. Migration test: upgrade → downgrade → upgrade on empty DB; N+1 guard with query counting for list endpoints.
4. External services: stub servers from contracts; never the internet.
5. Marker `@tests TS-…`; update TS status; record run command in the task.
