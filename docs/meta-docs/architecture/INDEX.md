# architecture/ — how an application built with AIX is shaped
Read this when: designing a new app/feature or deciding where code belongs. Skip when: editing inside a known layer.

| Path | What | Read when |
|---|---|---|
| `mvc.md` | MVC as used here: what Model/View/Controller mean for APIs, SPAs, server-rendered and data/AI apps | Any design; onboarding |
| `frontend-backend-separation.md` | The contract boundary, what never crosses it, who owns validation/state/auth | Designing UI ↔ API; any "should this go in the frontend?" |
| `layering.md` | Controller → Service → Repository → Model; DTOs; dependency rule | Placing any new class/function |
| `project-layout.md` | Mandatory folder tree (`backend/ frontend/ shared/ infra/`), nesting rules, where tests live | Creating files; finding files |
| `api-design.md` | REST/GraphQL/events conventions, versioning, error envelope, pagination, idempotency | Writing `API-*` contracts or endpoints |
| `configuration-and-secrets.md` | 12-factor config, env layering, secret handling, feature flags | Any config/env/secret |
| `errors-logging-observability.md` | Exception taxonomy, structured logs, correlation IDs, metrics, tracing | Error handling; NFR-OBS |
| `background-jobs-and-events.md` | Async work, queues, schedulers, outbox pattern | Anything not request/response |
