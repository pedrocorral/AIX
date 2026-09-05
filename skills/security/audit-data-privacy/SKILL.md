---
name: security-audit-data-privacy
description: Audit PII inventory, minimisation, encryption, retention/deletion, backups/exports and third-party or AI data flows; VUL-DATA rows, new DM-* with personal data, GDPR/privacy questions.
---
# security-audit-data-privacy
Read: register rows for category DATA (`grep -n "VUL-DATA" docs/security/vulnerability-register.md`); `docs/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `persistence/migrations-and-data-lifecycle.md`.

## Checks
- Each `DM-*` states PII fields and retention; no PII collected without an FR.
- TLS everywhere; at-rest encryption for stores/backups per NFR.
- Deletion/anonymisation use case exists and is tested; exports scoped and authorised.
- Third-party/AI data flows documented in NFR-DATA; minimisation applied.
- Test data synthetic; no prod dumps in repo/CI.

## Procedure
1. Locate code by layer (`docs/meta-docs/architecture/project-layout.md`): `docs/requirements/data-model/`, `adapters/`, `infra/` (backups), AI adapters. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: grep for PII field names across logs/exports; review infra encryption settings.
3. Write/extend the negative tests `sec_VUL-DATA-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-DATA-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
