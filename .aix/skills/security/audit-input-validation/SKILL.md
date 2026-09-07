---
name: security-audit-input-validation
description: Audit schema strictness, size limits, deserialisation, uploads and encoding edge cases at the boundary; VUL-INPUT rows, new request schemas, upload/import features.
---
# security-audit-input-validation
Read: register rows for category INPUT (`grep -n "VUL-INPUT" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `architecture/api-design.md`.

## Checks
- Every controller parses through a strict schema (unknown fields rejected, types, lengths, ranges).
- Body/query/header size limits; pagination limit capped.
- No unsafe deserialisation (pickle/yaml.load/unsafe JSON revivers).
- Uploads: size, content-sniffed type, filename sanitised, stored outside web root, virus scan if NFR.
- Unicode normalisation and null bytes handled; numbers parsed safely.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): `backend/app/*/schemas/`, `controllers/`, `core/`. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: fuzz a sample of endpoints with oversized/odd payloads; schema linters.
3. Write/extend the negative tests `sec_VUL-INPUT-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-INPUT-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
