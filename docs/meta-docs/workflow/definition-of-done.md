---
id: META-WORKFLOW-DOD
title: Definition of done
---
# Definition of done

## Task
- All `requirements:` in the task are `status: implemented`; code has `@implements` markers.
- All `tests:` in the task are `status: automated`, green in CI, with `@tests` markers.
- `security:` entries either `addressed` (audit report exists) or explicitly `accepted` by the user (ADR).
- Every new/changed doc is in its folder INDEX; `aix validate` passes; `aix coverage` regenerated.
  `aix validate` **fails** when a status outruns the code: FR/NFR/API `implemented`/`verified` without `@implements`, TS `automated` without `@tests`, VUL `mitigated` without `@mitigates`. Markers are not optional.
- Task file has a final progress-log entry; moved to `completed/YYYY-MM/`; `STATE.md` updated.

## Feature (group of tasks)
- Functional test specs for the user journey exist and pass.
- API contracts (`API-*`) match implementation (skill `review-doc-drift-check` run).
- NFRs touched (performance, accessibility, observability) have measurements recorded in the TS.

## Release
- `docs/conflicts/open/` is empty.
- Coverage matrix has no `no test spec` / `no code` gaps for `priority: must` requirements.
- Security register: no `expected` on internet-facing components; dependency audit < 7 days old.
- `CHANGELOG.md` entry lists FR/ADR IDs.
