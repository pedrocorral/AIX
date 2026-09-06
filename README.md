# AIX — Spec-Driven Development Kit for Agentic AI

A language-agnostic, clone-and-go framework for building applications with AI coding agents
(opencode, VS Code / Copilot, Claude Code, Cursor, Antigravity, Gemini CLI, …) where **documentation is the ground truth**
and code is its optimised implementation.

## What you get

| Folder | Purpose |
|---|---|
| `AGENTS.md` | The single entry point every agent reads first (≈ 80 lines). |
| `docs/meta-docs/` | How to build apps: MVC, frontend/backend split, persistence abstraction, ORM, testing, security, project layout, Python/Java/JS stacks. |
| `docs/requirements/` | **Ground truth** for *your* application (functional, non-functional, data model, API, ADRs). |
| `docs/tests/` | What must be tested (one spec per requirement group) + generated coverage matrix. |
| `docs/security/` | Vulnerability register (expected → addressed) + audit reports. |
| `docs/conflicts/` | Open/resolved spec-vs-code conflicts awaiting or holding human decisions. |
| `docs/operations/` | Deployment, recovery, runbooks. |
| `docs/road-map/` | `pending/` → `going-on/` → `completed/` tasks; session state for resuming work. |
| `skills/` | Hierarchical agent skills (one source of truth) installed into every agent runtime. |
| `templates/` | Canonical templates for every document type. |
| `aix` / `aix.cmd` | The CLI (Linux/macOS bash launcher, Windows batch launcher) → `scripts/aix.py`. |
| `scripts/` | CLI implementation: installer, validator, coverage matrix, road-map helper (Python 3.9+, no deps). |
| `backend/ frontend/ shared/ infra/` | Where your application code lives, following `docs/meta-docs/architecture/project-layout.md`. |

## Quick start

```bash
git clone <this-repo> my-app && cd my-app
./aix install        # links skills into .opencode/ .github/ .claude/ .agents/ .cursor/ ; writes pointer files (Copilot, Cursor, Gemini) + road-map state
aix validate         # sanity-check IDs, links, indexes
```

`aix` acts on the nearest project at or above your current folder (the one holding `framework.yaml`), running that project's own copy of the CLI. Outside any project only `help`, `about`, `version`, `install --into` and `skills registry` work. `aix` is the only tool you need. Linux/macOS run the `aix` bash launcher, Windows runs `aix.cmd`; both call
`scripts/aix.py` (Python 3.9+, no dependencies). `aix install` also links `aix` into `~/.local/bin` when that folder exists.

| Command | Does |
|---|---|
| `aix install [--into DIR] [--copy]` | Install skills into every agent runtime; `--into` first copies the kit into an existing project, asking per existing item: replace (old kept as `.bak`), skip, merge (add missing files only), all-variants, abort. `--replace-all` / `--skip-all` / `--merge-all` answer for you |
| `aix upgrade [PROJECT] [--dry-run] [--yes]` | Update a project to the kit version of the `aix` you run: overwrites kit-owned paths (scripts, templates, meta-docs, built-in skills, launchers), merges AGENTS.md and framework.yaml, never touches your docs, code or extern skills |
| `aix validate` | Check IDs, links, indexes, front-matter (exit 1 on errors) |
| `aix doctor` | Installation health (links, pointer files, always-on wiring, STATE.md, Python, PATH) with a fix per problem. `validate` = the docs; `doctor` = the tooling |
| `aix security [open\|validated] [--gate]` | Vulnerability register: validated vs not-validated rows, audit skills still to run, statuses without evidence; `--gate` is the release check |
| `aix graph` / `aix complexity` `[PATH...] [--functions] [--gate] [--max-reducible PCT] [--report]` | The modularity metric: complexity vs ideal complexity (transitive reduction) = reducible %, plus cycles, shortcuts, hubs, propagation cost; `--gate` for CI |
| `aix coverage` | Regenerate `docs/tests/coverage-matrix.md` |
| `aix task new\|start\|block\|done\|list` | Road-map helper, keeps `STATE.md` in sync |
| `aix skills [general\|specific] [category]` | Catalogue: group (general = behaviour for every session, specific = one job), level (always / orchestrator / on-demand), state, runtimes. `*` marks always-on; a general skill not always-on shows as inactive. `show`, `enable`, `disable`, `always`, `on-demand NAME` manage them |
| `aix skills registry` / `add NAME [--always]` / `remove` / `update` | Known third-party skills with evidence (caveman, ponytail, karpathy-guidelines, superpowers' systematic-debugging, verification-before-completion). `add` downloads into `skills/extern/` and links everywhere; general skills become always-on (named in AGENTS.md and the Copilot/Cursor/Gemini pointers) unless `--on-demand` |
| `aix help COMMAND` / `aix COMMAND --help` | Detailed help for one command, written so an agent can understand the tool (e.g. `aix help graph`) |
| `aix about` | Full explanation of the kit: purpose, workflow, folders, IDs, skills, every command |
| `aix version` | Kit version from `framework.yaml` |

Then open the folder in opencode / VS Code and say:

> "Read AGENTS.md and run the `core-session-resume` skill."

For an **existing project** (any language): `aix install --into /path/to/project` copies `docs/`, `skills/`,
`templates/`, `scripts/`, `AGENTS.md` and links the skills, without touching your code.

## Core principles

1. **Requirements are the ground truth.** Code that disagrees with `docs/requirements/` is a defect
   unless the user decides otherwise (the agent must ask; decision is recorded as an ADR).
2. **Navigate, don't scan.** Every folder has an `INDEX.md`. Agents go `AGENTS.md → INDEX → INDEX → file`,
   never `ls -R` or "read the whole project".
3. **Everything has an ID and a trail.** `FR-…` → `TS-…` → code markers (`@implements`, `@tests`) → `VUL-…`.
4. **Skills are small and specific.** Each does one job; the orchestrator skills chain them.
5. **State survives sessions.** `docs/road-map/going-on/STATE.md` lets any agent resume.

See `docs/INDEX.md` and `skills/INDEX.md` to explore. Developing AIX itself (not an app)? Read `AIX-DEVELOPMENT.md` — it is never loaded by app agents. Framework version: see `framework.yaml`.
