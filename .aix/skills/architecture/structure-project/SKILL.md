---
name: architecture-structure-project
description: Create or fix the folder layout (backend/frontend/shared/infra, test mirrors) per project-layout.md; use when scaffolding, when files sit in the wrong layer, or on "where should this go".
---
# architecture-structure-project
Read: `.aix/meta-docs/architecture/project-layout.md`; `.aix/meta-docs/stacks/<lang>/…` mapping section.

## Procedure
1. For each domain in the glossary, create `backend/app/<domain>/{controllers,schemas,services,models,repositories,adapters/memory}/` (+ `views/` if server-rendered), each with an `__init__`/`index` file exporting the public surface (empty is fine) and a 1-line README only at the domain level.
2. `backend/app/{main,composition,config,core,shared_kernel}` skeletons; `backend/tests/{unit,integration,functional,fixtures}/<domain>` mirrors.
3. `frontend/src/{api,app,features/<domain>,shared,types}` and `frontend/tests/`.
4. `shared/` with `error-codes.*` and OpenAPI placeholder; `infra/` with `.env.example`, `README.md` (run commands), CI skeleton.
5. Add lint config enforcing the dependency rule (`stacks/*/tooling`).
6. Report the tree (only new folders) to the user. Never move existing files without listing the moves and getting confirmation.
