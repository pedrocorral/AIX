---
id: acme/frontend-vue
name: "Vue Frontend Standards"
description: "Use when creating or changing the Vue frontend: components, composables, Pinia stores, routes, generated contract types, Vitest or Playwright tests, ESLint or Vite configuration."
applyTo: "frontend/**/*.{ts,vue,js,json,css},packages/contracts/**"
---
# Vue frontend standards
- Components render props and emit events; data fetching in composables; state in Pinia stores per domain.
- Types come from `packages/contracts`; a component never declares an API shape.
- Routing per feature folder `features/<domain>/`; lazy routes; guards in one module.
- Tests: Vitest for composables and stores, Playwright for TS-* journeys with evidence (`testing-validate-ui`).
- Accessibility: every interactive element keyboard-reachable; axe check in CI.
