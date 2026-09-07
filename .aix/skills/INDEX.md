# skills/ — one source of truth, installed into every agent runtime
Skill name = folder path joined with `-` (e.g. `security/audit-injection` → `security-audit-injection`). `aix install` links each leaf into `.opencode/skills`, `.claude/skills`, `.github/skills`, `.agents/skills`. Never edit the installed copies. States, filters and always-on rules: `.aix/meta-docs/conventions/cli.md`.

| Category | Skills | Purpose |
|---|---|---|
| `core/` | `sdd-workflow` (orchestrator), `session-resume`, `session-handoff`, `conflict-resolution`, `roadmap-task`, `find-doc` | Running the loop, sessions, navigation |
| `spec/` | `write-requirement`, `write-adr`, `review` | Producing/reviewing ground truth |
| `architecture/` | `design-app`, `design-persistence`, `structure-project` | Whole-app and data-layer design |
| `implement/` | `feature` (orchestrator), `orm-model`, `repository`, `endpoint`, `ui` | Writing code in the right layer |
| `testing/` | `plan-tests` (orchestrator), `write-unit-tests`, `write-integration-tests`, `write-functional-tests`, `coverage-audit` | Test specs and automation |
| `security/` | `audit` (orchestrator), `threat-model`, `audit-injection`, `audit-authn-authz`, `audit-input-validation`, `audit-secrets-config`, `audit-dependencies`, `audit-web-xss-csrf`, `audit-data-privacy`, `audit-logging-monitoring`, `audit-ai-llm`, `audit-infra` | Register lifecycle |
| `review/` | `code-review`, `doc-drift-check` | Quality gates |
| `refactor/` | `cycle`, `shortcut`, `hub`, `dead`, `clone`, `readability`, `modernise` | One skill per `aix code` finding type: how to fix it safely, verify with the tool and the tests, hand off |
| `extern/` | third-party skills from `registry.json` (`aix skills registry`), e.g. `caveman`, `ponytail` | Style/method add-ons; bare names, always-on via `aix skills add NAME --always` |

Skills may bundle `.aix/scripts/` (deterministic scans the agent runs before reasoning — cheaper than reading code) and `references/`. Conventions for skills: front-matter `name` + pushy `description`; sections *When NOT to use / Inputs / Procedure / Outputs / Hand-off*; a reading budget; no duplication of meta-docs (link to them).
