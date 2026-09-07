---
id: META-SEC-BASELINE
title: Secure coding baseline
---
# Secure coding baseline (all stacks)
1. Parameterised queries / specification objects only; no string-built queries (`@mitigates VUL-INJ-*`).
2. Validate at the boundary with schemas (allowlists, lengths, types); reject, don't sanitise, unless output-encoding.
3. Output-encode per context (HTML, attribute, JS, URL); templating with autoescape on.
4. Authorise in the **service** for every use case: object-level (`can(user, action, resource)`), not only route-level.
5. Passwords: modern KDF (argon2id/bcrypt/scrypt), constant-time compare; tokens random ≥ 128 bits; short-lived access + revocable refresh.
6. Secrets from environment/secret manager only; never logged; `.env.example` documents keys.
7. Dependencies pinned via lockfile; automated CVE scanning in CI; minimal base images; run as non-root.
8. Security headers (CSP, HSTS, X-Content-Type-Options, frame-ancestors), strict CORS, CSRF tokens or same-site cookies.
9. Uploads: size limit, type by content sniffing, store outside web root / object storage, never execute.
10. Errors never expose stack traces or internals; logs structured with `trace_id`, PII minimised.
11. Rate limits and request size limits at the edge; timeouts on every outbound call.
12. AI features: treat model output as untrusted input; tools least-privileged; see `ai-llm-security.md`.
