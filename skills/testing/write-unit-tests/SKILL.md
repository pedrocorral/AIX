---
name: testing-write-unit-tests
description: Automate unit-level TS-* (models, services with memory adapters, serialisers, frontend logic) with @tests markers; use when a unit TS is planned or unit tests are requested.
---
# testing-write-unit-tests
Read: the TS file(s); `docs/meta-docs/testing/fixtures-and-data.md`; stack test tooling.
1. Test file mirrors the source path (`tests/unit/<domain>/<layer>/test_<module>`), one test per TS (parametrise for multiple inputs).
2. Fixtures: builders from `tests/fixtures/`, memory adapters, fixed clock/ids.
3. Name `test_<function>_<scenario>_<expected>`; first line/comment `@tests TS-…`; assert on domain outcomes and repository state, not on implementation details.
4. Run only this domain's unit tests. On pass: TS `status: automated`, `automated_in:` filled. On fail because the requirement is wrong → `core-conflict-resolution`.
