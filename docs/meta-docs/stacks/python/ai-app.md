---
id: META-STACK-PY-AI
title: Python AI / LLM-supported apps
---
# Python AI / LLM-supported apps

## Layout additions
```
backend/app/<domain>/services/        # use cases orchestrating LLM calls (chains, agents) — business logic lives here
backend/app/<domain>/prompts/         # versioned prompt assets: <name>.v<N>.md with front-matter (model, temperature, schema)
backend/app/<domain>/repositories/    # ports: LLMClient, EmbeddingStore, ToolRegistry (yes: providers are repositories/adapters)
backend/app/<domain>/adapters/{anthropic,openai,local,fake}/   # provider adapters; `fake/` is mandatory for tests
backend/app/<domain>/tools/           # tool definitions: schema + least-privilege handler + audit log
docs/tests/non-functional/ai/         # TS-AI-* evals (golden sets, rubrics, injection corpora)
```

## Rules
- **Inference, embedding, training and any pandas/torch-scale work never run inside a request handler.** They are jobs (`backend/jobs/`) or a separate service; the handler enqueues and returns/streams. Blocking the web thread is a review-blocking defect.
- Provider SDKs only in `adapters/`; services depend on the `LLMClient` port (`complete(messages, schema?) -> Result`).
- Prompts are assets with IDs and versions; a change = task + eval run. Never build prompts by string concatenation inside services — use templates in `prompts/` with explicit variables.
- Structured outputs validated with schemas before use; treat outputs as untrusted (`../../security/ai-llm-security.md`).
- Tools: declare schema, permissions, side-effect class (read / write / external-send); human confirmation for the last two unless FR says otherwise.
- Observability: log prompt id/version, token counts, latency, cost, tool calls (redacted); budget per request and per user.
- RAG: ingestion is a pipeline (`data-science-app.md`); document provenance stored with chunks; retrieval results tagged untrusted.
- Determinism in tests: `fake/` adapter returns canned responses keyed by prompt id; evals use recorded runs.
