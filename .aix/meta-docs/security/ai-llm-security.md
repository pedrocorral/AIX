---
id: META-SEC-AI
title: AI / LLM security
---
# AI / LLM security
- **Trust boundary**: user messages, retrieved documents, tool results and model outputs are all untrusted. System prompt is policy, not a secret guarantee.
- **Prompt injection**: isolate untrusted content with delimiters + explicit instructions; never let retrieved text change tool permissions; validate structured outputs against schema before acting.
- **Tool use**: least privilege per tool; allowlist of actions; human confirmation for destructive/financial/external-send actions; log every tool call with arguments (redacted).
- **Data exfiltration**: outbound tool calls (HTTP, email) restricted to allowlists; scan outputs for secrets/PII patterns before returning or sending.
- **Supply chain**: pin model versions; verify downloaded weights (hash); vet third-party prompts/plugins like dependencies.
- **Abuse & cost**: per-user token budgets, rate limits, max tool iterations, timeouts.
- **Privacy**: minimise what is sent to providers; document data flows in `NFR-DATA-*`; retention of prompts/responses explicit.
- Tests: `sec_VUL-AI-*` negative tests with injection corpora; evals in `docs/tests/non-functional/`.
