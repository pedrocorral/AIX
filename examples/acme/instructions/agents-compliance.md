---
id: acme/agents/compliance
description: "ACME compliance rules every agent follows: data classes, licences, retention."
block: true
order: 60
section: "Compliance (ACME)"
---
- Personal data fields carry `pii: true` in their DM-* row; no PII in logs, fixtures or prompts.
- Dependencies: MIT, BSD, Apache-2.0 only; anything else needs an ADR with legal sign-off.
- Retention: every stored personal record has a deletion path tested by a TS-*.
