---
name: architecture-design-persistence
description: Design aggregates, repository ports, specifications, unit of work, backends and migrations; use for new entities, choosing/switching a database, ORM, storage, repository questions.
---
# architecture-design-persistence
Read: `docs/meta-docs/persistence/abstraction-layer.md`, `orm-guidelines.md`, `switching-backends.md`; the relevant `DM-*` docs; stack notes in `docs/meta-docs/stacks/<lang>/`.

## Procedure
1. Aggregates: for each `DM-*` decide root vs child; one repository per root; list specifications needed from FR ACs (e.g. `ByOwnerAndName`).
2. Ports: write the interface signatures (method list) in the design note; read-model ports for reporting queries.
3. UoW: one per domain (or shared); events collected for outbox.
4. Backends: memory (mandatory) + production default (+ alternates) per ADR-0001; mapping strategy (imperative vs separate entities) → ADR if not already decided.
5. Migrations tool and folder; index plan tied to specifications.
6. Contract test suite outline (`switching-backends.md` list) → TS entries via `testing-plan-tests` (`TS-<DOMAIN>-…` level integration).
7. Output a design note as ADR (if decisions) or as the task's plan (if only applying defaults). Then `implement-orm-model` / `implement-repository` do the code.
