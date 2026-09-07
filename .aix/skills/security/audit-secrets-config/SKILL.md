---
name: security-audit-secrets-config
description: Audit secrets in repo/history/logs/bundles, default credentials, startup validation and key management; VUL-SECRET rows, any config, env, key or credential change.
---
# security-audit-secrets-config
Read: register rows for category SECRET (`grep -n "VUL-SECRET" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/configuration-and-secrets.md`.

## Script first (near-zero tokens)
Run `bash <skill-dir>/scripts/scan.sh` first (gitleaks/detect-secrets if installed, regex fallback; also lists tracked .env files and env keys missing from `.env.example`). `<skill-dir>` is this skill's folder (e.g. `.aix/skills/security/audit-secrets-config/` or the installed copy).

## Checks
- No secrets in tracked files or git history; `.env` ignored; `.env.example` complete.
- Settings object is the only env reader; startup fails on missing/invalid values.
- No default/weak credentials in code, seeds, compose files.
- Frontend bundle contains no secrets; only public config.
- Logs/error envelopes never include secrets.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): `backend/app/config/`, `infra/`, `frontend/` build config, git history. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: detect-secrets/gitleaks/trufflehog if available; `git log -p -S` for known key patterns.
3. Write/extend the negative tests `sec_VUL-SECRET-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-SECRET-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
