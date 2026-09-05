---
name: implement-ui
description: Implement frontend features (components, pages, hooks, state, API client) or server-rendered views and dashboards (Streamlit/Dash/Gradio) respecting the frontend/backend contract.
---
# implement-ui
Read: FR + `API-*` docs; `docs/meta-docs/architecture/frontend-backend-separation.md`; `docs/meta-docs/stacks/javascript/frontend.md` (or server-rendered section of the stack doc; dashboards: `stacks/python/data-science-app.md`).

## Procedure
1. Field names verbatim from `docs/requirements/data-model/field-dictionary.md` (types in `frontend/src/types/` mirror it). API client: add/extend `frontend/src/api/<domain>.*` from `API-*` (typed from `shared/`); components never call HTTP directly.
2. Feature folder `features/<domain>/`: components (presentational), hooks (data), state (minimal), views/pages (composition). `@implements FR-…` on the page/hook that realises it.
3. Validation mirrors backend schema for UX only; show backend `error.code` via i18n map.
4. Security: escape/sanitise any HTML rendering (`@mitigates VUL-WEB-001`), no secrets, CSRF per stack.
5. Accessibility basics (labels, keyboard, contrast) — note `NFR-A11Y` TS if present.
6. Tests: unit/component with the API module mocked; e2e only for the journey TS.
7. Server-rendered: view-model in `views/`, template with autoescape; no logic in templates.
