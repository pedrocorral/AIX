#!/usr/bin/env python3
"""AIX is a spec-driven development kit for AI coding agents: documentation is the ground truth,
code is its implementation, and every change leaves a traceable trail. `aix install` puts everything
an agent needs to build any application into your project: {n} skills for specifying, designing,
implementing, testing, auditing and reviewing; design patterns and architecture guides (MVC,
frontend/backend split, persistence abstraction, ORM, testing, security); document templates; and
the road-map that lets work resume across sessions. `aix` then keeps the documentation consistent
and moves tasks between states. Run `aix about` for the full story.

Usage: aix <group> <command> [args]   (no command = this help; aix help <command> for details)
aix acts on the nearest project at or above the current folder (the one holding .aix/config.yaml).

The kit
  aix install [--into DIR] [--copy]   link skills into agent runtimes; --into copies the kit into DIR first
      --into asks per existing item: [r]eplace [s]kip [m]erge [R/S/M] all [a]bort  (replace keeps <item>.bak)
      --replace-all | --skip-all | --merge-all   answer for every collision without asking (CI, no terminal)
  aix upgrade [PROJECT] [--dry-run] [--yes]
                                      bring a project's kit files up to this checkout: overwrites kit-owned paths,
                                      merges AGENTS.md and .aix/config.yaml, never touches your docs, code or extern skills
  aix doctor                          is the INSTALL right? skill links, pointer files, always-on wiring, STATE.md,
                                      Python, PATH. Each problem comes with its fix
  aix about | version | help [CMD]    the full story | kit version | detailed help (e.g. aix help code dead)

The code                              (aix code ...; all four: Python, JS/TS, Rust, Java; --report writes docs/tests/)
  aix code graph [PATH...]            the modularity metric (alias: aix code complexity): real dependency graph
                                      vs its ideal (transitive reduction) = reducible %, each edge listed with its
                                      bypass; cycles, upward dependencies, hubs, propagation cost, NCCD, folder Q
      --functions                     Python call graph (functions and methods) instead of modules
      --gate [--max-reducible PCT]    CI: exit 1 on any cycle, any upward dependency, or reducible above the limit
      --selftest                      run the built-in known-answer cases; proves the arithmetic
  aix code dead [PATH...] [--functions] [--gate]
                                      dead code: modules no entry point reaches; with --functions, Python
                                      functions/methods never referenced (name-based, conservative)
  aix code clones [PATH...] [--similarity PCT] [--gate]
                                      duplicated functions: exact groups (same structure, other names/literals)
                                      and near-clones above the threshold (default 70 %)
  aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]
                                      deterministic static checks mapped to the VUL register and CWEs: injection,
                                      shell/eval, unsafe deserialisation, secrets and tokens, TLS off, debug on,
                                      weak hashes/randomness, JWT/cookies, XSS/CSRF/CORS, secrets in logs, prompt
                                      injection, Dockerfile root/unpinned, unpinned deps. Findings to REVIEW, never
                                      proof; --audit writes the audit report the register needs as evidence
  aix code stats [PATH...] [--metric lines|cognitive|cyclomatic|nesting|params] [--report]
                                      distribution of function sizes as a terminal histogram scaled to the window,
                                      mean, sd, median, p90/p95, max, share over the limit; the largest functions
                                      and the files and folders pushing most functions over the limit
  aix code style [TARGET...] [--all] [--gate] [--report] [--selftest]
                                      readability, per function: lines, cognitive and cyclomatic complexity,
                                      nesting, parameters, names, docstring, magic numbers; limits in
                                      .aix/config.yaml. TARGET = folder | file[.ext] | file:func | file::Class.m;
                                      a single function gets a card with line-numbered findings and advice;
                                      detects the runtime (pyproject, venv, tsconfig, Cargo, pom) and suggests
                                      modernisations that version enables (match, X | None, ?., let-else, ...)

The docs                              (aix docs ...)
  aix docs validate                   are the DOCS right? IDs, links, indexes, front-matter, status vs code markers,
                                      VUL evidence. CI gate, exit 1 on errors
  aix docs coverage                   regenerate docs/tests/coverage-matrix.md (requirement -> test -> code gaps)
  aix docs security [open|validated] [--gate]
                                      vulnerability register: validated rows (evidence) vs not, audit skills
                                      still to run; --gate exits 1 if any row is open

The road-map                          (aix task ...)
  aix task new "Title" [--bucket next|backlog|ideas] | start|block|done TASK-0007 ["reason"] | list

The skills                            (aix skills ...)
  aix skills [general|specific] [cat] catalogue: name, state (always / on-demand / disabled), description
  aix skills info NAME | show NAME    details (group, level, runtimes, source) | the SKILL.md
  aix skills enable|disable NAME...   link/unlink a skill everywhere; remembered in .aix/config.yaml
  aix skills registry                 known third-party skills (caveman, ponytail, ...) with evidence
  aix skills add NAME [--on-demand]   download a registry skill into .aix/skills/extern/, link it everywhere;
                                      general skills become always-on unless --on-demand
  aix skills remove|update NAME       drop it / re-download it;  aix skills always|on-demand NAME
  aix skills refactor                 the seven fix skills, one per aix code finding (aix help refactor)

Old forms still work: aix graph|complexity|validate|coverage|security = aix code graph | aix docs ...

Launchers: `aix` (bash, Linux/macOS) and `aix.cmd` (Windows) simply call this file with python3."""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from project import find_project


ABOUT = """\
AIX — Spec-Driven Development Kit for Agentic AI
=================================================

1. PURPOSE
----------
AIX exists because coding agents (Claude Code, opencode, GitHub Copilot, Cursor, ...) are excellent at writing
code and terrible at remembering why. Left alone they drift: a fix in one session contradicts a decision from the
previous one, tests get edited until they pass, security concerns are forgotten, and nobody can say which
requirement a given function serves. AIX turns the documentation of a project into the ground truth and makes the
agent work from it, so that:

  - requirements, not code, define what the application must do;
  - every test exists because a specification asks for it;
  - every piece of new attack surface is registered before it ships;
  - a new session (or a different agent, or a human) can resume exactly where the last one stopped;
  - the whole trail is greppable by ID rather than readable only by an LLM.

It is language-agnostic. The core documents describe architecture, persistence, testing and security in general
terms; per-stack notes (Python, Java, JavaScript) live under .aix/meta-docs/stacks/. AIX ships no runtime library
and imposes nothing on the compiled or deployed application.

2. THE CENTRAL RULE: REQUIREMENTS ARE GROUND TRUTH
--------------------------------------------------
When code disagrees with docs/requirements/, the code is a defect — unless the human decides otherwise. The agent
must not silently fix either side. It records a CONFLICT-* file in docs/conflicts/open/, freezes that scope, asks
the user, and the decision is written down as an ADR (Architecture Decision Record). Authority order, highest first:

  1. accepted ADRs                 docs/requirements/decisions/
  2. approved requirements         docs/requirements/  (FR, NFR, API, DM)
  3. accepted test/security specs  docs/tests/, docs/security/
  4. source code
  5. generated artefacts           (coverage matrix, reports)

3. HOW AN AGENT USES IT
-----------------------
AGENTS.md at the repository root is the contract every agent reads first (CLAUDE.md, GEMINI.md,
.github/copilot-instructions.md and .cursor/rules/aix.mdc just point to it; Antigravity reads it directly). It fits in about 3k tokens and stays in context permanently. Everything
else is loaded on demand by navigation, never by scanning: docs/INDEX.md -> folder INDEX.md -> file, or
`grep -rln "<ID>"`. The design constraint behind every file is minimal resident context per turn.

A session looks like this:

  start   -> skill core-session-resume: reads docs/road-map/going-on/STATE.md, the active task and only the files
             the task lists in `context_files`; verifies with git status and the task's test command; reports in
             six lines.
  work    -> skill core-sdd-workflow, the orchestrator, for any build/change/fix request:
               1. classify the request (feature, change, bug, refactor, infra, docs, exploration)
               2. spec check: does an approved requirement exist? write one if not (user approves); on
                  contradiction stop and run core-conflict-resolution
               3. plan tests (testing-plan-tests) -> TS-* files
               4. threat-model new surface (security-threat-model) -> VUL-* rows marked `expected`
               5. create/start a road-map task with `context_files`
               6. implement (implement-feature picks the layer skills) with @implements markers
               7. write tests per TS, mark them automated, run the suite
               8. security audit for the categories touched
               9. code review and doc-drift check on the diff
              10. close: aix docs validate, aix docs coverage, definition-of-done, task done, session handoff
  end     -> skill core-session-handoff (also at ~60 % context): update STATE.md, task progress, INDEXes.

4. THE DOCUMENT HIERARCHY  (docs/)
----------------------------------
  meta-docs/      How to build software with the kit: MVC, frontend/backend separation, project layout,
                  persistence abstraction (ports, unit of work, in-memory adapter, backend switching), ORM
                  guidelines, test strategy and levels, security practices, conventions (IDs, document format,
                  token economy), workflow (session protocol, conflict resolution, definition of done), stacks.
  requirements/   Ground truth for THIS application: product vision and glossary, functional requirements per
                  domain (FR-*), non-functional (NFR-*), API contracts (API-*), data model (DM-*) with a canonical
                  field dictionary (the only field names that may exist), decisions (ADR-*).
  tests/          One test specification (TS-*) per requirement group, each declaring what it `covers` and what it
                  deliberately does not; plus the generated coverage-matrix.md.
  security/       Vulnerability register (VUL-*) seeded with expected weaknesses; statuses expected -> unverified ->
                  confirmed -> mitigated -> addressed | accepted | not-applicable. A status may only change with an
                  audit report as evidence.
  conflicts/      open/ and resolved/ CONFLICT-* records; an open conflict freezes its scope.
  operations/     Deployment, recovery, runbooks, incident notes.
  road-map/       pending/{ideas,backlog,next} -> going-on -> blocked -> completed/YYYY-MM. going-on/STATE.md is the
                  cross-session memory.

Every folder has an INDEX.md listing its files and when to read them. Files stay under ~300 lines. Documents carry
YAML front-matter with their ID, status and relations.

5. IDS AND TRACEABILITY
-----------------------
  FR-<DOMAIN>-nnn  functional requirement      TS-<DOMAIN>-nnn  test specification
  NFR-nnn          non-functional requirement   VUL-nnn          vulnerability register row
  API-nnn          API contract                 TASK-nnnn        road-map task
  DM-nnn           data model entity            CONFLICT-nnnn    spec-vs-code conflict
  ADR-nnnn         decision

Code carries markers in comments: @implements FR-..., @tests TS-..., @mitigates VUL-.... `aix docs coverage` scans them
(no LLM involved) and produces the matrix requirement -> test spec -> code -> gaps ("no test spec", "spec not
automated", "no code"). `aix docs validate` checks that every referenced ID exists, links resolve, each folder has an
INDEX that lists its files, front-matter is present, skill names match their paths, register statuses are valid and
API/DM field names appear in the field dictionary.

6. SKILLS  (skills/)
--------------------
Small skills in the Agent Skills open format (SKILL.md with YAML front-matter), each doing one job,
organised in seven categories:

  core/          sdd-workflow (orchestrator), session-resume, session-handoff, conflict-resolution, roadmap-task,
                 find-doc
  spec/          write-requirement, write-adr, review
  architecture/  design-app, design-persistence, structure-project
  implement/     feature (orchestrator), orm-model, repository, endpoint, ui
  testing/       plan-tests (orchestrator), write-unit-tests, write-integration-tests, write-functional-tests,
                 coverage-audit
  security/      audit (orchestrator), threat-model, audit-injection, audit-authn-authz, audit-input-validation,
                 audit-secrets-config, audit-dependencies, audit-web-xss-csrf, audit-data-privacy,
                 audit-logging-monitoring, audit-ai-llm, audit-infra
  review/        code-review, doc-drift-check
  refactor/      cycle, shortcut, hub, dead, clone, readability, modernise (one per `aix code` finding type)

The nested folder is the single source of truth. `aix install` links every leaf skill, under its flat name
(security/audit-injection -> security-audit-injection), into the folders each runtime reads:
.opencode/skills, .claude/skills, .github/skills, .agents/skills and .cursor/skills (.agents/skills is the
agentskills.io location read by Antigravity, Gemini CLI and VS Code). Never edit the installed copies; they are
ignored by git. Some skills bundle deterministic scripts/ (regex scans that are cheaper than
having the model read code) and references/.

7. THE CLI
----------
`.aix/bin/aix` is a bash launcher (Linux, macOS) and `.aix/bin/aix.cmd` a batch launcher (Windows). Both run .aix/scripts/aix.py with
Python 3.9+ and no third-party dependencies. It acts on the nearest project at or above the current folder (the
one holding .aix/config.yaml). Commands are grouped by what they act on; `aix help <command>` explains each.

  The kit
  aix                       version and command list (same as `aix help`)
  aix about | version       this text | kit version from .aix/config.yaml
  aix install               link all skills into the five runtime folders; write pointer files for Copilot, Cursor
                            and Gemini CLI if missing; create road-map STATE.md if missing; on Linux/macOS symlink
                            `aix` into ~/.local/bin when that folder exists. Idempotent.
      --copy                copy skills instead of symlinking
      --into DIR            first copy the kit payload into an existing project, asking per existing item
                            ([r]eplace keeps <item>.bak, [s]kip, [m]erge adds missing files only, R/S/M for all,
                            [a]bort); --replace-all | --skip-all | --merge-all answer without a terminal
  aix upgrade [PROJECT] [--dry-run] [--yes]
                            update a project created with `--into` to the kit version of the checkout whose `aix`
                            you run. Kit-owned paths overwritten, AGENTS.md / GEMINI.md / .aix/config.yaml merged
                            (always-on skills, project notes, disabled skills kept), project docs and code never
                            touched. Shows the full plan, warns (experimental), asks; git is the backup.
  aix doctor                installation health: every skill linked in every runtime, no dangling links, pointer
                            files present, always-on sections consistent, extern skills updatable, STATE.md
                            consistent, Python and PATH. Prints a fix per problem.

  The code (aix code ...)   Python, JS/TS, Rust, Java; PATH... limits the folders; --report writes docs/tests/
  aix code graph            the modularity metric (alias: aix code complexity). Real dependency graph vs its ideal,
                            the transitive reduction with cycles contracted (the lowest complexity delivering the
                            same dependencies; a baseline, achievable or not): reducible %, each edge listed with
                            its bypass. Also cycles, upward dependencies, hubs, propagation cost, Lakos NCCD,
                            folder modularity Q. --functions for the Python call graph; --gate for CI (any cycle,
                            any upward dependency, or reducible above --max-reducible); --selftest proves the
                            arithmetic on known-answer cases.
  aix code dead             dead code: modules no entry point reaches; with --functions, Python functions and
                            methods never referenced by name (decorated, dunder, exported, entry/test code excluded)
  aix code clones           duplicated functions: exact groups (same structure, other names/literals) and
                            near-clones above --similarity PCT (default 70). Candidates: merge on shared purpose.
  aix code security         deterministic static checks mapped to the VUL register and CWEs (injection, shell,
                            deserialisation, secrets, TLS, debug, weak hashes, JWT, XSS/CSRF/CORS, logs, prompt
                            injection, Dockerfile, dependencies). Findings to review, never proof. --audit writes
                            the audit report the register requires as evidence for a status change.
  aix code stats            the shape of the code base: histogram of function sizes (or cognitive, cyclomatic,
                            nesting, parameters) scaled to the terminal, mean/sd/median/p90/p95/max, share over
                            the limit, and the largest functions, files and folders pulling the tail.
  aix code style            readability per function (lines, cognitive and cyclomatic complexity, nesting,
                            parameters, names, docstring, magic numbers) against the limits in .aix/config.yaml;
                            a folder or file gives a ranked table, one function (file:func) a card with
                            line-numbered findings and advice. Limits and evidence: conventions/readability.md.

  The docs (aix docs ...)
  aix docs validate         documentation integrity check described in section 5, plus status drift (a doc may
                            not claim implemented/automated/mitigated without the code marker) and VUL evidence
                            (a status beyond `expected` needs an audit report). Exit 1 on errors; the CI gate.
  aix docs coverage         regenerate docs/tests/coverage-matrix.md
  aix docs security [open|validated] [--gate]
                            the vulnerability register: rows not validated (worst first) with the audit skill to
                            run, validated rows, statuses without evidence. --gate is the release check.

  The road-map (aix task ...)
  aix task new "Title" [--bucket next|backlog|ideas]   create pending/<bucket>/TASK-nnnn-title.md
  aix task start | block "reason" | done TASK-nnnn     move it and keep STATE.md in sync
  aix task list                                        one line per task with status

  The skills (aix skills ...)
  aix skills [general|specific] [category]            catalogue: state (recommended/available/always/on-demand/
                                                      disabled), * marks always-on; general = behaviour for every
                                                      session, specific = one job
  aix skills info | show NAME                         details | the SKILL.md
  aix skills enable | disable NAME                    link/unlink everywhere; recorded in .aix/config.yaml
  aix skills registry | add NAME | remove | update    third-party skills with evidence; add downloads (no git),
                                                      general skills become always-on unless --on-demand
  aix skills always | on-demand NAME                  the always-on wiring (AGENTS.md, Copilot, Cursor, Gemini)

  Old forms remain as aliases: aix graph | complexity | validate | coverage | security.

8. GETTING STARTED
------------------
  New project:      git clone <aix> my-app && cd my-app && ./.aix/bin/aix install
  Existing project: aix install --into /path/to/project   (answer the prompts, then merge any previous agent
                    instructions into AGENTS.md section 5)
  Then open the folder in your agent and say: "Read AGENTS.md and run the core-session-resume skill."
  The seeded TASK-0001 guides the first session: product vision, glossary, ADR-0001 (stack choice), then the
  architecture-design-app skill.

9. WHEN NOT TO USE IT
---------------------
AIX is ceremony by design. A throwaway script or a one-person weekend project does not need requirement IDs,
test specs and a vulnerability register. It pays off when several sessions, agents or people touch the same
codebase, when you must show why something was built the way it was, or when security and test coverage have to
be demonstrable rather than assumed.

Developing the kit itself? Read AIX-DEVELOPMENT.md; it is deliberately kept out of app projects.
"""


def skill_count():
    return sum(1 for _ in (ROOT / ".aix" / "skills").rglob("SKILL.md"))


ANYWHERE = {"help", "-h", "--help", "about", "version", "-V", "--version"}  # need no project


def reexec_in_project(argv):
    """Run the project's own copy of the CLI so every module resolves ROOT to the project, not to this checkout."""
    if argv[:1] == ["upgrade"]:
        return  # upgrade must run from THIS checkout's scripts, not the project's older copy
    project = find_project(Path.cwd())
    if project is None:
        if argv and argv[0] in ANYWHERE or (argv[:1] == ["install"] and "--into" in argv) or argv[:2] == ["skills", "registry"]:
            return
        sys.exit("aix: not inside an AIX project (no .aix/config.yaml here or above). "
                 "Use `aix install --into DIR` to add AIX to a project, or cd into one.")
    own = project / ".aix" / "scripts" / "aix.py"
    if project != ROOT and own.exists():
        os.execv(sys.executable, [sys.executable, str(own), *argv])
    if project != ROOT and (project / "framework.yaml").exists():
        sys.exit(f"aix: {project} uses the 1.x layout; run `aix upgrade` (from this kit) to migrate it to .aix/")
    if project != ROOT:
        sys.exit(f"aix: {project} has .aix/ but no .aix/scripts/aix.py; run `aix install --into {project}`")



TOPICS = {
"install": """aix install [--copy] [--into DIR] [--replace-all|--skip-all|--merge-all]

Links every enabled skill from skills/ into the folders each agent runtime reads (.opencode/skills, .claude/skills,
.github/skills, .agents/skills, .cursor/skills), writes the pointer files for Copilot, Cursor and Gemini CLI if
missing, creates docs/road-map/going-on/STATE.md if missing, prunes dangling links, and on Linux/macOS links `aix`
into ~/.local/bin when that folder exists. Idempotent: run it after adding, removing or editing skills.
  --copy         copy skill folders instead of symlinking (filesystems or Windows setups without symlinks)
  --into DIR     first copy the kit payload (.aix/, AGENTS.md, CLAUDE.md, GEMINI.md, the docs/ seed) into an
                 existing project, asking per existing item:
                 [r]eplace (yours kept as <item>.bak)  [s]kip  [m]erge (folders: add missing files only)
                 [R]/[S]/[M] same answer for the rest  [a]bort
  --replace-all | --skip-all | --merge-all   answer every collision without a terminal (CI)
Related: aix upgrade (update an already installed project), aix doctor (check the result).""",

"upgrade": """aix upgrade [PROJECT] [--dry-run] [--yes]   (experimental)

Brings a project created with `aix install --into` up to the kit version of the `aix` you run. Run the KIT's aix
(the one on PATH) from inside the project; the project's own copy refuses, because the newest logic must come
from the kit. Ownership decides what happens:
  kit-owned, overwritten, removed if gone from the kit:
                 .aix/scripts, .aix/bin, .aix/templates, .aix/meta-docs, .aix/skills/<built-in categories>, CLAUDE.md
  merged:        AGENTS.md and GEMINI.md (kit text + your "## Always-on skills" and "## Project notes"),
                 .aix/config.yaml (your disabled_skills line kept)
  never touched: docs/requirements tests security conflicts operations road-map, .aix/skills/extern/, runtime folders,
                 your code
Prints the full plan, one line per file (line deltas, kept sections, removals), then warns and asks.
  --dry-run      plan only, nothing written        --yes   skip the question (scripts)
Afterwards it relinks skills; run `aix doctor` and `aix docs validate`. Your git history is the backup.""",

"docs validate": """aix docs validate

Are the DOCS right? Exit 1 on errors. Checks every markdown file under docs/ and skills/:
  - front-matter present; skill `name` equals its folder path
  - every folder has an INDEX.md and every file is listed in it
  - every referenced ID (FR/NFR/API/DM/ADR/TS/VUL/TASK/CONFLICT) exists; relative links resolve
  - test specs cover existing requirements; vulnerability statuses are valid
  - API/DM field names appear in the field dictionary
  - STATUS DRIFT: FR/NFR/API `implemented`/`verified` need an @implements marker in code, TS `automated` needs
    @tests, VUL `mitigated` needs @mitigates, and any VUL status beyond `expected` needs an audit report
    (`accepted` also an ADR). A doc may not claim more than the code and the evidence show.
Run before every hand-off and in CI. `aix doctor` is the counterpart for the installation.""",

"doctor": """aix doctor

Is the INSTALL right? Exit 1 if anything is broken; every finding comes with its fix. Checks Python >= 3.9,
`aix` on PATH, the pointer files (CLAUDE.md, .github/copilot-instructions.md, .cursor/rules/aix.mdc, GEMINI.md)
reaching AGENTS.md, every enabled skill linked in all runtime folders, dangling links, unknown names in
disabled_skills, always-on sections consistent across AGENTS.md / Copilot / Cursor / Gemini, extern skills with
provenance, and STATE.md naming a task that exists in going-on/. `aix docs validate` is the counterpart for the docs.""",

"docs coverage": """aix docs coverage

Regenerates docs/tests/coverage-matrix.md: one row per requirement with the test specs that cover it (`covers:`
in TS files), the code that implements it (@implements markers) and the tests that exercise it (@tests markers),
plus a gap column: `no test spec`, `spec not automated`, `no code`. Pure regex scan, no model. Only as honest as
the markers: `aix docs validate` fails a status that claims more than the markers show.""",

"docs security": """aix docs security [open|validated] [--gate]

Where does the vulnerability register stand? Reads docs/security/vulnerability-register.md and the audit reports.
  NOT VALIDATED   rows still expected / unverified / confirmed / mitigated, worst first, with the audit skill to run
  VALIDATED       addressed with evidence, accepted by ADR, or not-applicable
  PROBLEM         a status beyond `expected` with no audit report mentioning the VUL (or `accepted` without ADR)
  --gate          release check: exit 1 if any row is open or lacks evidence
The audits themselves are done by the security-audit-* skills; this only reports and gates.""",

"code graph": """aix code graph [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report] [--selftest]     alias: aix code complexity

THE MODULARITY METRIC. Distance between the real dependency graph and its ideal: the lowest complexity that still
delivers every dependency the code has. The ideal is a baseline, achievable or not; the same baseline for every
project makes the numbers comparable. 0 % = at the baseline.

What it builds
  modules (default)   nodes = source files; edges = imports between project files. Python, JavaScript/TypeScript,
                      Rust, Java. External packages ignored; unresolved imports ignored, never guessed.
  --functions         nodes = functions/methods (Python only, stdlib parser); edges = calls resolved by name in the
                      module, through imported names, and self.method(). Calls through typed objects cannot be
                      resolved statically: the function graph is a lower bound.
  PATH...             restrict to these folders (default: backend frontend shared infra src app tests lib)

Normalisations (all reported)
  facades collapsed   an __init__.py / index.ts / mod.rs that only re-exports its own folder is a name, not a
                      module; edges into it go to what it re-exports.
  stable nodes        instability I = out / (in + out) (Martin 1994). I <= 0.25 = stable: value types, models,
                      ports, pure helpers. Depending on a stable node is free reuse (modularity.md); edges into
                      stable nodes are not complexity. Replaces the naive "leaf = no dependencies" rule.
  wiring              edges out of composition roots (composition.py, main.py, app.py, index.ts ...) and tests
                      are never shortcuts: wiring and exercising many modules directly is their job.

The measurement
  complexity          edges into non-stable nodes.
  ideal complexity    transitive reduction (Aho, Garey & Ullman 1972) of the graph with each cycle contracted to
                      one node: the smallest graph with exactly the same reachability. Unique. Every dependency
                      is kept; only shortcuts go (A -> C while A -> B -> C), and each cycle of k nodes is counted
                      at its acyclic minimum, k-1 edges.
  reducible           (complexity - ideal) / ideal in %. THE number. Every counted edge is listed:
                        SHORTCUT  A -> C  also reached via B      drop A -> C, or route C through B
                        cycle edges beyond the minimum            break the cycle
  upward              not part of reducible, listed and gated on their own: an edge into a composition root, or
                      from a lower layer into a higher one (models/core 1 < adapters/ports 2 < services 3 <
                      controllers 4, by folder name). Wrong direction is a defect regardless of reachability.
  cycles              strongly connected components; each listed. Defects.
  hubs                fan-in >= 3 AND fan-out >= 3; composition roots labelled as hubs by design.
  propagation cost    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006).
  NCCD                Lakos' normalised cumulative component dependency: CCD / CCD of a balanced binary tree of
                      the same size. 1.0 = as coupled as an ideal tree, above = more coupled.
  modularity Q        Newman-Girvan Q of the folder partition at depths 1, 2, 3: ~0 = folders mean nothing
                      structurally, 0.3-0.7 = real clusters with few edges between them.

How to read the result
  cycles or upward > 0       fix first; these are facts, not candidates
  SHORTCUT lines             each is one removable edge; the bypass names the intermediate to route through
  reducible                  distance from the baseline; compare across time and across projects
  NCCD, Q                    shape: tree-likeness and folder cohesion; trend indicators
  a hub that is not a root   split it: keep the stable part, move the rest up to its callers

Dead code (--dead)
  DEAD MODULES        files no entry module reaches through imports. Entry modules are live by definition:
                      composition roots and entry points (main, app, index, server, manage, wsgi, cli, ...),
                      tests, tool/framework config, facades, and any Python file with an `if __name__ ==
                      "__main__"` guard. Reachability, not fan-in: an orphan cluster importing itself is dead.
  DEAD FUNCTIONS      with --functions, Python only: a function or method whose simple name is never referenced
                      anywhere else, as a bare name or an attribute. Decorated functions (routes, fixtures,
                      commands are called by the framework), dunder and implicit names, `__all__` exports and
                      entry/test code are excluded. Name-based like vulture, so a method called through any object
                      of the same name is live: conservative, few false positives, some misses.
  Every line is a candidate: confirm nothing reaches it by string, reflection or a framework before deleting.
  aix code dead --gate fails on any candidate.

Clones (--clones)
  EXACT               groups of functions with the same normalised structure: identifiers -> role, literals ->
                      type, docstrings and comments dropped (clone types 1-2, Roy & Cordy 2007). Found exactly by
                      hashing; Python via the parser, JS/TS/Rust/Java via normalised tokens of the function body.
  NEAR                pairs sharing >= --similarity % (default 70) of winnowed fingerprints (Schleimer, Wilkerson
                      & Aiken 2003, the MOSS algorithm; k-grams of 5 tokens): clone type 3, the copied-and-tweaked
                      function. Functions under 6 lines are ignored. Sorted by size x similarity: biggest wins first.
  Why: clones are the leaf that was never extracted, and clones later changed inconsistently are bugs (Juergens
  et al., ICSE 2009). Every line is a candidate: adapters of one port share a shape legitimately; merge only when
  they share a purpose. aix code clones --gate fails on exact groups only.

Options
  aix code dead         the dead-code report (see above); aix code clones the clone report (--similarity PCT)
  --gate                exit 1 on any cycle, any upward dependency, or reducible > --max-reducible PCT (CI)
  --report              also write docs/tests/dependency-graph.md (generated, git-ignored)
  --selftest            run the built-in cases with known answers (chain, diamond, shortcut, cycle, reuse, layer skip, upward)

Coverage: static analysis. The graph is only as complete as the imports/calls it can resolve; the tool never guesses.
Used by: review-code-review on every diff (compare before/after), architecture-design-app, the definition of done.""",

"task": """aix task new "Title" [--bucket next|backlog|ideas] | start ID | block ID "reason" | done ID | list

Moves TASK-* files through the road-map and keeps docs/road-map/going-on/STATE.md in sync:
  pending/{ideas,backlog,next}  ->  going-on  <->  blocked  ->  completed/YYYY-MM/
  new     create pending/<bucket>/TASK-nnnn-title.md from .aix/templates/task.md
  start   move to going-on/, status going-on, STATE.md active_task = ID
  block   move to blocked/, note the reason, clear active_task
  done    move to completed/YYYY-MM/ (creating the month INDEX), stamp the date, clear active_task
  list    one line per task with status
Never move task files by hand; agents use this through the core-roadmap-task skill.""",

"refactor": """The refactor skills (aix skills refactor)

One skill per `aix code` finding type; each says how to fix it safely, how to verify (re-run the tool, run the
tests) and what to write in the hand-off. One finding per change.
  refactor-cycle        CYCLE / UPWARD: extract the shared part into a leaf, or invert through a port
  refactor-shortcut     SHORTCUT: use the intermediate's result, move the type to a stable module, or split
  refactor-hub          HUB (not a root): split by stability, the stable part becomes a leaf
  refactor-dead         DEAD MODULE / FUNCTION: prove unreachable (grep strings, frameworks), delete, test
  refactor-clone        EXACT / NEAR: extract the identical part as a leaf, parametrise the difference
  refactor-readability  OVER metric: nesting, cognitive, cyclomatic, lines, parameters, one metric per change
  refactor-modernise    modernise line: one construct per change, no behaviour change
Every report names the skill on its last line; review-code-review proposes it; core-sdd-workflow runs it.""",

"skills": """aix skills [list|general|specific [category]] | info NAME | show NAME | enable|disable NAME...
           | registry [general|specific] | add NAME... [--on-demand|--always] [--extra a,b] | remove NAME... | update [NAME...]
           | always NAME | on-demand NAME

Catalogue: SKILL, STATE, DESCRIPTION (cut at the terminal width). States:
  recommended / available   known in .aix/skills/extern/registry.json, not downloaded (listed first)
  (*) always                named in AGENTS.md: applied in every session
  on-demand                 installed; invoked by name, by an orchestrator, or when its description matches
  disabled                  listed in .aix/config.yaml disabled_skills; linked into no runtime
Groups (filters): general = behaviour that applies to every session (style, method); specific = one job.
  info      group, level (always/orchestrator/on-demand), category, runtimes it is linked into, source
  add       download a registry skill (GitHub tarball, no git) into .aix/skills/extern/NAME, bare name, linked
            everywhere; general skills become always-on unless --on-demand; --extra adds siblings from the repo
  always    write the "## Always-on skills" section into AGENTS.md, .github/copilot-instructions.md,
            .cursor/rules/aix.mdc and GEMINI.md (no runtime has an always-apply switch; the instruction files are
            the only mechanism every tool honours); on-demand removes it
  registry  the known third-party skills with their evidence line (only entries with evidence belong there)""",

"about": "aix about      prints the full description of the kit: purpose, workflow, folders, IDs, skills, every command.",
"version": "aix version    prints the kit version from .aix/config.yaml.",
"help": "aix help [COMMAND]    this list, or the detailed help for one command or group (e.g. aix help code dead; also: aix code dead --help).",
}
TOPICS["code style"] = """aix code style [TARGET...] [--all] [--gate] [--report] [--selftest]

READABILITY, per function, with specific feedback. TARGET is a folder, a file (extension optional), or one
function: path:func, path/func, path::Class.method. A folder or file gives a table ranked worst first; a single
function gives a card: each metric against its limit, then every finding with its line and what to do.

Metrics and limits (.aix/config.yaml `style:` block; sources in .aix/meta-docs/conventions/readability.md)
  lines                  60   NASA/JPL one page; McConnell: a ceiling, not a target
  cognitive complexity   15   Campbell / SonarSource 2017: nesting and breaks in linear flow; built for readability
  cyclomatic complexity  10   McCabe 1976: independent paths = tests needed
  nesting depth           4   Kernighan & Plauger, McConnell
  parameters              5   pylint default; McConnell's hard limit 7
  file lines            400
Advice (not gated): naming (language casing, single-letter names outside loops), missing docstring on a public
function, magic numbers. Evidence for names: Lawrie 2006, Butler 2010, Hofmeister 2017.

Feedback is concrete: "72 lines: the deepest block is lines 40-58, extract it", "cognitive 31: biggest costs at
line 12 (loop, nesting +2) ...", "nesting 5 at lines 44-52: invert the condition and return early",
"6 parameters: group them into one object".

Python is measured exactly (stdlib parser, Sonar's cognitive rules). JS/TS, Rust and Java are measured from
tokens and braces: close for lines, parameters and nesting, approximate for complexity.

Modernise (advice tier, never gated): the report detects the runtime the project targets (pyproject
requires-python, .python-version, the venv, tsconfig target, engines.node, Cargo.toml, pom/Gradle; the header
names the source) and suggests only what that version enables: if/elif ladder -> match (3.10+), Optional[X] ->
X | None (3.10+), typing.List -> list (3.9+), assign-only __init__ -> @dataclass (3.7+), os.path -> pathlib,
toml -> tomllib (3.11+), a && a.b -> a?.b and x !== undefined ? x : d -> x ?? d (ES2020+), var -> const/let,
unwrap-only match -> let-else (Rust 1.65+), switch with breaks -> switch expression (Java 14+).
"Python on PATH (assumed)" means nothing in the project declares a version: declare it in pyproject.
  --gate      exit 1 if any function is over a limit or any file too long (advice never fails the gate)
  --all       full table instead of the top 30
  --report    also write docs/tests/code-style.md
  --selftest  known-answer cases (Sonar's example scores 9, a five-deep nest scores 5, ...)
Examples
  aix code style backend                       ranked table
  aix code style backend/app/notes/services/note_service:create   one function, full card
  aix code style frontend/src/app/App.tsx::handleSaveNote
The stack linters enforce the same limits in the editor: stacks/<lang>/tooling."""

TOPICS["code security"] = """aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]

DETERMINISTIC SECURITY SCAN, mapped to the vulnerability register. Every rule names the VUL row it feeds and the
CWE it detects, so a finding is evidence the register can act on. Rules follow bandit, semgrep, gitleaks and
eslint-plugin-security; categories follow the OWASP Top 10 and the seeded register. No dependencies.

What it checks (Python, JS/TS, Rust, Java, plus Dockerfiles, compose, manifests, env files)
  VUL-INJ-001/002    SQL built from strings; shell commands (shell=True, exec/system); eval; template strings;
                     paths from request input                                             CWE-89/78/95/1336/22
  VUL-INPUT-001/002  pickle/marshal/yaml.load without SafeLoader, ObjectInputStream, XML entities  CWE-502/20
  VUL-SECRET-001/002 private keys, cloud/API tokens, hard-coded passwords; TLS verification off; DEBUG on;
                     ALLOWED_HOSTS *                                                       CWE-798/295/489/16
  VUL-AUTHN-001/002  md5/sha1 for passwords, random for tokens; JWT unverified / alg none; cookies without
                     Secure/HttpOnly                                                       CWE-328/338/347/614
  VUL-WEB-001/002/003 innerHTML/dangerouslySetInnerHTML/mark_safe; CSRF disabled; CORS *; open redirect
                                                                                          CWE-79/352/942/601
  VUL-LOG-001        credentials in log/print lines                                        CWE-532
  VUL-AI-001/002     prompts built by interpolation; LLM calls without an output limit      CWE-77/770
  VUL-INFRA-001      chmod 777, privileged containers, Dockerfile without USER              CWE-732/250
  VUL-DEP-001        unpinned requirements, unbounded npm ranges, missing lockfiles, FROM without tag  CWE-1104

How to read it
  A match is a FINDING TO REVIEW, never proof of exploitability; a row with no match is not proven clean. The
  report says both. Findings in test code are listed but not gated (--strict gates them too).
  Reviewed and accepted? Mark the line:   # aix: accepted VUL-INJ-002 <why>   (listed, never hidden)

The important part: --audit
  Writes docs/security/audits/AUDIT-<date>-code.md from .aix/templates/audit-report.md with the findings table filled
  (asset, control, evidence file:line, status before -> "confirmed? review"), and rows for every rule that matched
  nothing ("unverified by scan alone"). That file is the evidence `aix docs validate` and `aix docs security`
  require before a VUL status may change; a human (or the security-audit-* skills) completes the Status column.

Options
  --strict    gate on test-code findings as well      --gate    exit 1 if any finding to review remains
  --audit     write the audit report + INDEX row       --report  write docs/tests/code-security.md
  --selftest  known-vulnerable snippets must be found, safe variants must not
Related: aix docs security (register state), skills security-audit-* (reasoning on the hits), security-threat-model."""

TOPICS["code stats"] = """aix code stats [PATH...] [--metric lines|cognitive|cyclomatic|nesting|params] [--report] [--selftest]

THE SHAPE OF THE CODE BASE in one screen: where function sizes sit, how spread they are, and who is pulling the
tail. Uses the same per-function measurements as `aix code style`.

  histogram    fixed bins (1-5, 6-10, 11-20, 21-30, 31-40, 41-60, 61-100, 101-200, 201+ lines), so two projects or
               two dates compare directly; bars scaled to the terminal width, half blocks for resolution; the bin
               holding the limit and every bin above it are marked
  numbers      functions, mean, sample standard deviation, median, p90, p95, max, and how many sit over the
               .aix/config.yaml limit (tests and framework-decorated functions use their adjusted limits)
  offenders    the ten largest functions (* = over its limit); the five files and five folders (depth 2) that push
               the most functions over the limit, with the total excess

Reading it: a healthy code base is right-skewed with a short tail: most functions in 1-20, p90 under the limit,
a handful of large ones you can name. A fat tail or a high sd means size is not being managed; the offender
lists say where to start (`aix code style FILE:FUNCTION` for the card, skill refactor-readability to fix).
--metric switches the whole view to cognitive or cyclomatic complexity, nesting depth or parameter count.
--report writes docs/tests/code-stats.md. Python exact; JS/TS, Rust, Java approximate (as in aix code style)."""

TOPICS["code"] = """aix code graph | complexity | dead | clones | style | security | stats   [TARGET...] [--gate] [--report]

Three tools on one engine (.aix/scripts/graph.py). All read the same dependency graph of the project's source
(Python, JS/TS, Rust, Java modules; Python functions with --functions); PATH... limits the folders.
  aix code graph      the modularity metric: real graph vs its ideal (transitive reduction) = reducible %,
                      cycles, upward dependencies, hubs, propagation cost, NCCD, folder Q.  alias: complexity
  aix code dead       dead code: modules no entry point reaches; with --functions, Python functions never referenced
  aix code clones     duplicated functions: exact groups (same structure) and near-clones (--similarity PCT)
  aix code style      readability per function: lines, cognitive/cyclomatic complexity, nesting, parameters,
                      names, docstring, magic numbers; one function = a card with line-numbered advice
  aix code security   static security checks mapped to VUL rows and CWEs; --audit writes the audit evidence
  aix code stats      histogram of function sizes (or any style metric) with mean/sd/percentiles and offenders
--gate turns each into a CI check; --report writes docs/tests/dependency-graph.md; aix code graph --selftest
proves the arithmetic on known-answer cases. Details: aix help code graph | code dead | code clones | code style | code security | code stats."""
TOPICS["docs"] = """aix docs validate | coverage | security

  aix docs validate   are the DOCS right? front-matter, INDEXes, IDs, links, TS -> FR, VUL statuses, field
                      dictionary, status drift (implemented/automated/mitigated without the code marker), VUL
                      evidence. CI gate, exit 1 on errors.
  aix docs coverage   regenerate docs/tests/coverage-matrix.md: requirement -> test spec -> code -> gaps.
  aix docs security   the vulnerability register: validated rows vs not, audit skills still to run, statuses
                      without evidence; --gate is the release check.
Details: aix help docs validate | docs coverage | docs security."""
TOPICS["code complexity"] = TOPICS["code graph"]
TOPICS["code dead"] = TOPICS["code graph"]
TOPICS["code clones"] = TOPICS["code graph"]
for _old, _new in (("graph", "code graph"), ("complexity", "code graph"), ("validate", "docs validate"), ("coverage", "docs coverage"), ("security", "docs security")):
    TOPICS[_old] = TOPICS[_new]


def topic_help(name: str):
    text = TOPICS.get(name)
    if not text:
        print(f"aix: no help for '{name}'. Topics: install, upgrade, doctor, code, code graph, code dead, code clones, code style, code security, code stats, refactor, docs, docs validate, docs coverage, docs security, task, skills, about, version")
        sys.exit(1)
    print(text)


def usage(code=0):
    print(f"AIX {version()}\n")
    print(__doc__.replace("{n}", str(skill_count())))
    sys.exit(code)


def run_script(name):
    """Run a sibling script in a subprocess so its module-level main() stays untouched."""
    return subprocess.call([sys.executable, str(HERE / name)])


def version():
    for line in (ROOT / ".aix" / "config.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].split("#")[0].strip()
    return "unknown"


def expose_on_path():
    """Best effort: make `aix` callable from anywhere. Never edits shell profiles or the registry."""
    if os.name == "nt":
        print(f"PATH: add {ROOT} to your PATH to call `aix` from anywhere (aix.cmd lives there).")
        return
    bin_dir = Path.home() / ".local" / "bin"
    if not bin_dir.is_dir():
        print(f"PATH: {bin_dir} does not exist; call ./.aix/bin/aix from the repo or add {ROOT} to PATH.")
        return
    link = bin_dir / "aix"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(ROOT / ".aix" / "bin" / "aix")
    on_path = str(bin_dir) in os.environ.get("PATH", "").split(os.pathsep)
    print(f"PATH: linked {link} -> {ROOT / '.aix' / 'bin' / 'aix'}" + ("" if on_path else f" (add {bin_dir} to PATH)"))


def cmd_install(args):
    import install_skills as inst
    copy, into = "--copy" in args, None
    if "--into" in args:
        i = args.index("--into")
        if i + 1 >= len(args):
            sys.exit("aix install --into needs a directory")
        into = Path(args[i + 1]).resolve()
    if into:
        mode = "replace" if "--replace-all" in args else "skip" if "--skip-all" in args else "merge" if "--merge-all" in args else "ask"
        inst.copy_kit_into(into, mode)
        inst.install_into(into, copy)
    else:
        inst.install_into(inst.KIT_ROOT, copy)
        expose_on_path()


def cmd_task(args):
    import roadmap as rm
    if not args:
        usage(1)
    sub, rest = args[0], args[1:]
    if sub == "new" and rest:
        bucket = rest[2] if len(rest) > 2 and rest[1] == "--bucket" else "next"
        rm.cmd_new(rest[0], bucket)
    elif sub == "start" and rest:
        rm.cmd_start(rest[0])
    elif sub == "block" and rest:
        rm.cmd_block(rest[0], rest[1] if len(rest) > 1 else "")
    elif sub == "done" and rest:
        rm.cmd_done(rest[0])
    elif sub == "list":
        rm.cmd_list()
    else:
        usage(1)


ALIASES = {"graph": ["code", "graph"], "complexity": ["code", "graph"], "validate": ["docs", "validate"],
           "coverage": ["docs", "coverage"], "security": ["docs", "security"]}
CODE_MODES = {"graph": [], "complexity": [], "dead": ["--dead"], "clones": ["--clones"]}


def run_code(args):
    if args and args[0] == "style":
        import style
        return style.main(args[1:])
    if args and args[0] == "security":
        import codesecurity
        return codesecurity.main(args[1:])
    if args and args[0] == "stats":
        import stats
        return stats.main(args[1:])
    import graph
    sub = args[0] if args and args[0] in CODE_MODES else "graph"
    rest = args[1:] if args and args[0] in CODE_MODES else args
    graph.main(CODE_MODES[sub] + rest)


def run_docs(args):
    sub, rest = (args[0], args[1:]) if args else ("", [])
    if sub == "validate":
        sys.exit(run_script("validate.py"))
    if sub == "coverage":
        sys.exit(run_script("coverage_matrix.py"))
    if sub == "security":
        import security
        return security.main(rest)
    print("aix docs: validate | coverage | security [open|validated] [--gate]")
    sys.exit(1)


def main(argv):
    argv = list(argv)
    if argv and argv[0] in ALIASES:
        argv = ALIASES[argv[0]] + argv[1:]
    if len(argv) >= 2 and argv[0] == "help":
        return topic_help(" ".join(argv[1:]))
    if len(argv) >= 2 and argv[-1] in ("--help", "-h"):
        return topic_help(" ".join(argv[:-1]))
    reexec_in_project(argv)
    if not argv or argv[0] in ("help", "-h", "--help"):
        usage(0)
    cmd, args = argv[0], argv[1:]
    if cmd == "about":
        print(ABOUT)
    elif cmd == "install":
        cmd_install(args)
    elif cmd == "upgrade":
        import upgrade
        upgrade.main(args)
    elif cmd == "doctor":
        sys.exit(run_script("doctor.py"))
    elif cmd == "code":
        run_code(args)
    elif cmd == "docs":
        run_docs(args)
    elif cmd == "task":
        cmd_task(args)
    elif cmd == "skills":
        import skills
        skills.main(args)
    elif cmd in ("version", "-V", "--version"):
        print(f"AIX {version()}")
    else:
        print(f"aix: unknown command '{cmd}'\n")
        usage(1)


if __name__ == "__main__":
    main(sys.argv[1:])
