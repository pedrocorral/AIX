# Changelog

## 1.5.0 — 2026-09-06
- `aix help COMMAND` / `aix COMMAND --help`: detailed per-command help written for agents; `aix complexity` alias of `aix graph`.
- `aix graph`: the modularity metric. Module graph (Python, JS/TS, Rust, Java) or Python call graph measured against its ground state (forest): circuit rank, excess %, leaf-adjusted excess, cycles, hubs, propagation cost; `--gate`, `--report`. Wired into modularity.md and code-review. Applied to the kit itself: two import cycles in scripts/ removed by extracting the leaves catalog.py and project.py (leaf-adjusted excess 0 %, propagation cost halved).

## 1.4.0 — 2026-09-06
- `aix upgrade`: verbose per-file plan (line deltas, kept sections, removals), experimental-feature warning before the confirmation, `GEMINI.md` merged like `AGENTS.md` (keeps the always-on section), content-only copies (works on files owned by another user). Verified on a real project.
- Front-matter parsers read YAML block scalars (`>` / `|`), so skills such as ponytail show their full description.
- `aix upgrade [PROJECT] [--dry-run] [--yes]`: update a project's kit files from the kit checkout by ownership (kit-owned overwritten/removed, project-owned untouched, AGENTS.md and framework.yaml merged). Fix: `aix skills always|on-demand` now accepts built-in skills.
- Design principle *modularity* (`docs/meta-docs/architecture/modularity.md`, AGENTS.md rule 8): acyclic, one-directional, sparse dependency graph; reuse leaves, never hubs; evidence cited. Wired into design-app, code-review and the definition of done.
- `aix task done` creates `completed/YYYY-MM/INDEX.md` when the month folder is new (`aix validate` used to fail on the first completed task). [TASK-0002]
- Antigravity and Gemini CLI support: both read skills from the existing `.agents/skills` target; `GEMINI.md` pointer (committed, in the `--into` payload, created by `aix install` if missing) carries the always-on section for Gemini CLI; `aix doctor` checks it. Antigravity reads `AGENTS.md` directly. [TASK-0002]
- `aix security [open|validated] [--gate]`: register report (validated vs not, audit skills to run, missing evidence). `aix validate` fails a VUL status beyond `expected` without an audit report (and an ADR for `accepted`).
- `aix validate` fails on status drift: FR/NFR/API `implemented`/`verified` without `@implements`, TS `automated` without `@tests`, VUL `mitigated` without `@mitigates` in code.
- `aix doctor`: installation health with a fix per finding (validate = docs, doctor = tooling). Hand-off trigger unified at ~60 % context plus event triggers.
- Single `aix` CLI (`aix` bash launcher, `aix.cmd` for Windows, logic in `scripts/aix.py`): `install`, `validate`, `coverage`, `task`, `version`. Replaces `install.sh`, `install.ps1` and the `Makefile`. `aix install` links itself into `~/.local/bin` when present.
- `aix install --into` prompts on every existing item ([r]eplace/[s]kip/[m]erge, R/S/M for all, [a]bort); replace keeps a `.bak`; merge adds missing files only; `--replace-all`/`--skip-all`/`--merge-all` for non-interactive use.
- `aix help` opens with a short introduction; `aix about` prints a complete description of the kit.
- `aix skills list|show|enable|disable`: skill catalogue with derived activation level; disabled skills recorded in `framework.yaml` `disabled_skills` and honoured by `aix install`.
- Third-party skills: `skills/extern/registry.json` (evidence required), `aix skills registry|add|remove|update`, tarball download without git, bare names for extern skills, `--always` / `aix skills always|on-demand` writes an *Always-on skills* section into AGENTS.md, `.github/copilot-instructions.md` and `.cursor/rules/aix.mdc`. `aix install` prunes dangling runtime links.
- Skill groups: `general` (behaviour for every session) vs `specific` (one job); `aix skills general|specific [category]` filters, `*` marks always-on, general skills not always-on show as `inactive`; `aix skills add` makes general skills always-on by default (`--on-demand` to opt out).
- `aix` finds the project from the current folder (nearest `framework.yaml`) and re-executes that project's `scripts/aix.py`; outside a project only help/about/version/install --into/skills registry run. Skill list: `recommended` and `available` states listed first, `(*) always` marker.

## 1.3.0 — 2026-09-05
- Renamed kit to AIX. Added `AIX-DEVELOPMENT.md` (kit-development handoff; excluded from app context and from `--into`).

## 1.2.0 — 2026-09-05
- Canonical field dictionary (`docs/requirements/data-model/field-dictionary.md`) enforced by validator and spec/implement skills.
- Deterministic `scripts/` bundled in injection, secrets/config and dependency audit skills.
- Cursor support: `.cursor/skills` target + `.cursor/rules/aix.mdc` pointer.
- Blunt no-heavy-compute-in-request rule in AI and data-science stack docs; ADRs marked as settled decisions.

## 1.1.0 — 2026-09-05
- Authority order in AGENTS.md; AGENTS.md trimmed ~35 %; skill descriptions trimmed.
- `docs/conflicts/` (open/resolved CONFLICT-* records) feeding ADRs.
- Register states `unverified`, `confirmed`, `mitigated`; audit report captures asset/threat/control/evidence/residual risk.
- Requirement template: actors & permissions, data & privacy, security & observability; lifecycle adds `verified`.
- Task template: files changed, verification performed, exact next actions; `road-map/blocked/` + `roadmap.py block`.
- `docs/operations/` (deployment, recovery, runbooks); per-area allowed/forbidden dependency notes.

## 1.0.0 — 2026-09-04
- Initial release: docs hierarchy, 36 skills, installer for opencode / VS Code / Claude Code / agents dirs,
  validator, coverage matrix, road-map tooling, templates.
