---
id: META-ARCH-LAYERS
title: Layering and the dependency rule
---
# Layering

Special case of `modularity.md`: the layers are the levels of an acyclic graph whose edges point inward.

```
 controllers  ──►  services  ──►  domain models
      │               │                ▲
   schemas         repositories        │
  (DTOs in/out)   (interfaces)         │
                      ▲                │
             adapters (ORM / files / API clients)  ◄─ implement interfaces, depend inward
```

| Layer | Folder (per domain) | Contains | May import |
|---|---|---|---|
| Controllers | `controllers/` | routers/handlers, request parsing, response mapping | services, schemas |
| Schemas / DTOs | `schemas/` | request/response/validation models | nothing from other layers (plain types) |
| Services | `services/` | use cases, transactions (unit of work), orchestration, policy | models, repository *interfaces*, other services |
| Domain models | `models/` | entities, value objects, invariants, domain events | stdlib / pure libs only |
| Repository interfaces | `repositories/` | abstract ports (`UserRepository`) | models |
| Adapters | `adapters/<tech>/` | ORM mappings, SQL, file stores, external API clients | models, repository interfaces, tech libs |

## Rules
- **Dependency rule**: imports point inward only. An adapter may import a model; a model never imports an adapter. Enforce with an import-linter (see `stacks/*/tooling`).
- **One transaction per use case**: services open/commit the unit of work; repositories never commit.
- **DTOs at the edges**: controllers convert schema → service input (primitives/DTOs); services return domain objects or result DTOs; controllers serialise.
- **No layer skipping**: controller → repository is forbidden; use a service even if trivial.
- **Cross-domain calls** go service → service through the other domain's public service interface, never through its repositories.
- Errors: domain raises domain exceptions; controllers map them to API errors (`errors-logging-observability.md`).

## Where does X go? (quick table)
| X | Layer |
|---|---|
| "Password must be ≥ 12 chars" | model (value object) |
| "Send welcome email after signup" | service (use case) + adapter (mailer) |
| "Return 404 when user missing" | controller (maps `NotFound` domain error) |
| "Only admins can delete" | service (policy), enforced before repository call |
| "Cache products for 60 s" | adapter/decorator around repository, configured in composition root |
| Dependency wiring | `backend/app/composition.py` (or DI container) — the **only** place adapters are chosen |
