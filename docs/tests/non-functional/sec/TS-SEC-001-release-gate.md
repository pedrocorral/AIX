---
id: TS-SEC-001
title: Vulnerability register release gate
level: security
covers: [NFR-SEC-001]
status: planned
automated_in: []
---
# TS-SEC-001
Run `aix validate` and a check that no `VUL-*` row with component tagged `internet-facing` is `expected`/`unverified`/`confirmed`/`mitigated`. Fails the release pipeline otherwise.
