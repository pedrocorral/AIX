---
name: implement-tdd
class: implement/tdd
id: "@acme/tdd-red-green"
version: 1.0.0
description: Test-driven development: build features or fix bugs test-first, one red test, one green change, one commit per cycle; use when the user says test-first or TDD.
---
# @acme/tdd-red-green

Test-driven development, ACME cadence: one red test, one green change, one commit, no exceptions.
1. Name the behaviour as a test title first; the test must fail for the right reason (run it, read the message).
2. Smallest change to green; no refactor while red.
3. Refactor under green; `aix code style FILE:FUNC` keeps it under the limits.
4. Commit per cycle with the TS id; a cycle longer than 20 minutes means the step is too big: split.
