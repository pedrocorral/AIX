---
name: security-audit-web-xss-csrf
description: Audit XSS, CSRF, CORS, security headers, open redirects and cookie flags; VUL-WEB rows, templates/components rendering user content, cookie or redirect code.
---
# security-audit-web-xss-csrf
Read: register rows for category WEB (`grep -n "VUL-WEB" docs/security/vulnerability-register.md`); `docs/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/frontend-backend-separation.md`.

## Checks
- Autoescape on; any raw HTML rendering sanitised with an allowlist; no `innerHTML`/dangerouslySetInnerHTML with user data.
- State-changing requests protected by CSRF token or SameSite + custom header, per stack ADR.
- CORS allowlist explicit; no wildcard with credentials.
- Headers: CSP without unsafe-inline where possible, HSTS, X-Content-Type-Options, frame-ancestors.
- Redirect targets allowlisted; cookies Secure/HttpOnly/SameSite.

## Procedure
1. Locate code by layer (`docs/meta-docs/architecture/project-layout.md`): `frontend/src/`, `backend/app/*/views/`, `core/` middleware, `infra/` edge config. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: header checks via HTTP client; XSS payload tests on rendering paths.
3. Write/extend the negative tests `sec_VUL-WEB-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-WEB-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
