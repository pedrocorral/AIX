---
name: architecture-domain-model
description: Build and sharpen the project's domain model: terms, entities, relationships, invariants and bounded contexts, recorded in the glossary and DM-* docs; use when terminology is fuzzy or a new domain appears.
---
# architecture-domain-model

Reading budget: `docs/requirements/product/glossary.md`, `docs/requirements/data-model/INDEX.md`, `.aix/templates/data-model.md`.

## Procedure
1. Collect the nouns the users and the code use; for each, one definition, one owner context. Conflicting meanings → two terms.
2. Entities vs values vs events; identity and lifecycle for entities; invariants as sentences ("an Order has ≥ 1 line").
3. Bounded contexts: group terms that change together; name the relationships (customer/supplier, shared kernel) between contexts.
4. Write DM-* docs (`spec-write-requirement` for the data-model type), field names only from the field dictionary.
5. Decisions that were hard get an ADR (`spec-write-adr`).
6. `aix docs validate`.

## Outputs
Glossary rows, DM-* docs, context map (a table in `docs/requirements/product/`), ADRs for the contested choices.
