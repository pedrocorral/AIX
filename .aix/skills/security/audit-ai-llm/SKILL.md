---
name: security-audit-ai-llm
description: Audit prompt injection, system-prompt leakage, tool least-privilege, exfiltration via tools/RAG, model/prompt supply chain, cost limits; VUL-AI rows, any LLM, agent, tool, RAG or prompt change.
---
# security-audit-ai-llm
Read: register rows for category AI (`grep -n "VUL-AI" docs/security/vulnerability-register.md`); `.aix/meta-docs/security/secure-coding-baseline.md`; relevant meta-doc: `security/ai-llm-security.md`, `stacks/python/ai-app.md`.

## Checks
- Untrusted content isolated and labelled in prompts; outputs schema-validated before use.
- Tools: schema + permission + side-effect class; write/external-send require confirmation unless FR says otherwise; outbound allowlists.
- Injection corpus tests pass (no instruction following from documents/tool results); no secret/system prompt echo.
- Model versions pinned; prompts versioned with evals.
- Budgets: tokens per request/user, max tool iterations, timeouts.

## Procedure
1. Locate code by layer (`.aix/meta-docs/architecture/project-layout.md`): `backend/app/*/{prompts,tools,adapters/<provider>}/`, AI services. Grep targeted patterns; do not read whole directories.
2. For each check: evidence (file:line) → finding or pass. Run available tools: run `TS-AI-*` evals and injection corpus; review tool registry permissions.
3. Write/extend the negative tests `sec_VUL-AI-NNN` in `tests/<level>/security/` (marker `@tests TS-SEC-…`) proving each mitigation; add `@mitigates VUL-AI-NNN` at the control.
4. Return findings rows to `security-audit` (or write the audit report yourself if run standalone): VUL id, before → after, evidence.
5. New issues → `confirmed` rows + tasks; controls added without a negative test yet → `mitigated`. Never flip to `addressed` without a passing negative test or a documented manual verification.
