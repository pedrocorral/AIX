---
name: security-audit-dependencies
description: Audit dependencies and supply chain: CVEs, pinning, lockfiles, build scripts, base images; VUL-DEP rows, dependency/lockfile/Dockerfile changes, weekly runs.
---
# security-audit-dependencies
Read: register rows for category DEP (`grep -n "VUL-DEP" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `stacks/*/tooling`.

## Script first (near-zero tokens)
Run `bash <skill-dir>/scripts/run.sh` first: runs pip-audit / npm audit / osv-scanner / trivy where installed and lists lockfiles. Reason only about its output. `<skill-dir>` is this skill's folder (e.g. `.aix/skills/security/audit-dependencies/` or the installed copy).

## Checks
- Lockfiles committed and consistent; versions pinned.
- No known high/critical CVEs (backend, frontend, build tooling, base images).
- No install-time scripts from untrusted packages; registry sources pinned.
- Minimal base images, non-root user.
- New dependencies have a task note and licence check.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): root manifests, `backend/`, `frontend/`, `infra/` Dockerfiles. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: pip-audit / npm audit / osv-scanner / trivy where available; record versions in the report.
3. Write/extend the negative tests `sec_VUL-DEP-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-DEP-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
