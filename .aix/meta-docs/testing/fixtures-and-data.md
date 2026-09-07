---
id: META-TEST-FIXTURES
title: Fixtures and test data
---
# Fixtures and test data
- **Builders/factories** per aggregate in `backend/tests/fixtures/` (`a_user().with_role("admin").build()`); defaults valid, overrides explicit.
- **Determinism**: inject clock, id generator and random source through the composition root; tests fix them.
- **Memory adapters** are the default fixture for unit tests; they are also used to run functional tests fast (`PERSISTENCE_BACKEND=memory`).
- **Databases**: one container per test session, one transaction (rolled back) or schema per test; never share state between tests.
- **External services**: stubs recorded from `API-*`-like contracts; never call the internet in CI.
- **Sensitive data**: synthetic only; never copy production data into tests (`VUL-DATA-*`).
- **Golden files** for serialisers/reports, updated deliberately with a task reference.
