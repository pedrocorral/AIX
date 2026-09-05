---
id: META-PERSIST-ORM
title: ORM guidelines
---
# ORM guidelines

An ORM is an adapter detail. Use it for mapping, transactions and migrations — not as your domain model.

## Mapping strategy (pick one per project, record ADR)
| Strategy | When | Cost |
|---|---|---|
| **Imperative / classical mapping** (domain classes stay plain; ORM maps them in the adapter) | Default. Clean domain, easy memory adapter | Extra mapping code |
| Separate ORM entities + explicit mapper functions | ORM cannot map plain classes (many ORMs) | Two class hierarchies, mapper per aggregate |
| Domain = ORM entities (Active Record style) | Tiny apps / prototypes only (ADR must say "prototype") | Couples everything; hard to test without DB |

## Sessions & transactions
- One session/connection per unit of work; created by the UoW adapter, never global.
- Repositories never commit or flush explicitly except where required for ID generation (prefer domain-generated IDs).
- Read-only use cases use a read-only session/transaction if supported.

## Loading & performance
- Default to eager-loading the aggregate; forbid lazy loads after the UoW closes (raise in tests).
- Detect N+1 in integration tests (query counting fixture) — one TS per list endpoint.
- Bulk operations bypass the ORM object layer via the adapter's bulk methods, still behind the port.
- Indexes are declared in migrations with a comment referencing the query/spec that needs them.

## Schema
- Migrations are the only way to change schema; models never `create_all` outside tests.
- Nullable columns need a reason; enums stored as strings; timestamps UTC; soft-delete only if an FR requires it.
- Optimistic concurrency (`version` column) on aggregates that can be edited concurrently (FR must state it).

## Testing
Unit tests use the memory adapter. Integration tests run the ORM adapter against a real engine (SQLite in-memory is acceptable **only** for dialect-neutral code; otherwise a container of the production engine) and execute the contract suite.
