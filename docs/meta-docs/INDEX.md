# meta-docs/ — how to build applications with AIX

Language-agnostic guidance. Stack specifics live in `stacks/`. Each sub-folder has its own INDEX.

| Folder | What | Read when |
|---|---|---|
| `workflow/` | The spec-driven loop, conflict resolution, session protocol, definition of done | Starting any task; on code/spec disagreement |
| `conventions/` | IDs & traceability, document format, token economy (how to find things cheaply), git, the `aix` CLI | Writing any doc; when unsure where something is |
| `architecture/` | MVC, frontend/backend separation, layering, project layout, API design, config & secrets, errors & logging | Designing a new app or feature; deciding where code goes |
| `persistence/` | Persistence abstraction layer, ORM rules, switching backends, migrations | Anything touching data storage |
| `testing/` | Strategy, levels (unit/integration/functional/e2e), fixtures & data, test-spec ↔ code mapping | Planning or writing tests |
| `security/` | Audit process, threat categories → skills, AI/LLM-specific security | Audits; any new attack surface |
| `stacks/` | Python (general web, data science, AI apps, tooling), Java, JavaScript | Once the stack is chosen (`ADR-0001`) |

**Designing a new app?** Read in this order: `workflow/spec-driven-loop.md` → `architecture/INDEX.md` (all) →
`persistence/abstraction-layer.md` → `testing/strategy.md` → `security/audit-process.md` → your stack in `stacks/`.
That set is sufficient for a complete architecture design; record the choices as ADRs in `docs/requirements/decisions/`.
