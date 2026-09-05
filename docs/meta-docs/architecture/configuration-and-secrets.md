---
id: META-ARCH-CONFIG
title: Configuration and secrets
---
# Configuration and secrets
- 12-factor: config from environment; a typed settings object in `backend/app/config/` is the only reader of env vars.
- Layering: defaults in code → `.env` (local, git-ignored) → environment → secret manager. `infra/.env.example` lists every variable with a comment, no values.
- Secrets never in repo, logs, error messages, or frontend bundles. Rotation documented in `infra/`.
- Persistence backend is selected by config (`PERSISTENCE_BACKEND=postgres|sqlite|memory|mongo`) and wired in `composition` — see `../persistence/switching-backends.md`.
- Feature flags: typed, defaulted, read through the settings object; every flag has an FR or task that will remove it.
- Validation at startup: fail fast with the list of missing/invalid variables.
- Register rows `VUL-SECRET-*` cover this file's concerns; skill `security-audit-secrets-config` audits it.
