---
id: META-ARCH-JOBS
title: Background jobs and events
---
# Background jobs and events
- Anything > ~500 ms or not needed for the response becomes a job (`backend/jobs/`) triggered by a domain event.
- Outbox pattern: the service writes the event in the same transaction as the state change; a relay publishes it. Never publish from inside the request after commit "by hand".
- Jobs are idempotent, retried with backoff, dead-lettered after N attempts, and observable (`errors-logging-observability.md`).
- Schedulers own no business logic: they call a service method.
- Data-science pipelines follow the same rule: each stage is an idempotent job with declared inputs/outputs (`stacks/python/data-science-app.md`).
