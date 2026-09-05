---
name: security-audit-infra
description: Audit container hardening, exposed ports, TLS, CI secrets, IaC misconfiguration, edge rate/size limits; VUL-INFRA rows, changes under infra/, Dockerfiles, CI, deployment.
---
# security-audit-infra
Read: register rows for category INFRA (`grep -n "VUL-INFRA" docs/security/vulnerability-register.md`); `docs/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/configuration-and-secrets.md`.

## Checks
- Containers non-root, minimal images, read-only FS where possible; only needed ports exposed.
- TLS termination and internal encryption per NFR; admin endpoints not public.
- CI: secrets masked, least-privilege tokens, pinned actions/images.
- IaC scanned; network policies/security groups restrictive.
- Edge rate limiting and body size limits configured; health endpoints not leaking.

## Procedure
1. Locate code by layer (`docs/meta-docs/architecture/project-layout.md`): `infra/`, Dockerfiles, CI config. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: trivy/checkov/tfsec/hadolint where available.
3. Write/extend the negative tests `sec_VUL-INFRA-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-INFRA-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
