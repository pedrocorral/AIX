---
id: FR-EXAMPLE-001
title: Create an item
type: functional
status: approved
priority: must
domain: EXAMPLE
depends_on: []
related: [API-EXAMPLE-001, DM-Item]
tests: [TS-EXAMPLE-001, TS-EXAMPLE-002]
---
# FR-EXAMPLE-001 — Create an item

## Statement
The system SHALL allow an authenticated user to create an item with a unique, non-empty name (≤ 120 chars).

## Rationale
Items are the core object users manage; creation is the first journey.

## Acceptance criteria
- AC1: Given a valid name, when the user submits, then an item is persisted with a generated id and `created_at`, and returned.
- AC2: Given a name already used by this user, when submitted, then the request fails with error code `ITEM_NAME_TAKEN` and nothing is persisted.
- AC3: Given an empty or > 120-char name, when submitted, then a validation error identifies the `name` field.

## Constraints & edge cases
- Name uniqueness is per user, case-insensitive.

## Out of scope
- Editing and deleting items (FR-EXAMPLE-002/003).
