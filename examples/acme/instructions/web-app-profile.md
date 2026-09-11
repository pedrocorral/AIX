---
id: acme/web-app-profile
name: "ACME Web Application Profile"
description: "Use when designing, scaffolding or making cross-cutting changes to an ACME web application: Django backend, Vue frontend, shared contracts package, quality gates and deployment boundaries."
---
# ACME web application profile
Default for a new ACME web repository unless an ADR says otherwise.
- **Stack**: Django 5 + DRF backend under `backend/`; Vue 3 + Pinia + Vite frontend under `frontend/`; typed contracts generated from OpenAPI into `packages/contracts/`.
- **Boundaries**: the frontend talks to the backend only through `packages/contracts`; no direct model import across the boundary.
- **Auth**: session cookies for the app, tokens only for machine clients; both issued by the backend.
- **Quality gates** (all in CI): `aix docs validate`, `aix code graph --gate`, `aix code security --gate`, ruff + mypy, eslint + tsc, pytest, vitest, Playwright for TS-* functional specs.
- **Deployment**: one container per side; migrations run by the backend job before rollout; feature flags in config, never in code branches.
