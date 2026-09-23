---
id: NFR-OBS-001
title: Observability baseline
type: non-functional
status: approved
priority: must
related: []
tests: [TS-OBS-001]
---
# NFR-OBS-001 — Observability baseline
## Statement
Every request and job SHALL emit structured logs carrying a `trace_id`; the service SHALL expose liveness and readiness endpoints; error responses SHALL include the `trace_id`.
## Acceptance criteria
- AC1: A request with header `X-Trace-Id` is logged with that id and returns it in any error envelope.
- AC2: `/healthz` returns 200 without dependencies; `/readyz` returns 503 when persistence is unavailable.
