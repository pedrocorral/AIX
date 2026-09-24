# road-map/pending/backlog/ — agreed, not ready
Ordered by priority (top = next). Each becomes a `TASK-*` file when it has requirements and tests planned.

| Item | Why |
|---|---|
| Planted-finding tests for `aix code security`, `vulnerabilities`, `dead`, `clones` | the four tools are only smoke-run today |
| Tests for `aix task`, `aix docs coverage`, `aix docs security --gate`, always-on wiring | uncovered commands |
| Windows: run the suite there once; `install.ps1`; `aix self-install` on PowerShell | never executed |
| Cross-file taint in `aix code vulnerabilities` | Python and JS/TS today, one call deep, per file |
| `aix code clones` on real code: hundreds of exact groups (bat 739, ripgrep 978, requests 382) | type-2 normalisation makes every small test or getter a clone; review the threshold or exclude tests |
| `aix code dead` on real code: WebGoat 223, Juice Shop 247, ripgrep 65 dead modules | Spring components by reflection, TS path aliases (`@/`), Rust workspace `mod` trees are not resolved |
| Scripts for the seven audit skills without one | authorisation on `{id}` routes is the real gap |
| Skill trigger evals; measure "navigate, never scan" | the kit's claims are unmeasured |
| Multi-agent STATE.md; scaffolds; INDEX generation; multi-repo | earlier backlog |
