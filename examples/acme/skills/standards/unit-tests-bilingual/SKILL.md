---
name: testing-write-unit-tests
class: testing/write-unit-tests
id: "@acme/unit-tests-bilingual"
version: 1.0.0
description: Automate unit-level TS-* (models, services with memory adapters, serialisers, frontend logic) with @tests markers; use when a unit TS is planned or unit tests are requested.
---
# @acme/unit-tests-bilingual

ACME unit tests, Python and TypeScript alike: fixtures over mocks, properties over examples where a rule exists.
1. One test module per TS; names read as sentences (`test_order_rejects_empty_lines`).
2. Python: pytest, fixtures in conftest, hypothesis strategies for value types; TypeScript: vitest, factories in `test/factories`, fast-check for rules.
3. Memory adapters for ports; no network, no clock (inject time).
4. `@tests TS-…` markers; TS status automated; coverage of the acceptance criteria, not of lines.
