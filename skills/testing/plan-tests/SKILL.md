---
name: testing-plan-tests
description: Turn acceptance criteria into TS-* specs at the right level without duplicates; use before writing any test, when a requirement changes, or on "what should we test".
---
# testing-plan-tests (orchestrator)
Read: the FR/API/NFR docs in scope; `docs/tests/test-plan-rules.md`; `docs/meta-docs/testing/strategy.md` + `levels.md` (once per session).

## Procedure
1. For each AC: decide the lowest level that can prove it (decision table in `levels.md`).
2. `grep -rl "<FR-id>" docs/tests` → extend an existing TS if the same AC+level exists; otherwise create `TS-<DOMAIN>-NNN` from `templates/test-spec.md` in `docs/tests/<functional|non-functional>/<domain>/`.
3. Fill *Not covered here* with pointers to sibling TS (this is the anti-duplication contract).
4. Set `tests:` in the FR front-matter; add rows to the folder INDEX.
5. Security/NFR: if the FR adds surface, add `TS-SEC-*` stubs tied to VUL rows; perf/a11y TS for NFRs touched.
6. Summarise to the user as a table AC → TS → level. Hand off to `testing-write-*` skills.
