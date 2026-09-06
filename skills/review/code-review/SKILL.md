---
name: review-code-review
description: Review a diff against AIX rules: layering, MVC placement, persistence abstraction, markers, requirement fidelity, tests, security baseline; use before closing tasks, on PRs, or "review this".
---
# review-code-review
Inputs: `git diff` (or the files named), the FR/TS IDs in the task, `docs/meta-docs/architecture/layering.md`, `docs/meta-docs/security/secure-coding-baseline.md`.

Checklist (table: item / ok·issue / file:line / fix):
- Each changed behaviour maps to an FR (`@implements`) and each FR AC in the task has a TS automated (`@tests`).
- Modularity (`architecture/modularity.md`; run `aix graph` on the touched roots, compare with the report before the change): no new cycle; no sibling domain import; new shared code is a leaf (no upward imports); no module gains more than ~7 project imports; no growth of `utils`/`common` hubs.
- Layer placement: controllers thin; no ORM/driver imports outside adapters; services own transactions and authorisation; models pure.
- Persistence: ports unchanged or extended with memory adapter + contract test; no backend-specific leakage.
- API: contract (`API-*`) and OpenAPI match; error envelope; pagination/idempotency rules.
- Security baseline items touched; `@mitigates` where controls were added; new deps noted.
- Naming/layout per `project-layout.md`; file/folder size limits; INDEX updated for docs.
- Requirement fidelity: no extra behaviour; if found → `core-conflict-resolution`.
Verdict: approve / request changes with concrete edits. Do not rewrite code unasked; propose.
