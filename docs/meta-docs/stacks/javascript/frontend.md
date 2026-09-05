---
id: META-STACK-JS-FE
title: Frontend (React / Vue / Svelte)
---
# Frontend
- Layout per `../../architecture/project-layout.md`: `src/api/` (only place that talks HTTP, typed from `shared/`), `src/features/<domain>/`, `src/shared/` (design system), `src/app/` (routing/providers).
- State: server state via a query cache (React Query / TanStack / Pinia equivalents) keyed by `API-*` resources; UI state local; global state minimal and typed.
- Validation mirrors backend schemas from `shared/` (zod/valibot generated from OpenAPI where possible); backend remains authoritative.
- Security: no secrets; tokens in httpOnly cookies or memory (ADR); sanitise any HTML rendering; CSP-compatible (no inline scripts).
- Testing: Vitest/Jest unit, Testing Library component tests with `api/` mocked (msw), Playwright e2e for journeys; `@tests TS-…` in comments.
- Accessibility: semantic HTML, keyboard paths, axe checks per view (`NFR-A11Y-*`).
- Tooling: TypeScript strict, ESLint + Prettier, `npm audit` in CI, dependency lockfile.
