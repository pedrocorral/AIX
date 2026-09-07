---
id: META-ARCH-OBS
title: Errors, logging, observability
---
# Errors, logging, observability

## Exception taxonomy
`DomainError` (base) → `NotFound`, `Conflict`, `ValidationError`, `PermissionDenied`, `RuleViolation`. Adapters raise
`InfrastructureError` (base) → `PersistenceError`, `ExternalServiceError`, `Timeout`. Controllers map domain → HTTP
(`api-design.md`); infrastructure → 5xx with generic message and full context in logs.

## Logging
- Structured (JSON) with: timestamp, level, logger, `trace_id`, `user_id` (hashed if PII rules require), event name, fields.
- Correlation: a `trace_id` created at the edge, propagated to jobs and external calls, returned in the error envelope.
- Never log secrets, tokens, full request bodies, or PII beyond what `NFR-DATA-*` allows. `VUL-LOG-*` rows enforce this.
- Levels: DEBUG local only; INFO business events; WARN recoverable; ERROR needs a human.

## Metrics & tracing
RED metrics per endpoint (rate, errors, duration), queue depth for jobs, DB pool usage; OpenTelemetry where the stack supports it. Health endpoints: `/healthz` (liveness), `/readyz` (dependencies).

## For AI apps
Log prompt/response *hashes* and token counts by default; full content only behind an explicit `NFR-DATA` decision and retention policy.
