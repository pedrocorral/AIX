# AIX — Spec-Driven Development Kit for Agentic AI

A language-agnostic, clone-and-go framework for building applications with AI coding agents
(opencode, VS Code / Copilot, Claude Code, Cursor, Antigravity, Gemini CLI, …) where **documentation is the ground truth**
and code is its optimised implementation.

## What you get

| Folder | Purpose |
|---|---|
| `AGENTS.md` | The single entry point every agent reads first (≈ 80 lines). |
| `.aix/meta-docs/` | How to build apps: MVC, frontend/backend split, persistence abstraction, ORM, testing, security, project layout, Python/Java/JS stacks. |
| `docs/requirements/` | **Ground truth** for *your* application (functional, non-functional, data model, API, ADRs). |
| `docs/tests/` | What must be tested (one spec per requirement group) + generated coverage matrix. |
| `docs/security/` | Vulnerability register (expected → addressed) + audit reports. |
| `docs/conflicts/` | Open/resolved spec-vs-code conflicts awaiting or holding human decisions. |
| `docs/operations/` | Deployment, recovery, runbooks. |
| `docs/road-map/` | `pending/` → `going-on/` → `completed/` tasks; session state for resuming work. |
| `.aix/` | The kit: `config.yaml`, `scripts/` (the CLI), `templates/`, `meta-docs/` (how to build), `skills/` (built-in + `extern/`), `bin/` (launchers). Replaced wholesale by `aix upgrade`, except your config values and extern skills. |
| your code | Whatever layout your stack wants (`backend/ frontend/`, `src/`, a Cargo workspace ...). The kit never creates or touches it; `.aix/meta-docs/architecture/project-layout.md` recommends a tree for new monorepos. |

## Quick start

```bash
git clone <this-repo> my-app && cd my-app
./.aix/bin/aix install        # links skills into .opencode/ .github/ .claude/ .agents/ .cursor/ ; writes pointer files (Copilot, Cursor, Gemini) + road-map state
aix docs validate         # sanity-check IDs, links, indexes
```

`aix` acts on the nearest project at or above your current folder (the one holding `.aix/config.yaml`), running that project's own copy of the CLI. Outside any project only `help`, `about`, `version`, `install --into` and `skills registry` work. `aix` is the only tool you need. Linux/macOS run the `aix` bash launcher, Windows runs `aix.cmd`; both call
`.aix/scripts/aix.py` (Python 3.9+, no dependencies). `aix install` also links `aix` into `~/.local/bin` when that folder exists, and that one `aix` then runs the `.aix/scripts/aix.py` of whatever project you are in.

| Command | Does |
|---|---|
| `aix install [--into DIR] [--copy]` | Install skills into every agent runtime; `--into` first copies the kit into an existing project, asking per existing item: replace (old kept as `.bak`), skip, merge (add missing files only), all-variants, abort. `--replace-all` / `--skip-all` / `--merge-all` answer for you |
| `aix upgrade [PROJECT] [--dry-run] [--yes]` | Update a project to the kit version of the `aix` you run: overwrites kit-owned paths (scripts, templates, meta-docs, built-in skills, launchers), merges AGENTS.md and .aix/config.yaml, never touches your docs, code or extern skills |
| `aix code security [PATH...] [--gate] [--audit]` | Deterministic static security checks mapped to the VUL register and CWEs; findings to review, never proof; `--audit` writes the audit report the register needs as evidence |
| `aix code stats [PATH...] [--metric ...]` | Terminal histogram of function sizes (or any style metric) scaled to the window, mean/sd/median/percentiles, share over the limit, and the largest functions, files and folders |
| `aix code vulnerabilities [--taint] [--cve] [--history] [--audit]` | The deep security layer: Python taint paths from input to dangerous sinks, known CVEs for pinned dependencies (OSV, network), secrets in git history; evidence to review, `--audit` writes the report |
| `aix code style [TARGET...] [--gate]` | Readability per function: lines, cognitive and cyclomatic complexity, nesting, parameters, names, docstring, magic numbers, against limits in `.aix/config.yaml`; a single function (`file:func`) gets a card with line-numbered advice |
| `aix docs validate` | Check IDs, links, indexes, front-matter (exit 1 on errors) |
| `aix doctor` | Installation health (links, pointer files, always-on wiring, STATE.md, Python, PATH) with a fix per problem. `validate` = the docs; `doctor` = the tooling |
| `aix docs security [open\|validated] [--gate]` | Vulnerability register: validated vs not-validated rows, audit skills still to run, statuses without evidence; `--gate` is the release check |
| `aix code graph` / `aix code complexity` `[PATH...] [--functions] [--dead] [--clones] [--gate] [--max-reducible PCT] [--report] [--selftest]` | The modularity metric: real dependency graph vs its ideal (transitive reduction) = reducible %, each edge listed with its bypass; cycles, upward dependencies, hubs, propagation cost, NCCD, folder Q; `--dead` lists dead modules and (Python) never-referenced functions; `--clones` lists duplicated functions (exact groups and near-clones); `--gate` for CI |
| `aix docs coverage` | Regenerate `docs/tests/coverage-matrix.md` |
| `aix task new\|start\|block\|done\|list` | Road-map helper, keeps `STATE.md` in sync |
| `aix skills [general\|specific] [category]` | Catalogue: group (general = behaviour for every session, specific = one job), level (always / orchestrator / on-demand), state, runtimes. `*` marks always-on; a general skill not always-on shows as inactive. `show`, `enable`, `disable`, `always`, `on-demand NAME` manage them |
| `aix skills registry` / `add NAME [--always]` / `remove` / `update` | Known third-party skills with evidence (caveman, ponytail, karpathy-guidelines, superpowers' systematic-debugging, verification-before-completion). `add` downloads into `.aix/skills/extern/` and links everywhere; general skills become always-on (named in AGENTS.md and the Copilot/Cursor/Gemini pointers) unless `--on-demand` |
| `aix help COMMAND` / `aix COMMAND --help` | Detailed help for one command, written so an agent can understand the tool (e.g. `aix help graph`) |
| `aix about` | Full explanation of the kit: purpose, workflow, folders, IDs, skills, every command |
| `aix version` | Kit version from `.aix/config.yaml` |

Then open the folder in opencode / VS Code and say:

> "Read AGENTS.md and run the `core-session-resume` skill."

For an **existing project** (any language): `aix install --into /path/to/project` copies `docs/`, `.aix/skills/`,
`.aix/templates/`, `.aix/scripts/`, `AGENTS.md` and links the skills, without touching your code.

## Layout (2.0)

```
my-app/
├── AGENTS.md  CLAUDE.md  GEMINI.md      the agent contract and two one-line pointers (runtimes read them at the root)
├── .aix/                               everything the kit owns; `aix upgrade` replaces it, keeping your config values
│   ├── config.yaml                     version, paths, disabled skills, style limits
│   ├── scripts/  templates/  bin/      the CLI, the document templates, the launchers
│   ├── meta-docs/                      how to build: architecture, persistence, testing, security, conventions, workflow, stacks
│   └── skills/                         core/ spec/ architecture/ implement/ testing/ security/ review/ refactor/ + extern/
├── docs/                               the project's own ground truth, never touched by the kit
│   └── requirements/  tests/  security/  conflicts/  operations/  road-map/
├── .claude/ .opencode/ .github/ .agents/ .cursor/   generated skill links + pointer files (links are git-ignored)
└── your code                           whatever layout your stack wants; the kit never creates it
```

Projects on the 1.x layout (kit folders at the root, `framework.yaml`) are migrated in place by `aix upgrade`.

## Core principles

1. **Requirements are the ground truth.** Code that disagrees with `docs/requirements/` is a defect
   unless the user decides otherwise (the agent must ask; decision is recorded as an ADR).
2. **Navigate, don't scan.** Every folder has an `INDEX.md`. Agents go `AGENTS.md → INDEX → INDEX → file`,
   never `ls -R` or "read the whole project".
3. **Everything has an ID and a trail.** `FR-…` → `TS-…` → code markers (`@implements`, `@tests`) → `VUL-…`.
4. **Skills are small and specific.** Each does one job; the orchestrator skills chain them.
5. **State survives sessions.** `docs/road-map/going-on/STATE.md` lets any agent resume.
6. **Modularity.** One job per node; the dependency graph is sparse, acyclic and one-directional; reuse stable
   leaves, never hubs. Measured, not assumed: see below.

## Modularity: the principle and the measurement

Picture the code as a graph. Nodes are modules (or functions), edges are dependencies (imports, calls).
The principle, known in the literature as **modularity** (Parnas 1972, Constantine 1974, Martin's acyclic and
stable dependencies, Baldwin & Clark 2000), says:

- **One job per node.** If describing a module needs "and", split it.
- **Few edges, one direction, no cycles.** Edges point from the specific toward the stable: controllers → services
  → ports → models. Never sideways into a sibling domain, never upward into whoever calls you.
- **Reuse leaves, never hubs.** Depending on a stable node (a value type, a pure function, a port) is free reuse and
  makes the graph bigger without tangling it. A hub, widely depended on *and* reaching into state, I/O or a domain,
  spreads every change to all its dependants.

Evidence that this predicts real cost: propagation cost (MacCormack, Rusnak & Baldwin 2006), Sturtevant's MIT
study of a cyclic core (several times the defect density, lower productivity), Cai & Kazman's design-rule-space
work, and the fact that Cargo and Go refuse to compile dependency cycles.

**`aix code graph` (alias `aix code complexity`) measures it** instead of trusting anyone's opinion:

| Step | What |
|---|---|
| real graph | files and their imports (Python, JS/TS, Rust, Java) or Python functions and calls; re-export facades collapsed; unresolved imports ignored, never guessed |
| stable nodes | Martin's instability `out / (in + out)` ≤ 0.25; edges into them are free reuse and not counted |
| **ideal complexity** | the transitive reduction of the graph with cycles contracted (Aho, Garey & Ullman 1972): the smallest graph that delivers exactly the same dependencies. A baseline, achievable or not, identical for every project |
| **reducible %** | `(complexity − ideal) / ideal`. Every counted edge is listed with its bypass (`A -> C also reached via B`) so a human or an agent can confirm it. 0 % = at the baseline |
| exact findings | cycles; upward dependencies (into a composition root, or against the layer order); hubs |
| shape | propagation cost, Lakos' NCCD (1.0 = balanced binary tree), Newman modularity Q of the folder tree |

```bash
aix code graph --selftest          # known-answer cases: chain, diamond, shortcut, cycle, reuse, layer skip, upward
aix code graph                     # the report
aix code graph --gate              # CI: fails on any cycle or upward dependency (add --max-reducible PCT for a ceiling)
```

Read it in this order: cycles and upward dependencies are facts, fix them first; each SHORTCUT line is one edge
to drop or route through its bypass; reducible % and the shape numbers are for comparing over time and across
projects. Full method: `aix help graph` and `.aix/meta-docs/architecture/modularity.md`.

See `docs/INDEX.md` and `.aix/skills/INDEX.md` to explore. Developing AIX itself (not an app)? Read `AIX-DEVELOPMENT.md` — it is never loaded by app agents. Framework version: see `.aix/config.yaml`.
