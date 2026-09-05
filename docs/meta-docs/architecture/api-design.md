---
id: META-ARCH-API
title: API design conventions
---
# API design

Defaults (override via ADR): REST + JSON, OpenAPI as the machine contract in `shared/openapi.yaml`, versioned by URL prefix.

## Conventions
- Resources are plural nouns: `/v1/users/{id}/orders`. Verbs only for non-CRUD actions: `POST /v1/orders/{id}:cancel`.
- Every endpoint: `API-*` doc → OpenAPI → code. Drift is checked by skill `review-doc-drift-check`.
- Pagination: cursor-based (`?cursor=&limit=`), response `{ "items": [], "next_cursor": null }`.
- Filtering/sorting: explicit whitelisted params; never pass raw query language to storage.
- Idempotency: `Idempotency-Key` header on POST that creates resources; PUT/DELETE idempotent by design.
- Time: ISO-8601 UTC strings; money: integer minor units + currency; IDs: opaque strings (UUID v7 preferred).
- Versioning: additive changes in place; breaking → new major prefix; deprecate with `Sunset` header + ADR.

## Error envelope (mandatory, all endpoints)
```json
{ "error": { "code": "USER_NOT_FOUND", "message": "human readable", "details": [{"field": "email", "issue": "invalid"}], "trace_id": "…" } }
```
- `code` values are an enum in `shared/error-codes.*` and referenced by the frontend for i18n.
- HTTP mapping: 400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict/idempotency, 422 domain rule, 429 rate, 5xx never leaks internals.

## Security defaults
Auth on every route unless `API-*` says `auth: none`; rate limiting at the edge; request size limits; CORS allowlist;
no sensitive data in URLs; `VUL-WEB-*` and `VUL-AUTHZ-*` rows apply to every new endpoint.

## Non-REST
GraphQL: same envelope semantics in `errors[].extensions.code`; depth/complexity limits. Events: schema in `shared/events/`, versioned, consumer-driven contract tests (`testing/levels.md`).
