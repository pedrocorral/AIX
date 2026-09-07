---
id: META-SEC-PROCESS
title: Security audit process
---
# Security audit process

## Register lifecycle (`docs/security/vulnerability-register.md`)
| Status | Meaning | Who sets |
|---|---|---|
| `expected` | Theoretically present; assumed valid until audited | threat model / seeding |
| `unverified` | Audit ran but could not confirm or rule out (missing access/tooling) — follow-up task required | audit skill |
| `confirmed` | Audit found it present; no control yet | audit skill |
| `mitigated` | Control implemented (`@mitigates`) but not yet proven by a negative test | implementer |
| `addressed` | Control + evidence: negative test (`sec_VUL-…`) green and audit report | audit skill only |
| `accepted` | Residual risk accepted by the user, with ADR naming owner and review condition | user via ADR |
| `not-applicable` | Component absent (e.g. no file uploads); re-evaluated when surface changes | threat model, with justification |

Every row: `| VUL id | description | component | status | audit skill | last audit ref |`. The audit report carries the detail (asset, threat, impact, likelihood, control, verification, evidence, residual risk).

## When to audit
- **Per task**: before closing, run the audit skills named in the task's `security:` list.
- **Per feature**: `security-audit` orchestrator picks skills by touched categories.
- **Scheduled**: dependencies weekly; full register quarterly; on any auth/persistence change.

## Evidence
An audit produces `docs/security/audits/AUDIT-<date>-<category>.md` (template `.aix/templates/audit-report.md`) with findings,
status transitions, and the tests/commits that prove mitigations. Without a report, no status change.

## Category → skill map
| Category | Skill |
|---|---|
| INJ (SQL/NoSQL/OS/template/LDAP) | `security-audit-injection` |
| AUTHN (identity, sessions, passwords, MFA, tokens) | `security-audit-authn-authz` |
| AUTHZ (IDOR, privilege escalation, tenancy) | `security-audit-authn-authz` |
| INPUT (validation, deserialisation, uploads, size) | `security-audit-input-validation` |
| SECRET (config, keys, env, logs) | `security-audit-secrets-config` |
| DEP (supply chain, CVEs, lockfiles) | `security-audit-dependencies` |
| WEB (XSS, CSRF, CORS, headers, clickjacking) | `security-audit-web-xss-csrf` |
| DATA (PII, encryption at rest/transit, retention) | `security-audit-data-privacy` |
| LOG (leakage, monitoring, alerting) | `security-audit-logging-monitoring` |
| AI (prompt injection, exfiltration, tool abuse) | `security-audit-ai-llm` |
| INFRA (containers, IaC, network, CI) | `security-audit-infra` |
