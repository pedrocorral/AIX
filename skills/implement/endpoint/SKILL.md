---
name: implement-endpoint
description: Implement an endpoint from its API-* contract: schemas, thin controller, error mapping, auth, OpenAPI sync; use on "add endpoint/route/API/handler" or controller changes.
---
# implement-endpoint
Read: the `API-*` doc; `docs/meta-docs/architecture/api-design.md`; `layering.md`; stack controller mapping.

## Procedure
1. Schemas in `schemas/`: field names taken verbatim from `docs/requirements/data-model/field-dictionary.md` (grep it; add a row via `spec-write-requirement` if missing); request (strict, size limits, allowlist fields — `@mitigates VUL-INPUT-001`, `VUL-AUTHZ-003`) and response DTOs.
2. Controller ≤ 30 lines: auth dependency, parse → call one service method → map result; `@implements API-…`.
3. Error mapping via `core/errors` (domain → envelope codes from `shared/error-codes`).
4. Authorisation is in the service; controller only authenticates (`@mitigates VUL-AUTHZ-001` lives in the service).
5. Idempotency/pagination per api-design; rate limit annotation if applicable.
6. Update `shared/openapi.*`; run `review-doc-drift-check` for this endpoint.
7. Functional TS → `testing-write-functional-tests`.
