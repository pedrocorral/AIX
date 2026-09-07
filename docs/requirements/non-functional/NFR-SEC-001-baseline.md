---
id: NFR-SEC-001
title: Secure coding baseline applies to all components
type: non-functional
status: approved
priority: must
related: []
tests: [TS-SEC-001]
---
# NFR-SEC-001 — Secure coding baseline
## Statement
Every component SHALL comply with `.aix/meta-docs/security/secure-coding-baseline.md`; every `VUL-*` row on an internet-facing component SHALL be `addressed`, `accepted` or `not-applicable` before release.
## Acceptance criteria
- AC1: Release gate fails if any such row is `expected`, `unverified`, `confirmed` or `mitigated`.
