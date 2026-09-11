# Changelog

## 2.10.0 — 2026-09-11

- Optional kit language standards `aix/languages/python`, `aix/languages/typescript`, `aix/languages/java`, `aix/languages/rust` (`.aix/instructions/languages/`): each states decisions (version floor, toolchain that must pass, errors and logging, structure) in about forty lines, scoped by file extension, meant to be replaced by an organisation's own. The kit profiles `fastapi-react` (python, typescript) and `kedro` (python) include them.

## 2.9.0 — 2026-09-11

- `aix skills use NAME ID` and `aix skills use NAME default`: choose the implementation of a skill class from the command line instead of editing `use:` in `.aix/config.yaml` by hand. The choice wins over the profile and over layer precedence; `info` lists the ids on offer.

## 2.8.4 — 2026-09-11

- `aix instructions list` uses the same columns as `aix skills list` (name, state, description); layer and kind moved to `info`.

## 2.8.3 — 2026-09-11

- `aix upgrade` now refreshes `.aix/profiles/` too (kit profiles were left at the installed version).
- The kit's opt-in technology standards are now `aix/frameworks/fastapi-backend`, `aix/frameworks/react-frontend` and `aix/frameworks/kedro-pipelines` (folder `.aix/instructions/frameworks/`, was `stacks`). A stack is a combination such as FastAPI plus React, which is what a profile is; each of these files covers one framework. `aix upgrade` rewrites the old ids in `.aix/config.yaml`.

## 2.8.2 — 2026-09-11

- `aix doctor` reports the AGENTS.md blocks and the scoped instructions separately (the blocks were labelled "scoped").

## 2.8.1 — 2026-09-11

- `aix rules` is an alias of `aix instructions` (the Cursor / Claude Code / Windsurf name for the same files).

## 2.8.0 — 2026-09-11

- `aix instructions [list] | info ID | show ID | enable ID | disable ID`: the instruction files are first-class next to skills. `list` shows every instruction any layer offers with its state (active, optional (off), disabled, not in profile), layer and kind (block that builds AGENTS.md, scoped by globs, always). `enable`/`disable` switch one file and re-run the install; state lives in `.aix/config.yaml` (`instructions:`, `disabled_instructions:`), survives `aix upgrade`, and wins over the active profile. Profiles stay the way to switch a whole set (router + instructions + skill implementations).
- `aix help instructions`.

## 2.7.0 — 2026-09-11
- Instruction blocks: AGENTS.md is assembled by `aix install` from instructions with `block: true`, `section` and `order`; the kit's contract lives in `.aix/instructions/agents/` (header, authority, rules, navigation, session, output) and a layer replaces a block by id or adds a section. Managed sections are preserved; `aix doctor` reports hand-written sections outside them. Rule order in AGENTS.md fixed (8 modularity, 9 the kit folder).
- Kit stack standards as opt-in scoped instructions (`optional: true`): `aix/stacks/fastapi-backend`, `react-frontend`, `kedro-pipelines`, selected by the new kit profiles `fastapi-react` and `kedro` or by `instructions:` in config.
- ACME example gains an output-block override and a compliance block.

## 2.6.1 — 2026-09-11
- `aix install --into DIR` run from a checkout whose `.aix/custom/` is filled installs as an organisation: the customisation lands as the project's `.aix/org/` and the checkout's git URL (or path) is recorded as `source:`. `custom/`, `org/` and the index never travel as payload.

## 2.6.0 — 2026-09-11
- `aix install --into DIR --from SOURCE`: install a project from an organisation. SOURCE is a path or git URL (cloned into `~/.cache/aix/sources/`) to either the organisation's kit checkout (its `.aix/` is the payload, its `.aix/custom/` becomes the project's `.aix/org/`) or a bare layer folder. `source:` is recorded in config.yaml and `aix upgrade` refreshes `.aix/org/` from it.
- `examples/acme/`: a complete fictional organisation layer used as the fixture: 36 skill implementations with `class:` and `@acme/…` ids (fifteen manual-only, some with references, scripts, agent metadata), 8 scoped instructions (Django, Vue, Dagster, engineering, documentation, shared packages, plain language, web-app profile), two profiles, documentation templates, a router fragment.

## 2.5.0 — 2026-09-11
- 28 new kit skills so that every class an organisation catalogue typically uses has a good default: `core/which-skill`; `spec/write-skill`, `write-for-agents`, `plain-language`; `architecture/trace`, `deep-modules`, `domain-model`, `improve`; `implement/code-python`, `code-typescript`; `testing/validate-ui`; new categories `debug/` (diagnose with a hypothesis-loop script, merge-conflicts), `workflow/` (plan-feature, to-tickets, triage with a label vocabulary, wayfinder, research, prototype, setup-tracker, wizard) and `coach/` (grill, grill-me, grill-with-docs, teach, questionnaire, wait-what, scaffold-exercises). Thirteen are manual-only. 71 kit skills in ten categories.

## 2.4.0 — 2026-09-11
- Skill classes and implementations: `class:` in front matter lets an implementation live under its own folder name; `id:`/`version:` name it; several implementations of one class may coexist, chosen by `use:` in config.yaml, by the active profile, or by layer precedence; `aix skills info` shows the winner, why, and the alternatives. `disable-model-invocation: true` shows as state `manual`.
- Scoped instructions: `instructions/*.md` in a layer (id, description, applyTo, always), rendered by `aix install` as native Copilot `.instructions.md` files, Cursor `.mdc` rules and a `## Scoped instructions` section in AGENTS.md/GEMINI.md; validated by `aix docs validate`.
- Profiles: `profiles/<name>.yaml` (router, instructions, skills) shipped by a layer; `aix profile list|show|use|off`. The organisation router becomes the `## Organisation` section of AGENTS.md, GEMINI.md and the Copilot pointer.

## 2.3.0 — 2026-09-11
- Skill overrides by layer (AIX-DEVELOPMENT.md §11-12, first slice): a folder at the same class path in `.aix/custom/skills/` (project, committed) or `~/.config/aix/skills/` (person; applied only with a terminal, never in CI or with `AIX_NO_USER=1`; `AIX_USER_DIR` relocates it) replaces the kit's implementation; a new path adds a class; an empty `DISABLED` file removes one. `aix install` links the winning implementation under the class name and writes `.aix/index.json` (layer, id, version, content hash per class; git-ignored). `aix skills info` shows layer, id, hash and shadowed copies; `aix skills` lists overrides; `aix doctor` reports linked content that changed since the last install. `aix docs validate` checks custom skills too.

Versioning: majors only for breaking changes (layout, removed commands, AGENTS.md contract); minors for new functionality, counting past 9 (`x.10`, `x.11`, …); patches for fixes. Details in `AIX-DEVELOPMENT.md` §10.

## 2.2.2 — 2026-09-08
- `aix install --into DIR` works again from a folder that is not a project (regression from 2.0.2).

## 2.2.1 — 2026-09-08
- `aix install` by a user who does not own the kit checkout: links already pointing at the right place are left untouched, and a permission error on the kit is a clear message instead of a crash (the PATH link for that user is already done). Unknown `aix install` options are rejected.

## 2.2.0 — 2026-09-07
- Kit-owned files are checksummed in `.aix/manifest.json` (written by `aix install` and `aix upgrade`); `aix doctor` reports locally edited kit files; `aix upgrade` marks them in the plan ("LOCAL EDIT WILL BE LOST") before overwriting. AGENTS.md rule 9: `.aix/` is the kit, not the project. Prompted by an agent patching a kit script inside a project.
- Security scanners read the `aix: skip-security-scan` marker in the first 30 lines (was 12; the vulnerabilities module's own marker sat on line 15).

## 2.1.1 — 2026-09-07
- `aix code <typo>` reports the unknown command and lists the valid ones instead of treating it as a path.

## 2.1.0 — 2026-09-07
- `aix code vulnerabilities [--taint] [--cve] [--history]`: the deep security layer. Python taint analysis (route/command parameters, request objects, argv, environment, stdin → shell, eval, SQL, file paths, redirects, template strings, deserialisation, outbound requests; sanitisers respected; one call deep, per file) reporting the chain from source to sink; known CVEs for pinned dependencies (requirements, uv/poetry/pdm locks, package-lock, pnpm-lock, Cargo.lock) via the OSV database; secrets in git history bounded by `--commits`. Findings name VUL row and CWE; `--audit` writes the evidence report; `--gate`. Self-test on known flows, a throwaway git history and a manifest.

## 2.0.2 — 2026-09-07
- `aix install` from inside a project: the kit fixes the `~/.local/bin/aix` link first (the aix on PATH is always the kit's launcher, never a project's copy), then relinks the project's skills; in a 1.x project it prints the upgrade hint instead of refusing.

## 2.0.1 — 2026-09-07
- `aix install` (no `--into`) works from any folder: it acts on the kit checkout the launcher belongs to (links its skills, puts `aix` on PATH). Needed after 2.0 since the kit folder is no longer a project by itself from outside.

## 2.0.0 — 2026-09-07
- **Layout**: everything the kit owns lives in `.aix/` (`config.yaml`, `scripts/`, `templates/`, `meta-docs/`, `skills/`, `bin/`); the project marker is `.aix/config.yaml`; root launchers are gone (the `aix` on PATH runs the project's `.aix/scripts/aix.py`); the kit no longer creates `backend/ frontend/ shared/ infra/` (project-layout.md only recommends a tree). At the root only AGENTS.md, CLAUDE.md, GEMINI.md, `docs/` (the project's ground truth) and your code remain.
- `aix upgrade` migrates a 1.x project in place: moves the kit-owned folders under `.aix/`, removes the root launchers, rewrites the pointer texts; project docs, code and git history untouched (renames). `.aix/config.yaml` merge keeps `disabled_skills` and the `style:` block.
- `aix install --into` copies `.aix/`, the three root files and the `docs/` seed. Code tools skip `.aix/` unless targeted explicitly. Validator checks both `docs/` and `.aix/meta-docs/`.

## 1.10.0 — 2026-09-07
- `aix code stats [PATH...] [--metric ...] [--report]`: terminal histogram of function sizes (fixed comparable bins, bars scaled to the window, limit marked), mean, sample sd, median, p90/p95, max, share over the limit; the largest functions and the files/folders pushing most functions over the limit. `--metric` switches to cognitive, cyclomatic, nesting or params. [TASK-0004]

## 1.9.0 — 2026-09-07
- `aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]`: deterministic static checks (Python, JS/TS, Rust, Java, Dockerfiles, compose, manifests, env files) mapped to the seeded VUL rows and CWEs, following bandit/semgrep/gitleaks/eslint-plugin-security: injection, shell/eval, template strings, path traversal, unsafe deserialisation, XML entities, private keys and tokens, hard-coded secrets, TLS off, debug on, weak hashes, weak randomness, JWT unverified, insecure cookies, XSS, CSRF off, CORS *, open redirect, secrets in logs, prompt injection, LLM calls without limits, chmod 777, privileged containers, Dockerfile without USER or tag, unpinned dependencies and missing lockfiles. Findings to review, never proof; test code listed, not gated; `aix: accepted VUL-…` inline suppressions listed; `aix: skip-security-scan` file marker. `--audit` writes `docs/security/audits/AUDIT-<date>-code.md` with the evidence table, the input `aix docs security` requires. Wired into the security-audit orchestrator. [TASK-0003]

## 1.8.0 — 2026-09-06
- `skills/refactor/`: seven skills, one per `aix code` finding type (cycle, shortcut, hub, dead, clone, readability, modernise), each with procedure, verification and hand-off. Reports name the skill on their last line; `review-code-review` proposes it; `core-sdd-workflow` runs it after review; modularity.md and readability.md point to them. `aix help refactor`.

## 1.7.3 — 2026-09-06
- `aix help` and `aix version` print the kit name in capitals: AIX 1.7.3.

## 1.7.2 — 2026-09-06
- `aix code style` respects context (after review feedback on a real project): tests get twice the line limit, `assert` no longer counts as a branch, no magic-number/docstring advice in tests; decorated functions (routes, commands, fixtures) have no parameter limit; React components may be PascalCase; HTTP status codes are not magic numbers.

## 1.7.1 — 2026-09-06
- `aix code style` detects the target runtime (`scripts/runtime.py`: pyproject requires-python, .python-version, venv, tsconfig target, engines.node, Cargo.toml, pom/Gradle; source shown in the header) and adds a modernise tier with only what that version enables (match, `X | None`, builtin generics, `@dataclass`, pathlib, tomllib, `?.`, `??`, const/let, let-else, switch expressions). Advice, never gated. JS/TS function detection now handles typed arrow functions and destructured parameters.

## 1.7.0 — 2026-09-06
- `aix code style [TARGET...]`: readability per function (lines, cognitive complexity per SonarSource, cyclomatic, nesting, parameters, naming, docstring, magic numbers) with limits in `framework.yaml` `style:`; targets are folders, files (extension optional) or one function (`file:func`, `file/func`, `file::Class.method`) which gets a card with line-numbered findings and advice; `--gate` on limits only; `--selftest`. `docs/meta-docs/conventions/readability.md` with the evidence; linter rule names per stack; wired into AGENTS.md, code-review, implement-feature and the definition of done.

## 1.6.0 — 2026-09-06
- Commands grouped by what they act on: `aix code graph|complexity|dead|clones`, `aix docs validate|coverage|security`, plus the kit commands (`install`, `upgrade`, `doctor`, `about`, `version`, `help`), `aix task`, `aix skills`. `aix help code`, `aix help docs` and `aix help code dead` etc. Old forms (`aix graph`, `aix complexity`, `aix validate`, `aix coverage`, `aix security`) remain as aliases for the 1.x line.

## 1.5.4 — 2026-09-06
- `aix graph --clones [--similarity PCT]`: duplicated functions. Exact groups by normalised structure hash (clone types 1-2; Python via the parser, JS/TS/Rust/Java via normalised tokens), near-clones by winnowed fingerprints (type 3, MOSS algorithm), sorted by size × similarity; `--clones --gate` fails on exact groups. Verified on the kit (0) and the monolith (1 exact pair, 8 near-clones, hand-checked).

## 1.5.3 — 2026-09-06
- `aix graph --dead`: dead modules (no entry module reaches them: entry points, tests, config, facades, `__main__` scripts) and, with `--functions`, Python functions/methods never referenced by name (decorated, dunder, exported, entry/test code excluded). Candidates listed with the rule that judged them; `--dead --gate` fails on any.

## 1.5.2 — 2026-09-06
- README explains the modularity principle and how `aix graph` measures it; `aix help` lists every graph option.

## 1.5.1 — 2026-09-06
- `aix graph`: measurement fixed and tested. Stable nodes by Martin instability (≤ 0.25) replace the fan-out-zero leaf rule (removed the false positives on models); transitive reduction on the graph with cycles contracted; every shortcut listed with its bypass; upward dependencies (into a composition root, or against the layer order) listed and gated; Lakos NCCD and Newman folder modularity Q; `--selftest` with known-answer cases. Verified on a real project by reading every candidate.
- `aix graph`: the headline is now **reducible complexity** = (complexity − ideal complexity) / ideal, where ideal complexity is the transitive reduction of the inner graph (facades collapsed, leaves excluded; composition roots and tests exempt from shortcut counting). 0 % = nothing removable without losing a dependency. `--max-reducible` (alias `--max-excess`). "Ground state" wording replaced.

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
