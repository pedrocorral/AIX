---
id: META-CONV-CLI
title: The aix command-line interface
read_when: You need to run a kit command (validate, coverage, task, skills) or wonder which project it acts on.
---
# The `aix` CLI

One command for every kit operation. `aix` (bash, Linux/macOS) and `aix.cmd` (Windows) call `scripts/aix.py`
(Python 3.9+, no dependencies). Agents run it instead of editing road-map files or runtime skill folders by hand.

## Which project it acts on
`aix` walks up from the current folder to the nearest `framework.yaml` and re-executes **that project's**
`scripts/aix.py`, so every path resolves inside the project, never inside the kit checkout on PATH.
Outside any project only `help`, `about`, `version`, `install --into` and `skills registry` work.

## Commands
| Command | Does | When an agent uses it |
|---|---|---|
| `aix install [--copy]` | Link every enabled skill into `.opencode/ .claude/ .github/ .agents/ .cursor/` skills dirs; write pointer files and `STATE.md` if missing; prune dangling links | After adding, removing or editing skills |
| `aix install --into DIR` | Copy the kit into an existing project, asking per existing item ([r]eplace keeps `.bak`, [s]kip, [m]erge adds missing files only, R/S/M for all, [a]bort); `--replace-all` / `--skip-all` / `--merge-all` when no terminal | Bootstrapping a project |
| `aix validate` | Doc integrity: front-matter, INDEX completeness, IDs exist, links resolve, TS → FR, VUL statuses, field dictionary, **status drift** (`implemented`/`automated`/`mitigated` claimed without the matching code marker). Exit 1 on errors | Closing any task; pre-commit / CI |
| `aix doctor` | Installation health: skill links in every runtime, dangling links, pointer files, always-on sections consistent, extern provenance, `STATE.md` vs `going-on/`, Python, PATH. Fix per problem, exit 1 | Session start when something seems off; after `aix install --into` |
| `aix security [open\|validated] [--gate]` | Register state: rows not validated (worst first) with the audit skill to run, validated rows, rows whose status lacks evidence (audit report; ADR for `accepted`). `--gate` exits 1 if any row is open: the release check | Before an audit; closing a task with `security:` rows; release |
| `aix graph` / `aix complexity` `[PATH...] [--functions] [--gate] [--max-excess PCT] [--report]` | The modularity metric: dependency graph (modules for Python/JS/TS/Rust/Java, `--functions` for Python calls) measured against its ground state (forest, N-P edges): excess %, leaf-adjusted excess (edges into leaves are free), cycles, hubs, propagation cost. `--gate` fails on any cycle or excess above the limit; `--report` writes `docs/tests/dependency-graph.md` | Design reviews; `review-code-review` on every diff; CI gate |
| `aix coverage` | Regenerate `docs/tests/coverage-matrix.md` from FR files, TS `covers:` and `@implements` / `@tests` markers | Closing a task; before release |
| `aix task new "T" [--bucket b]` / `start` / `block ID "why"` / `done` / `list` | Move `TASK-*` files through `pending → going-on ⇄ blocked → completed/YYYY-MM` and keep `STATE.md` in sync | `core-roadmap-task`, `core-session-handoff` |
| `aix skills [general\|specific] [category]` | Catalogue (see below) | Choosing a skill; checking what is always on |
| `aix skills info NAME` / `show NAME` | Details (group, level, runtimes, source) / the SKILL.md | Before invoking an unfamiliar skill |
| `aix skills enable\|disable NAME` | Link/unlink everywhere; recorded in `framework.yaml` `disabled_skills` | Trimming a project's skill set |
| `aix skills registry` / `add NAME [--on-demand\|--always] [--extra a,b]` / `remove` / `update` | Third-party skills (below) | Adopting caveman, ponytail, … |
| `aix skills always\|on-demand NAME` | Add/remove the always-on wiring for any skill | Making a behaviour permanent |

`aix help COMMAND` (or `aix COMMAND --help`) prints the detailed help of one command; read it before using a command for the first time.

## Skill catalogue
`aix skills` prints `SKILL`, `STATE`, `DESCRIPTION` (description truncated to the terminal width, dropped on narrow terminals).

| State | Meaning |
|---|---|
| `recommended` | In the registry, flagged recommended, not downloaded. Listed first. |
| `available` | In the registry, not downloaded. Listed second. |
| `(*) always` | Named in `AGENTS.md`; applied in every session. |
| `on-demand` | Installed; invoked by name, by an orchestrator, or when its description matches. |
| `disabled` | Listed in `framework.yaml` `disabled_skills`; not linked into any runtime. |

Two groups, usable as filters: **general** = behaviour that applies to every session (output style, decision
method); **specific** = does one job when invoked (all AIX skills). A skill declares `group:` in its front-matter;
extern skills take it from the registry. Adding a general skill makes it always-on unless `--on-demand`.

## Always-on wiring
No runtime has an "always apply this skill" switch; skills load by description match or by name. The only
mechanism every runtime honours is its instructions file, so `aix skills always NAME` writes an
`## Always-on skills` section into:

| File | Read by |
|---|---|
| `AGENTS.md` | Claude Code (via `CLAUDE.md`), opencode, Antigravity, generic agents |
| `.github/copilot-instructions.md` | VS Code / GitHub Copilot — points at `.github/skills/NAME/SKILL.md` |
| `.cursor/rules/aix.mdc` | Cursor (`alwaysApply: true`) — points at `.cursor/skills/NAME/SKILL.md` |
| `GEMINI.md` | Gemini CLI (its context file) — points at `.agents/skills/NAME/SKILL.md` |

`aix skills on-demand NAME`, `remove NAME` and disabling all delete the entry. Two always-on *style* skills
conflict; the CLI warns. Skills named in `AGENTS.md` by the session protocol (`core-session-resume`,
`core-sdd-workflow`, `core-session-handoff`, `core-conflict-resolution`) are always-on by definition.

## Third-party skills
`skills/extern/registry.json` maps a name to a GitHub repo, sub-path, group, licence and an **evidence** line
(who measured what, with caveats). Only entries with published measurements or wide, sustained adoption belong
there. `aix skills add NAME` downloads the repo tarball over HTTPS (no git), copies the sub-folder to
`skills/extern/NAME/`, rewrites the front-matter `name` to match, records provenance in `.aix-source`, links it
into every runtime. Extern skills keep their bare name (`caveman`, not `extern-caveman`) so slash commands match
upstream docs. `skills/extern/` is committed with the project; `aix skills update` re-downloads.

## Ownership (what `aix upgrade` may overwrite)
| Kit-owned (overwritten on upgrade) | Project-owned (never touched) | Merged |
|---|---|---|
| `scripts/`, `aix`, `aix.cmd`, `templates/`, `docs/meta-docs/`, `skills/<built-in categories>/`, `CLAUDE.md` | `docs/requirements tests security conflicts operations road-map`, `skills/extern/`, runtime folders, your code | `AGENTS.md`, `GEMINI.md` (project keeps `## Always-on skills`, `## Project notes`), `framework.yaml` (`disabled_skills`) |
Project-specific agent instructions therefore go in a `## Project notes` section of `AGENTS.md`, never elsewhere in that file.

## Rules for agents
- Never edit files under `.opencode/ .claude/ .github/skills .agents/ .cursor/skills`: they are generated links.
- Never move `TASK-*` files by hand; use `aix task`.
- Run `aix validate` before every hand-off; `aix coverage` when a task closes; `aix security --gate` at release.
- Never change a VUL status without an audit report (`aix validate` fails); `accepted` also needs an ADR.
- Do not add registry entries without evidence; do not make a second style skill always-on.
