---
name: implement-orm-model
description: Implement or change a domain model plus its ORM mapping and migration without coupling domain to ORM; use on DM-* changes or "add a field/table/model/entity".
---
# implement-orm-model
Read: the `DM-*` doc; `docs/meta-docs/persistence/orm-guidelines.md`; mapping strategy ADR; stack doc.

## Procedure
1. Field names verbatim from `docs/requirements/data-model/field-dictionary.md`. `models/<entity>.<ext>`: plain domain class, invariants enforced in constructor/methods (from DM "Invariants"), domain-generated id, `@implements DM-<Entity>`.
2. Mapping in `adapters/<tech>/mapper.<ext>` (imperative mapping or separate storage entity + `to_domain/from_domain`).
3. Migration: add/alter table, constraints, indexes (comment which specification uses each index). Never `create_all`.
4. Update memory adapter if fields affect specifications.
5. Tests: unit for invariants (`@tests TS-…`), integration round-trip in the contract suite, migration up/down.
6. Update `DM-*` doc if the design changed (via ADR if approved).
