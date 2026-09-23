---
id: TS-EXAMPLE-002
title: Create item — API journey
level: functional
covers: [FR-EXAMPLE-001, API-EXAMPLE-001]
status: planned
automated_in: []
---
# TS-EXAMPLE-002 — POST /v1/items journey
## Preconditions / fixtures
App with `PERSISTENCE_BACKEND=memory`; authenticated client.
## Steps / inputs
1. POST valid body → 201. 2. Same body, same Idempotency-Key → 201 same id. 3. Same name, new key → 409 `ITEM_NAME_TAKEN`. 4. Empty name → 400 with `details[].field == "name"`. 5. No auth → 401.
## Expected results
Per API-EXAMPLE-001 table; error envelope shape per `meta-docs/architecture/api-design.md`.
## Not covered here
- Rule details (case-insensitivity, length) → TS-EXAMPLE-001.
