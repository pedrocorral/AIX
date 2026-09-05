# requirements/ — GROUND TRUTH for this application
Read this when: implementing, testing, reviewing or discussing behaviour. Skip when: never (at least the domain you touch).

Conflicts between these docs and code are resolved by the user via `meta-docs/workflow/conflict-resolution.md`. Agents never edit an `approved` requirement without an ADR.

| Path | What | Read when |
|---|---|---|
| `product/` | Vision, personas, glossary (defines `<DOMAIN>` codes), scope | Onboarding; naming anything |
| `functional/` | `FR-<DOMAIN>-NNN` grouped by domain folder (mirrors `backend/app/<domain>/`) | Before any feature work |
| `non-functional/` | `NFR-<CAT>-NNN`: performance, security, accessibility, observability, data, ops, UX | Design; release |
| `data-model/` | `DM-<Entity>` aggregates, fields, invariants, retention | Persistence & API work |
| `api/` | `API-<DOMAIN>-NNN` contracts (source for OpenAPI in `shared/`) | Any endpoint / client work |
| `decisions/` | `ADR-NNNN` architecture decisions incl. stack choice and conflict rulings | Design; whenever "why?" |
| `how-to-write-requirements.md` | Quality bar for requirement text | Writing/reviewing FRs |
