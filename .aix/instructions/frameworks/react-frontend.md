---
id: aix/frameworks/react-frontend
name: "React Frontend Standards"
description: "Use when creating or changing a React and TypeScript frontend: components, hooks, routes, data fetching, state, generated API types, Vitest or Playwright tests, ESLint, Vite or TypeScript configuration."
applyTo: "frontend/**/*.{ts,tsx,js,jsx,css,json},shared/**/*.{ts,tsx,js,json,css},eslint.config.*,tsconfig*.json,vite.config.*,vitest.config.*,playwright.config.*"
optional: true
---
# React frontend standards

## Shape
- Feature folders `frontend/src/features/<domain>/` with `components/`, `hooks/`, `api/`, `routes/`; shared primitives in `frontend/src/ui/`; nothing imports across features except through `shared/` (`aix code graph --gate`).
- Components render props and raise events; every side effect, fetch or store access lives in a hook. A component over 60 lines or with more than one reason to change is split (`aix code style`).
- Server state through TanStack Query (keys per resource, invalidation on mutation); client state local first, a store only for state shared across routes.

## Contracts and types
- API types generated from the backend's OpenAPI into `shared/contracts/` (or `frontend/src/api/generated/`); no hand-written request shapes.
- `strict: true`, `noUncheckedIndexedAccess: true`; `unknown` plus narrowing instead of `any`; discriminated unions for view states (`idle | loading | error | ready`).

## Runtime
- Routing with lazy route modules; error boundaries per route; suspense for data.
- Accessibility is a requirement: semantic elements, labels, keyboard paths, `axe` in CI; translations through the i18n layer, never string literals in JSX for user text.
- Optional chaining and nullish coalescing (ES2020 target); no `var`.

## Tests and quality gates
- Vitest + Testing Library for hooks and components (behaviour, not implementation); Playwright for TS-* functional journeys with evidence (`testing-validate-ui`); MSW for API mocking, generated types as the single source.
- ESLint (`complexity 10`, `max-depth 4`, `max-params 5`, `max-lines-per-function 60`, `react-hooks/*`, `jsx-a11y/*`), Prettier, `tsc --noEmit`; `aix code style`, `aix code graph --gate` in CI.
