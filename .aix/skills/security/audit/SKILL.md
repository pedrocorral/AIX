---
name: security-audit
description: Orchestrate a security audit for a task, component or project: picks security-audit-* skills by category, writes audit reports, updates the register; use before closing tasks with attack surface or on "security review/audit/pentest".
---
# security-audit (orchestrator)
Read: `.aix/meta-docs/security/audit-process.md`; `grep -n "<component or category>" docs/security/vulnerability-register.md`; the task's `security:` list.

## Procedure
1. Scope: components/paths changed (`git diff --name-only` for a task) or the user's target.
   Run `aix code security <paths> --audit` and `aix code vulnerabilities <paths> --audit` first: deterministic findings per VUL row with file:line, and the audit report skeleton with the evidence table filled. The skills below reason about those hits and complete the Status column; they do not re-discover what the scan already lists.
2. Categories touched → skills (map in audit-process.md). Always include `security-audit-dependencies` if lockfiles changed and `security-audit-secrets-config` if config changed.
3. Run each selected skill; each returns findings rows.
4. Write `docs/security/audits/AUDIT-<date>-<category>.md` per category (template `.aix/templates/audit-report.md`); add rows to `audits/INDEX.md`.
5. Update register statuses **only** with evidence (test name / commit); new findings → `confirmed` rows + tasks (`core-roadmap-task`).
6. Report to the user: rows flipped, rows still `expected`/`unverified`/`confirmed`/`mitigated`, tasks created. Never mark `addressed` without a negative test (`sec_VUL-…`) or a documented manual verification.
