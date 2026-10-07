# road-map/pending/backlog/ — agreed, not ready
Ordered by priority (top = next). Each becomes a `TASK-*` file when it has requirements and tests planned.

| Item | Why |
|---|---|
| Planted-finding tests for `aix code security`, `vulnerabilities`, `dead`, `clones` | the four tools are only smoke-run today |
| Tests for `aix task`, `aix docs coverage`, `aix docs security --gate`, always-on wiring | uncovered commands |
| Windows: run the suite there once; `install.ps1`; `aix self-install` on PowerShell | never executed |
| Cross-file taint in `aix code vulnerabilities` | Python and JS/TS today, one call deep, per file |
| Scripts for the seven audit skills without one | authorisation on `{id}` routes is the real gap |
| Skill trigger evals; measure "navigate, never scan" | the kit's claims are unmeasured |
| Multi-agent STATE.md; scaffolds; INDEX generation; multi-repo | earlier backlog |
| Codex skill list budget: verify on a real Codex session (2.21.23) | Codex caps the initial skill list at 2 % of the context window or 8,000 characters; the kit's 71 skills need about 17,000. Unverified whether Codex trims here: watch for its "omitted skills" warning the first time Codex runs in an AIX project; if it does, shorten descriptions or disable unused skills with `aix skills` |
| ABAP `COND`/`SWITCH` expressions in cognitive complexity (section 22) | Sonar's rule: a conditional expression costs 1 plus its nesting, each further WHEN 1, the ELSE 1. Not built: both benchmark projects declare ABAP 7.02 and use none, so no real code would check the rule; build it when a 7.40+ project joins the extended suite (2.21.51, 2026-10-07) |
