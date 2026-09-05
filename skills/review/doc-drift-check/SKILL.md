---
name: review-doc-drift-check
description: Detect drift between docs and reality (API vs OpenAPI vs controllers, DM vs migrations, statuses vs markers, INDEX vs folders, STATE vs git); use before closing features/releases or when docs seem stale.
---
# review-doc-drift-check
1. `aix validate` and `aix coverage`; read only the error/warning lines and the matrix rows in scope.
2. API drift: for each `API-*` in scope compare path/method/status codes with OpenAPI and the controller (`grep -rn "@implements API-…"`).
3. DM drift: fields in `DM-*` vs model class vs latest migration.
4. Status drift: FR `implemented` without `@implements`; TS `automated` without a test containing `@tests`; register `addressed` without an audit report.
5. Road-map drift: task status vs folder; STATE.md `updated` older than last commit touching `going-on/`.
6. Report a table (doc / reality / fix). Fixes to docs that change *meaning* go through `core-conflict-resolution`; mechanical fixes (INDEX rows, statuses backed by evidence) apply directly.
