---
id: DM-Item
title: Item
status: approved
related: [FR-EXAMPLE-001, API-EXAMPLE-001]
---
# DM-Item
## Fields
| Field | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid v7 | pk, domain-generated | |
| owner_id | uuid | fk User, indexed | tenancy boundary |
| name | string(120) | non-empty, unique(owner_id, lower(name)) | |
| created_at | timestamp UTC | | |
## Invariants
- `name` trimmed, 1–120 chars. Uniqueness per owner enforced in service via repository specification `ByOwnerAndName`, and by DB constraint.
## Lifecycle
- Created → (edited) → deleted (hard delete; PII: none). Retention: n/a.
