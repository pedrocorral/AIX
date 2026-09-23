---
id: TEST-RULES
title: Test plan rules
---
# Test plan rules
1. A TS proves specific ACs of specific requirements (`covers:`). Empty `covers` is invalid.
2. Before creating a TS, `grep -rl "<FR-id>" docs/tests` — extend an existing TS if the same AC at the same level is already there.
3. One TS per AC per level is the norm; combine only when ACs are inseparable.
4. `level:` chosen with `.aix/meta-docs/testing/levels.md`; the "Not covered here" section names the TS that proves the rest.
5. File: `docs/tests/<functional|non-functional>/<domain>/TS-<DOMAIN>-NNN-<title>.md`; numbering per domain, never reused.
6. When automated, set `status: automated` and `automated_in:`; the test code carries `@tests TS-…`.
7. Security tests are `TS-SEC-*` referencing `VUL-*` in the body; evals `TS-AI-*`.
