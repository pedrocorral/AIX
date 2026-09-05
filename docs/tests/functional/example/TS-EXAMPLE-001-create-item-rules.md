---
id: TS-EXAMPLE-001
title: Create item — domain rules
level: unit
covers: [FR-EXAMPLE-001]
status: planned
automated_in: []
---
# TS-EXAMPLE-001 — Create item domain rules
## Preconditions / fixtures
Memory `ItemRepository`; fixed clock and id generator; user `u1`.
## Steps / inputs
1. `create_item(u1, "Alpha")` 2. `create_item(u1, "alpha")` 3. `create_item(u1, "")` 4. `create_item(u1, "x"*121)`
## Expected results
- AC1 → step 1 returns item with generated id, `created_at` = fixed clock; repository contains it.
- AC2 → step 2 raises `Conflict(ITEM_NAME_TAKEN)`; repository unchanged.
- AC3 → steps 3–4 raise `ValidationError` on field `name`.
## Not covered here
- HTTP mapping and idempotency → TS-EXAMPLE-002.
