---
id: META-SEC-CATEGORIES
title: Threat categories and baseline vulnerabilities
---
# Threat categories and baseline vulnerabilities

The baseline below seeds every new project's register (`docs/security/vulnerability-register.md`) as `expected`.
Skill `security-threat-model` adds project-specific rows and marks `not-applicable` with justification.

| Category | Baseline VULs (assumed present until audited) |
|---|---|
| INJ | SQL/NoSQL injection via specifications or raw queries; OS command injection; template injection; path traversal |
| AUTHN | Weak password policy; missing brute-force protection; insecure session/token storage; missing MFA for privileged roles; token not revocable |
| AUTHZ | IDOR on any `{id}` endpoint; missing object-level checks in services; tenant data leakage; privilege escalation through mass assignment |
| INPUT | Unbounded payload sizes; unsafe deserialisation; unvalidated file uploads (type, size, content); unicode/encoding tricks |
| SECRET | Secrets in repo/history; secrets in logs; default credentials; weak key management |
| DEP | Unpinned dependencies; known CVEs; no lockfile integrity; untrusted build scripts |
| WEB | XSS (stored/reflected/DOM); CSRF on state-changing requests; permissive CORS; missing security headers; open redirects |
| DATA | PII stored without need/retention; no encryption in transit/at rest; backups unencrypted; deletion not honoured |
| LOG | Sensitive data in logs; no audit trail for privileged actions; no alerting on auth anomalies |
| AI | Prompt injection via user content/tools/RAG documents; system-prompt leakage; data exfiltration through tool calls; over-privileged tools; unbounded cost |
| INFRA | Containers running as root; exposed admin ports; secrets in CI logs; missing TLS; no rate limiting at edge |

Reference frameworks: OWASP Top 10 (web, API, LLM), CWE Top 25. Map each VUL row to its reference in the description when useful.
