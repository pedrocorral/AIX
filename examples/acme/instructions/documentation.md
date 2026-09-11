---
id: acme/documentation
name: "Documentation Standards"
description: "Use when creating, changing or reviewing a README, ARCHITECTURE.md, an ADR, a runbook, a release guide or any page under docs/ in an ACME repository."
applyTo: "README.md,ARCHITECTURE.md,docs/**/*.md"
---
# Documentation standards
- Minimum set: `README.md` (what, run, test, deploy in ≤ 80 lines), `ARCHITECTURE.md` (the flow from entry point to storage, one diagram), `docs/INDEX.md`, ADRs under `docs/requirements/decisions/`, runbooks under `docs/operations/`.
- Templates from `.aix/org/templates/project-docs/`; every page carries `owner:` and `verified:` in its front matter.
- Claims are verified by `review-doc-drift-check` (ACME implementation: claim by claim) before a release.
- Plain language per `acme/plain-language`.
