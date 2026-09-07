---
id: META-TEST-AI
title: Testing data pipelines and AI features
---
# Testing data pipelines and AI features
- **Pipelines**: each stage is a pure function of inputs → outputs; unit-test with tiny fixtures; integration-test with a sampled dataset; assert schema (columns, types, ranges) with a data-validation library; record row counts and drift metrics.
- **Models (ML)**: tests for training reproducibility (seeded), evaluation metric thresholds from `NFR-*`, serialisation round-trip, and inference latency budgets.
- **LLM features**: never assert exact text. Use (1) structured-output schema validation, (2) golden sets with rubric scoring or LLM-as-judge with fixed model + temperature 0 recorded as a snapshot, (3) property checks (no PII echo, refusal on injection payloads — `VUL-AI-*`), (4) cost/token budgets. Record evals in `docs/tests/non-functional/` as `TS-AI-*`.
- **Prompt changes** are code changes: versioned files, a TS per prompt, eval run in CI (sampled) and nightly (full).
