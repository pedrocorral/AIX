# ACME — an example organisation layer

A fictional organisation's customisation of AIX, used by the kit's own tests and as the template for a real one.
It is a bare layer folder (`skills/`, `instructions/`, `profiles/`, `templates/`, `AGENTS.md` fragment): install a
project from it with

```bash
aix install --into my-app --from /path/to/AIX/examples/acme
cd my-app && aix profile use web-app        # or data-pipelines
```

- 37 skill implementations, one per class of a full catalogue, each `class:` + `id: "@acme/…"` with ACME's own
  approach (three-lens review, questions-first hand-off, glossary-locked writing, bisect-first diagnosis, …).
  Twelve are manual-only. Some carry `references/`, `scripts/` or `agents/openai.yaml`.
- 8 scoped instructions (Django backend, Vue frontend, Dagster pipelines, engineering discipline, documentation,
  shared packages, plain language, the web-app profile) with `applyTo` globs; two profiles select them.
- Two instruction blocks: one replaces the kit's `aix/agents/output` block (ACME commit format), one adds a
  `Compliance (ACME)` section to AGENTS.md.
- Documentation templates under `templates/project-docs/`. A layer may also ship `templates/docs/` (overlaid on the documentation seed every project receives) and `templates/pointers/` (the pointer texts).

A real organisation forks the kit repository and fills `.aix/org/` with the same shape; upstream releases arrive
by a normal git merge (upstream's `org/` is empty), and projects install with `--from` the fork's URL. The fork's
`.aix/custom/`, if any, travels the same way.
