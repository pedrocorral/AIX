---
name: security-audit-authn-authz
description: Audit passwords, sessions, tokens, MFA, brute-force protection, IDOR, tenant isolation and mass assignment; VUL-AUTHN/AUTHZ rows, login/session/permission code, roles, access control.
---
# security-audit-authn-authz
Read: register rows for categories AUTHN and AUTHZ (`grep -n "VUL-AUTHN\|VUL-AUTHZ" docs/security/vulnerability-register.md`); `docs/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/layering.md` (policy in services).

## Checks
- KDF for passwords; constant-time compare; lockout/rate limit on auth endpoints.
- Tokens random, short-lived, revocable; refresh rotation; secure cookie flags; no tokens in URLs/logs.
- MFA available/required for privileged roles per FR/NFR.
- Every service use case checks `can(user, action, resource)` on the object, not just the route.
- Repository queries filter by tenant/owner centrally.
- Update schemas allowlist fields; no role/owner fields writable by clients.

## Procedure
1. Locate code by layer (`docs/meta-docs/architecture/project-layout.md`): `backend/app/auth/`, every `services/` file for object checks, `schemas/` for mass assignment. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: grep for endpoints with `{id}` lacking service-level checks; auth negative tests (wrong user, wrong tenant, expired token).
3. Write/extend the negative tests `sec_VUL-AUTHN-NNN / sec_VUL-AUTHZ-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-AUTHN-NNN or VUL-AUTHZ-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
