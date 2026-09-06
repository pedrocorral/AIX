---
name: implement-feature
description: Implement an approved requirement across layers (model → repository → service → controller/UI) with @implements markers; entry point for any implement/build/add/code request after spec and tests are planned.
---
# implement-feature (orchestrator)
Inputs: task file (`context_files`), FR/API/DM docs listed there, `docs/meta-docs/architecture/layering.md`, stack doc. Budget: those only + the target domain folder.

## Procedure
1. Map each AC to the layer that owns it (`layering.md` "Where does X go?"). Write this mapping in the task plan.
2. Domain model changes → `implement-orm-model` (domain classes + mapping + migration).
3. New/changed queries → `implement-repository` (port method + memory adapter + production adapter + contract test).
4. Use case → service in `services/` (transaction boundary, authorisation check, domain events). Marker `@implements FR-…`.
5. Boundary → `implement-endpoint` (schema, controller, error mapping, OpenAPI) and/or `implement-ui`.
6. Wiring in `composition` only.
7. Run unit tests for the domain; then hand over to `testing-write-*` for remaining TS; then `security-audit`.

## Rules
Smallest change that satisfies the ACs; no speculative generality; no new dependency without noting it in the task (and `security-audit-dependencies`); no behaviour beyond the requirement (if needed → `spec-write-requirement` first).

Before hand-off: `aix code style <changed files>` must show no function over a limit (`conventions/readability.md`); `aix code graph --gate` no cycle or upward dependency.
