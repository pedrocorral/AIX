---
id: META-PERSIST-LIFECYCLE
title: Migrations and data lifecycle
---
# Migrations and data lifecycle
- Every schema change = migration + `DM-*` doc update in the same task. Migrations are forward-only in prod; down-migrations exist for dev.
- Expand/contract for zero-downtime: add → backfill → switch code → remove, across releases.
- Seeds: `backend/tests/fixtures/` for tests; `infra/seed/` for demo/dev; never seed prod from repo.
- Retention & deletion: each `DM-*` states retention and whether it contains PII; deletion/anonymisation is a service use case with a TS. `VUL-DATA-*` rows track exposure.
- Backups/restore are an NFR (`NFR-DATA-*`) with a tested restore procedure in `infra/`.
- Data-science datasets: versioned (DVC/lakeFS or content hashes) and described in `data/INDEX.md`.
