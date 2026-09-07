---
name: security-audit-logging-monitoring
description: Audit sensitive data in logs, trace ids, audit trails for privileged actions and alerting; VUL-LOG rows, logging or error-handling changes, monitoring questions.
---
# security-audit-logging-monitoring
Read: register rows for category LOG (`grep -n "VUL-LOG" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/errors-logging-observability.md`.

## Checks
- Structured logs; no secrets/tokens/PII beyond policy; request bodies not logged by default.
- `trace_id` propagated and in error envelopes; 5xx never leak internals.
- Audit events for login, permission changes, data export/deletion, admin actions, tool calls (AI).
- Alerts defined for auth failures spikes, 5xx rate, queue backlog.
- Log retention and access controlled.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): `backend/app/core/` (logging, errors), `infra/` observability config. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: grep loggers for sensitive field names; trigger an error and inspect the log/envelope.
3. Write/extend the negative tests `sec_VUL-LOG-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-LOG-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
