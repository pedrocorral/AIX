---
id: META-ARCH-MVC
title: MVC as applied in AIX
---
# MVC in AIX

MVC is used as an *organising principle*, not a framework feature. The three roles are:

| Role | Responsibility | Never does |
|---|---|---|
| **Model** | Domain entities, invariants, business rules, domain services. Persistence-agnostic. | Know about HTTP, UI, ORM sessions, JSON |
| **View** | Everything that renders for a consumer: HTML templates, SPA components, JSON serialisers (response schemas), CLI output | Business decisions, direct DB access |
| **Controller** | Translate an inbound request into calls on services/models and pick a view. Thin. | Contain business logic; call repositories directly (goes via services) |

## Mapping to modern app shapes
| App shape | Model | View | Controller |
|---|---|---|---|
| JSON API + SPA | `backend/app/<domain>/models` + `services` | `schemas` (response DTOs) + `frontend/` | `controllers` (routers/handlers) |
| Server-rendered | same | `templates/` + `schemas` | `controllers` |
| Data-science app | pipelines & feature models in `models`/`services` | notebooks (exploration only), dashboards, reports | job entry points, API |
| AI-supported app | prompts/chains are *services*; LLM clients are *adapters* (see `stacks/python/ai-app.md`) | chat UI, streaming schemas | controllers + orchestration services |

## Rules
1. **Dependency direction**: View → Controller → Service → Model. Model depends on nothing outward.
   Repositories are adapters injected into services (see `layering.md`, `../persistence/abstraction-layer.md`).
2. A **Model** must be constructible and testable without a database or web server.
3. **Controllers** are ≤ ~30 lines each: parse/validate input (schema), call one service method, map result → view/response.
4. **Views** never mutate state. Serialisers are pure functions of domain objects.
5. Cross-cutting (auth, logging, tracing, rate limits) is middleware, not controller code.

## Anti-patterns to reject in review
Fat controllers; models importing ORM session/HTTP types; templates/components calling APIs that aren't in `API-*`;
services returning ORM entities to controllers (return domain objects or DTOs).
