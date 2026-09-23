---
id: DM-FIELD-DICTIONARY
title: Canonical field dictionary
status: approved
---
# Canonical field dictionary

**The only field names that exist.** Every name used in a `DM-*`, an `API-*`, `shared/` schemas, ORM mappings and DTOs must appear here with the same spelling and type. No synonyms (`customer_id` vs `client_id`), no per-layer renames. Add a row before using a name; `aix docs validate` warns on API/DM field names missing from this table.

Conventions: `snake_case`; ids end in `_id`; timestamps end in `_at` (UTC ISO-8601); booleans start with `is_`/`has_`; money as `<name>_minor` + `<name>_currency`; counts end in `_count`.

| Field | Type | Meaning | Owner (DM) | Also used by (API/others) |
|---|---|---|---|---|
| id | uuid v7 | primary identifier of any aggregate | all | all |
| owner_id | uuid | user that owns the resource | DM-Item | API-EXAMPLE-001 |
| name | string(120) | human label of an item | DM-Item | API-EXAMPLE-001 |
| created_at | timestamp | creation time, UTC | all | all |
| updated_at | timestamp | last modification time, UTC | all | — |
| trace_id | string | request correlation id | — | error envelope |
| next_cursor | string \| null | pagination cursor | — | all list endpoints |
