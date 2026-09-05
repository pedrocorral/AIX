---
id: META-TEST-STRATEGY
title: Testing strategy
---
# Testing strategy

**Every test proves a `TS-*`; every `TS-*` proves at least one requirement/AC.** Anything else is deleted.

## Pyramid (targets, not dogma)
| Level | Share | Speed | Uses |
|---|---|---|---|
| Unit | ~70 % | ms | memory adapters, no I/O; models, services, pure frontend logic |
| Integration | ~20 % | s | real adapter ↔ real engine; contract suites; API client ↔ mocked server |
| Functional / e2e | ~10 % | s–min | user journeys through the public API/UI |
Plus cross-cutting: contract tests (API-*), security tests (VUL-*), performance (NFR-PERF), accessibility (NFR-A11Y).

## No-duplication rule
An AC is proven at the **lowest level that can prove it**; higher levels prove only integration/journey concerns
and reference (not repeat) the lower TS in "Not covered here". `testing-plan-tests` checks overlap before creating a TS.

## Mapping
- `docs/tests/<level>/<domain>/TS-<DOMAIN>-NNN-*.md` ⇄ `backend/tests/<level>/<domain>/test_*.py` with `@tests TS-…`.
- One TS may map to one test function or a parametrised set; never one test for many TS.
- `aix coverage` reports gaps: `no test spec`, `spec not automated`, `no code`.

## CI gates (define in `infra/ci/`)
1. lint + type check + import-layer check; 2. unit; 3. integration (containers); 4. functional; 5. security scans
(dependency, secrets, SAST); 6. `validate.py` + coverage matrix has no new gaps for `must` requirements.

## Flakiness policy
Quarantine folder `tests/quarantine/` with a task to fix within the sprint; a quarantined test cannot prove a TS (`status: planned` again).
