---
name: security-threat-model
description: Add or revise VUL rows and the threat model when new attack surface appears (endpoint, input, storage, dependency, LLM/tool, infra) or on "what could go wrong".
---
# security-threat-model
Read: `.aix/meta-docs/security/threat-categories.md`; `docs/security/threat-model.md`; grep the register for the component.
1. Identify assets, actors, boundaries touched; tag components (`internet-facing | internal | batch | ai-tool`) in `threat-model.md`.
2. For each category applicable, ensure a register row exists for this component (`.aix/templates/vulnerability.md` row format) with `status: expected`; mark inapplicable baseline rows `not-applicable` with justification in the description.
3. Create `TS-SEC-*` stubs for rows that need negative tests (`testing-plan-tests`).
4. Add the row IDs to the task's `security:` list. Report the new/changed rows.
