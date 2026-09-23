---
id: TASK-0001
title: Bootstrap project — vision, glossary, stack decision, layout
status: pending
created: 2026-09-04
completed:
requirements: []
tests: []
security: []
context_files: [docs/requirements/product/vision.md, docs/requirements/product/glossary.md, docs/requirements/decisions/ADR-0001-adopt-aix-and-choose-stack.md, .aix/meta-docs/architecture/project-layout.md]
---
# TASK-0001 — Bootstrap project

## Goal (one sentence)
Turn the kit into *this* project: vision, domains, stack decision, initial layout, register tagging.

## Plan
- [ ] Interview the user; fill `vision.md`, `personas.md`, `glossary.md` (domain codes).
- [ ] Complete and accept `ADR-0001` (stack, persistence backends, frontend).
- [ ] Run skill `architecture-design-app` → domain list, layering, persistence plan, initial FR/DM/API stubs.
- [ ] Run skill `security-threat-model` → tag components, adjust register rows.
- [ ] Scaffold `backend/`, `frontend/` per layout for the chosen stack (`stacks/<lang>/`); CI skeleton in `infra/`.
- [ ] Delete `example` domain docs once the first real domain exists.
## Progress log (append-only, newest last)
- 2026-09-04: created by installer.
## Decisions / open questions
## Definition of done checklist
- [ ] docs validated  - [ ] STATE.md updated  - [ ] first real tasks in `pending/next/`
