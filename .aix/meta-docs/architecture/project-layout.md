---
id: META-ARCH-LAYOUT
title: Project layout — predictable paths, minimal scanning
---
# Project layout

The layout is mandatory so that paths are guessable. An agent should be able to name the file it needs
without listing directories. Depth is bounded (≤ 4 levels under `backend/app/`) and every leaf folder is single-purpose.

```
<repo>/
├── AGENTS.md  docs/  skills/  templates/  scripts/           ← kit (see docs/INDEX.md)
├── backend/
│   ├── app/
│   │   ├── main.<ext>              # entry point: create app, mount routers, middleware
│   │   ├── composition.<ext>       # DI / wiring: which adapters implement which ports (ONLY place)
│   │   ├── config/                 # settings loading, env schemas (no secrets in repo)
│   │   ├── core/                   # cross-cutting: auth middleware, errors, logging, pagination, ids
│   │   ├── <domain>/               # one folder per bounded context (auth, users, billing, …)
│   │   │   ├── controllers/        # routers / handlers            (MVC: C)
│   │   │   ├── schemas/            # request/response DTOs         (MVC: V for APIs)
│   │   │   ├── views/              # templates + view-models       (server-rendered only)
│   │   │   ├── services/           # use cases, policies
│   │   │   ├── models/             # domain entities, value objects (MVC: M)
│   │   │   ├── repositories/       # abstract ports (interfaces)
│   │   │   └── adapters/           # <tech>/ implementations: sqlalchemy/, mongo/, memory/, http/
│   │   └── shared_kernel/          # tiny: base entity, result type, domain event base
│   ├── migrations/                 # DB migrations (tool-specific), one folder per backend if several
│   ├── jobs/                       # scheduled / queue workers entry points
│   └── tests/
│       ├── unit/<domain>/          # mirror of app/<domain>, no I/O
│       ├── integration/<domain>/   # real adapters against test DB/containers
│       ├── functional/<journey>/   # API-level user journeys
│       └── fixtures/               # factories, builders, seed data
├── frontend/
│   ├── src/
│   │   ├── api/                    # THE client for API-* (generated or hand-written), one file per domain
│   │   ├── app/                    # routing, providers, layout shell
│   │   ├── features/<domain>/      # components, hooks, state, per bounded context
│   │   │   ├── components/  hooks/  state/  views/(pages)
│   │   ├── shared/                 # design system, utils, i18n
│   │   └── types/                  # DTO types mirroring shared/ schemas
│   └── tests/{unit,component,e2e}/
├── shared/                         # contracts shared by both sides: JSON schemas / OpenAPI / proto, enums, error codes
├── infra/                          # IaC, Docker, CI, deployment manifests, env templates (.env.example)
└── data/ (optional, data-science apps)  raw/ interim/ processed/ (git-ignored), with data/INDEX.md describing sources
```

## Rules
1. **Domain folders mirror `docs/requirements/functional/<domain>/`** — same names, same case. A requirement's home
   folder tells you its code folder.
2. Files ≤ ~400 lines; folders ≤ ~15 files; beyond that split by sub-domain (`billing/invoices/`, `billing/payments/`).
3. One public entry per layer folder (`__init__` / `index`) re-exporting the public surface; agents read that first.
4. Tests mirror source paths one-to-one: `app/users/services/register.py` ⇄ `tests/unit/users/services/test_register.py`.
5. Nothing at repo root except kit files, code roots, and tool config.
6. Language-specific naming (packages, `src/main/java/...`) is mapped in `stacks/<lang>/…`; the *roles* above stay identical.

## Finding a file (agent recipe)
Need "the service that creates invoices" → `backend/app/billing/services/` → `ls` that folder only → open the obvious file.
If the guess fails once, `grep -rln "@implements FR-BILLING" backend/app/billing` — never widen further than the domain.
