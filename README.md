# AIX — a spec-driven development kit (SDDK) for coding agents

AIX is a spec-driven development kit (SDDK): a language-agnostic, clone-and-go kit for building applications with AI coding agents
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

One line puts `aix` on your PATH (clones the kit into `~/.local/share/aix/kit`, links `~/.local/bin/aix`, adds the
folder to your shell profile, verifies):

```bash
curl -fsSL https://raw.githubusercontent.com/pedrocorral/AIX/main/install.sh | sh
```

Windows, PowerShell: `irm https://raw.githubusercontent.com/pedrocorral/AIX/main/install.ps1 | iex`. Already cloned?
`./.aix/bin/aix self-install` does the same from your clone (`--dry-run` shows the plan). Then, in a new terminal:

```bash
aix install --into my-app     # copies the kit into the project, links skills into every agent runtime, asks which folders hold code
cd my-app && aix doctor && aix docs validate
```

`aix self-update` pulls the clone; `aix upgrade` inside a project brings it to that version. Install, upgrade and `aix agents` offer to add the generated paths (`.aix/`, agent link folders, rendered files, reports) to `.gitignore`, and keep any file of yours they would overwrite as `<name>-bak`. Note: the whole `.aix/` is ignored for now, so teammates and CI run `aix install --into .` first; see the CLI conventions for the trade-off.

`aix` acts on the nearest project at or above your current folder (the one holding `.aix/config.yaml`), running that project's own copy of the CLI. Outside any project only `help`, `about`, `version`, `install --into` and `skills registry` work. `aix` is the only tool you need. Linux/macOS run the `aix` bash launcher, Windows runs `aix.cmd`; both call
`.aix/scripts/aix.py` (Python 3.9+, no dependencies). That one `aix` on PATH runs the `.aix/scripts/aix.py` of whatever project you are in; `aix version` names both copies.

| Command | Does |
|---|---|
| `aix self-install [--dry-run]` | Make `aix` callable from any terminal, from a clone: `~/.local/bin/aix` link (foreign file kept as `.bak`), PATH line in every shell profile found (bash, zsh, fish; Windows: user PATH), verification. Idempotent. Alias `aix install aix`; `aix self-update` pulls the clone |
| `aix install [--into DIR] [--copy]` | Install skills into every selected agent (`aix agents`); `--into` first copies the kit into an existing project, asking per existing item: replace (old kept as `.bak`), skip, merge (add missing files only), all-variants, abort. `--replace-all` / `--skip-all` / `--merge-all` answer for you |
| `aix upgrade [PROJECT] [--dry-run] [--yes]` | Update a project to the kit version of the `aix` you run. The same list `aix install` copies (`.aix/scripts/payload.py`) says what may change: owned paths are overwritten, AGENTS.md, GEMINI.md and .aix/config.yaml are merged, everything else (your docs, code, downloads, `.aix/custom/`) is never touched |
| `aix code security [PATH...] [--gate] [--audit]` | Deterministic static security checks mapped to the VUL register and CWEs; findings to review, never proof; `--audit` writes the audit report the register needs as evidence |
| `aix code stats [PATH...] [--metric ...]` | Terminal histogram of function sizes (or any style metric) scaled to the window, mean/sd/median/percentiles, share over the limit, and the largest functions, files and folders |
| `aix code find` | Which folders hold code: a checklist that sets `code_roots` in `.aix/config.yaml`, the default scope of the code tools; also run at the end of `aix install` |
| `aix code vulnerabilities [--taint] [--cve] [--history] [--audit]` | The deep security layer: Python taint paths from input to dangerous sinks, known CVEs for pinned dependencies (OSV, network), secrets in git history; evidence to review, `--audit` writes the report |
| `aix code style [TARGET...] [--gate]` | Readability per function: lines, cognitive and cyclomatic complexity, nesting, parameters, names, docstring, magic numbers, against limits in `.aix/config.yaml`; a single function (`file:func`) gets a card with line-numbered advice |
| `aix docs validate` | Check IDs, links, indexes, front-matter (exit 1 on errors) |
| `aix doctor` | Installation health (links, pointer files, always-on wiring, STATE.md, Python, PATH) with a fix per problem. `validate` = the docs; `doctor` = the tooling |
| `aix docs security [open\|validated] [--gate]` | Vulnerability register: validated vs not-validated rows, audit skills still to run, statuses without evidence; `--gate` is the release check |
| `aix code graph` / `aix code complexity` `[PATH...] [--functions] [--dead] [--clones] [--gate] [--max-reducible PCT] [--report] [--selftest]` | The modularity metric: real dependency graph vs its ideal (transitive reduction) = reducible %, each edge listed with its bypass; cycles, upward dependencies, hubs, propagation cost, NCCD, folder Q; `--dead` lists dead modules and (Python) never-referenced functions; `--clones` lists duplicated functions (exact groups and near-clones); `--gate` for CI |
| `aix docs coverage` | Regenerate `docs/tests/coverage-matrix.md` |
| `aix task new\|start\|block\|done\|list` | Road-map helper, keeps `STATE.md` in sync |
| `aix skills [general\|specific] [category]` | Catalogue: group (general = behaviour for every session, specific = one job), level (always / orchestrator / on-demand), state, runtimes. `*` marks always-on; a general skill not always-on shows as inactive. `show`, `enable`, `disable`, `always`, `on-demand NAME` manage them |
| `.aix/custom/skills/<class>/`, `~/.config/aix/skills/<class>/` | Override a skill for this project or for yourself: same path replaces, new path adds, `DISABLED` removes; `aix skills info` shows the winning layer and hash |
| `aix skills use NAME ID` | Choose which implementation of a skill class the runtimes see, when a layer or profile offers several; `default` returns to precedence |
| `aix agents [NAME...\|all\|--list]` | Which agents the project equips: claude, copilot, cursor, gemini, opencode, codex. A checklist with the detected ones preselected; install then links folders and pointer files only for those, and removes what it made for the others. `aix install --into DIR --agents a,b` sets it at install time |
| `aix instructions [list] \| info ID \| show ID \| enable ID \| disable ID` | The instruction files every layer offers: blocks that build AGENTS.md and scoped standards rendered per runtime; switch one on or off. `aix rules` is an alias |
| `aix profile use NAME` | Apply a profile shipped by a layer: scoped instructions (rendered natively for Copilot and Cursor), one implementation per skill class, the organisation router |
| `aix skills registry` / `add NAME [--always]` / `remove` / `update` | Known third-party skills with evidence (caveman, ponytail, karpathy-guidelines, two from superpowers, the 25 of mattpocock/skills). `add` downloads into `.aix/skills/extern/`; an entry with a `class` becomes that kit class's implementation and is selected at once (`aix skills use CLASS default` returns to the kit's), one without keeps its bare name and is linked everywhere; general skills become always-on unless `--on-demand` |
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

In the kit repository itself, `docs/` is the kit's own ground truth (its ADRs, tasks, state, test map). Projects are seeded from `.aix/templates/docs/`, and pointer files from `.aix/templates/pointers/`; an organisation or a project overlays both by placing the same paths under its own `templates/`.

## The guide

`aix guide` prints the table of contents of the user guide, eleven chapters in plain language (`aix guide skills`, `aix guide 5`, `aix guide --all`); it travels with every project under `.aix/meta-docs/guide/`.

## Tests

`aix self-test` (from the clone; the long form is `python -m unittest discover -s tests`) runs the kit's own suite in temporary folders (install, upgrade from the previous release, layers, instructions, skills, code tools, migration); `tests/README.md` explains it. `tests/` is not in the payload, so projects never receive it. Nothing runs on GitHub: the suite runs when you run it.

## Organisations, profiles, personal overrides

An organisation forks the kit and fills `.aix/org/` with the same shape as `.aix/`: skill implementations
(`class:` + `id: "@org/…"`), scoped instructions (`applyTo` globs, rendered natively for Copilot and Cursor and
listed in AGENTS.md for the rest), profiles (saved sets of choices) and templates. Projects install with
`aix install --into my-app --from <fork url>` and follow it with `aix upgrade`; the kit's own updates reach the fork
by a normal git merge. `.aix/org/` and `.aix/custom/` follow one rule: copied when the origin has the folder,
replaced on upgrade when it has it, left alone when it does not; `--from-org SRC` / `--from-custom SRC` take one of
them from elsewhere. `examples/acme/` is a complete fictional organisation to copy from.
Instructions follow the same model: AGENTS.md is assembled from blocks that a layer can replace or extend, and
scoped standards (`applyTo` globs) render natively per runtime. The kit ships FastAPI, React and Kedro standards as
opt-in, as are language conventions for Python, TypeScript, Java and Rust (`aix/languages/*`): `aix instructions enable aix/frameworks/fastapi-backend` for one, or the profiles `aix profile use fastapi-react | kedro` for the set.
The same shape works one level down for one project (`.aix/custom/`) and for one person (`~/.config/aix/`, never
committed). `aix skills info CLASS` always says which layer won and why.

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

See `docs/INDEX.md` and `.aix/skills/INDEX.md` to explore. Developing AIX itself (not an app)? Read `AIX-DEVELOPMENT.md` — it is never loaded by app agents. Framework version: see `.aix/config.yaml`. Versioning: majors only for changes that break how a project uses the kit, minors for new functionality and they count past 9 (`x.10`, `x.11`, …), patches for fixes; see `AIX-DEVELOPMENT.md` §10.
