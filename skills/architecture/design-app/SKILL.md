---
name: architecture-design-app
description: Design a full application architecture from requirements (domains, MVC layers, contract, persistence, tests, security) and record ADRs; use for new projects, multi-domain features, or "how should we structure this".
---
# architecture-design-app

Reading order (required, ≈ 900 lines total): `docs/meta-docs/architecture/INDEX.md` and all files it lists; `docs/meta-docs/persistence/abstraction-layer.md`; `docs/meta-docs/testing/strategy.md`; `docs/meta-docs/security/audit-process.md`; the chosen `docs/meta-docs/stacks/<lang>/`. Inputs: `docs/requirements/product/*`, existing FR/NFR.

## Procedure
1. **Domains**: derive bounded contexts from requirements/personas; propose `<DOMAIN>` codes → glossary. One folder each in `functional/`, `api/`, `backend/app/`.
2. **Shape**: API+SPA / server-rendered / data-science / AI-supported (or mix) → ADR with rationale (`spec-write-adr`).
3. **Layering per domain**: list aggregates (DM-*), services (use cases from FRs), controllers (API-*), adapters needed. Produce `docs/requirements/decisions/ADR-000N-architecture-overview.md` containing a table domain → aggregates → use cases → endpoints.
4. **Persistence plan**: run `architecture-design-persistence`.
5. **Cross-cutting**: auth model, config, errors/observability, jobs/events — one ADR each only when deviating from meta-doc defaults.
6. **Test & security plan**: for each domain, TS families and VUL rows expected (`security-threat-model`).
7. **Layout**: run `architecture-structure-project` to scaffold folders.
8. Present to the user a ≤ 25-line summary; ask for approval of ADRs; then create `pending/next` tasks per domain (`core-roadmap-task`).

## Outputs
ADRs, glossary domains, DM/API stubs, scaffolded folders, tasks.
