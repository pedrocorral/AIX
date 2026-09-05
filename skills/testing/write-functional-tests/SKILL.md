---
name: testing-write-functional-tests
description: Automate functional, e2e and contract TS-*: API journeys, OpenAPI contract checks, browser flows; use after endpoints/pages exist or on end-to-end/API test requests.
---
# testing-write-functional-tests
Read: TS file(s); `API-*` docs; `docs/meta-docs/architecture/api-design.md`.
1. App started via factory with `PERSISTENCE_BACKEND=memory` (fast) and a nightly run against the production backend.
2. One module per journey; steps assert status, envelope shape/codes, and persisted effects through the API (not the DB).
3. Contract tests generated from `shared/openapi.*` (schema validation of real responses).
4. E2E (browser) only for TS marked e2e; keep ≤ 5 minutes total.
5. Marker `@tests TS-…`; update TS status; run in CI stage 4.
