---
id: API-EXAMPLE-001
title: POST /v1/items
status: approved
implements: [FR-EXAMPLE-001]
auth: required
---
# API-EXAMPLE-001 — POST /v1/items
## Request
- Body: `{ "name": string }` (see DM-Item)
## Responses
| Code | When | Body |
|---|---|---|
| 201 | created | `{ "id", "name", "created_at" }` |
| 400 | validation | error envelope, `details[].field = "name"` |
| 409 | name taken | error envelope, `code = ITEM_NAME_TAKEN` |
## Rules
- Idempotency-Key supported; same key + same body → 201 with the same resource.
