---
name: security-audit-injection
description: Audit and fix SQL/NoSQL, OS command, template, path-traversal and LDAP injection in adapters, services and file handling; VUL-INJ rows, raw queries, shell or template rendering.
---
# security-audit-injection
Read: register rows for category INJ (`grep -n "VUL-INJ" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `persistence/abstraction-layer.md`.

## Script first (near-zero tokens)
Run `bash <skill-dir>/scripts/scan.sh [paths]` first: it prints only suspicious file:line hits. Reason about the hits; do not read files that produced none. `<skill-dir>` is this skill's folder (e.g. `.aix/skills/security/audit-injection/` or the installed copy).

## Checks
- No string-built queries; specifications translate to parameterised queries/ORM expressions.
- No `shell=True`/string commands with user input; allowlisted arguments only.
- Templates with autoescape; no `eval`/dynamic template from input.
- File paths normalised and confined to a base directory; uploads never executed.
- NoSQL: operators (`$where`, regex) never built from input.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): `backend/app/*/adapters/`, `core/`, any file/subprocess helpers. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: SAST (bandit/semgrep/CodeQL if present), grep for `execute(f"`, `format(`, `subprocess`, `os.system`, `render_template_string`.
3. Write/extend the negative tests `sec_VUL-INJ-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-INJ-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
