# testing/ — proving requirements, without duplication
Read this when: planning or writing tests. Skip when: no test is involved.

| Path | What | Read when |
|---|---|---|
| `strategy.md` | Pyramid, what is proven where, TS ↔ code mapping, no-duplication rule, CI gates | Before planning tests for any feature |
| `levels.md` | Unit / integration / functional / e2e / contract / performance / security — scope, tooling, naming | Choosing the level of a TS |
| `fixtures-and-data.md` | Factories, builders, memory adapter, test databases, deterministic time/ids/randomness | Writing any test needing state |
| `ai-and-data-testing.md` | Testing pipelines, models, LLM features (evals, golden sets, non-determinism) | Data-science / AI apps |
