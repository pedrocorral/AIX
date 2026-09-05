Frontend (SPA, server-rendered views or dashboards). Contract rules: `docs/meta-docs/architecture/frontend-backend-separation.md`.
Allowed deps: `shared/` types and the `src/api/` client. Forbidden: direct HTTP outside `src/api/`; any import from `backend/`; secrets.
