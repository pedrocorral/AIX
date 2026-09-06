#!/usr/bin/env python3
"""AIX is a spec-driven development kit for AI coding agents: documentation is the ground truth,
code is its implementation, and every change leaves a traceable trail. `aix install` puts everything
an agent needs to build any application into your project: {n} skills for specifying, designing,
implementing, testing, auditing and reviewing; design patterns and architecture guides (MVC,
frontend/backend split, persistence abstraction, ORM, testing, security); document templates; and
the road-map that lets work resume across sessions. `aix` then keeps the documentation consistent
and moves tasks between states. Run `aix about` for the full story.

Usage: aix <command> [args]   (no command = this help)
aix acts on the nearest project at or above the current folder (the one holding framework.yaml).

  aix about                           what AIX is, how it works, and what every command does
  aix install [--into DIR] [--copy]   link skills into agent runtimes; --into copies the kit into DIR first
  aix upgrade [PROJECT] [--dry-run] [--yes]
                                      bring a project's kit files up to this checkout: overwrites kit-owned paths
                                      (scripts, templates, docs/meta-docs, built-in skills, launchers), merges
                                      AGENTS.md and framework.yaml, never touches your docs, code or extern skills
      --into asks per existing item: [r]eplace [s]kip [m]erge [R/S/M] all [a]bort  (replace keeps <item>.bak)
      --replace-all | --skip-all | --merge-all   answer for every collision without asking (CI, no terminal)
  aix validate                        are the DOCS right? IDs, links, indexes, front-matter. CI gate, exit 1 on errors
  aix doctor                          is the INSTALL right? skill links, pointer files, always-on wiring, STATE.md,
                                      Python, PATH. Each problem comes with its fix
  aix coverage                        regenerate docs/tests/coverage-matrix.md (requirement -> test -> code gaps)
  aix graph | complexity [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report]
                                      the modularity metric: complexity vs ideal complexity (transitive reduction)
                                      = reducible %, plus cycles, shortcuts, hubs, propagation cost. Modules for
                                      Python, JS/TS, Rust, Java; --functions for Python call graphs. --gate: CI
  aix security [open|validated]       vulnerability register: which VUL rows are validated (evidence) and which
                                      are not, which audit skills still to run; --gate exits 1 if any row is open
  aix task new "Title" [--bucket next|backlog|ideas]
  aix task start|block|done TASK-0007 ["reason"]
  aix task list
  aix skills [general|specific] [cat] catalogue: name, state (always / on-demand / disabled), description
  aix skills info NAME                details: group, level, runtimes it is installed in, source
  aix skills show NAME                print a skill's SKILL.md
  aix skills enable|disable NAME...   link/unlink a skill everywhere; remembered in framework.yaml
  aix skills registry                 known third-party skills (caveman, ponytail, ...) with evidence
  aix skills add NAME [--on-demand]   download a registry skill into skills/extern/, link it everywhere;
                                      general skills become always-on (AGENTS.md + Copilot/Cursor pointers)
                                      unless --on-demand; specific ones stay on-demand unless --always
  aix skills remove|update NAME       drop it / re-download it;  aix skills always|on-demand NAME
  aix version
  aix help [COMMAND]                  detailed help for one command (e.g. aix help graph), or aix COMMAND --help

Launchers: `aix` (bash, Linux/macOS) and `aix.cmd` (Windows) simply call this file with python3."""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
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
terms; per-stack notes (Python, Java, JavaScript) live under docs/meta-docs/stacks/. AIX ships no runtime library
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
              10. close: aix validate, aix coverage, definition-of-done, task done, session handoff
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

Code carries markers in comments: @implements FR-..., @tests TS-..., @mitigates VUL-.... `aix coverage` scans them
(no LLM involved) and produces the matrix requirement -> test spec -> code -> gaps ("no test spec", "spec not
automated", "no code"). `aix validate` checks that every referenced ID exists, links resolve, each folder has an
INDEX that lists its files, front-matter is present, skill names match their paths, register statuses are valid and
API/DM field names appear in the field dictionary.

6. SKILLS  (skills/)
--------------------
Thirty-six small skills in the Agent Skills open format (SKILL.md with YAML front-matter), each doing one job,
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

The nested folder is the single source of truth. `aix install` links every leaf skill, under its flat name
(security/audit-injection -> security-audit-injection), into the folders each runtime reads:
.opencode/skills, .claude/skills, .github/skills, .agents/skills and .cursor/skills (.agents/skills is the
agentskills.io location read by Antigravity, Gemini CLI and VS Code). Never edit the installed copies; they are
ignored by git. Some skills bundle deterministic scripts/ (regex scans that are cheaper than
having the model read code) and references/.

7. THE CLI
----------
`aix` is a bash launcher (Linux, macOS) and `aix.cmd` a batch launcher (Windows). Both run scripts/aix.py with
Python 3.9+ and no third-party dependencies.

  aix                       version and command list (same as `aix help`)
  aix about                 this text
  aix version               kit version from framework.yaml

  aix install               link all skills into the five runtime folders of the current kit checkout; write
                            pointer files for Copilot, Cursor and Gemini CLI if missing; create road-map STATE.md if missing;
                            on Linux/macOS symlink `aix` into ~/.local/bin when that folder exists. Idempotent.
      --copy                copy skills instead of symlinking (filesystems without symlinks, some Windows setups)
      --into DIR            first copy the kit payload (AGENTS.md, CLAUDE.md, GEMINI.md, framework.yaml, docs/, skills/,
                            templates/, scripts/, aix, aix.cmd) into an existing project, then install there.
                            For every item that already exists it asks:
                              [r]eplace   move yours to <item>.bak, copy the kit's version
                              [s]kip      leave yours untouched
                              [m]erge     folders only: add the kit's missing files, never overwrite
                              [R] [S] [M] the same answer for every remaining collision
                              [a]bort     stop; items already added stay
      --replace-all | --skip-all | --merge-all
                            answer every collision without asking (CI, no terminal). Without a terminal and
                            without one of these flags the installer refuses to guess and exits.

  aix upgrade [PROJECT] [--dry-run] [--yes]
                            update a project created with `--into` to the kit version of the checkout whose
                            `aix` you run (so run the kit's aix, from PATH, inside the project). Kit-owned paths
                            are overwritten and files gone from the kit removed: scripts/, aix, aix.cmd,
                            templates/, docs/meta-docs/, skills/<built-in categories>/, CLAUDE.md.
                            AGENTS.md and GEMINI.md are replaced by the kit's text with the project's "## Always-on skills" and
                            "## Project notes" sections kept; framework.yaml keeps disabled_skills. Never touched:
                            docs/requirements, tests, security, conflicts, operations, road-map, skills/extern,
                            code. Shows the plan and asks; git is the backup.

  aix validate              documentation integrity check described in section 5; exit 1 on errors
  aix doctor                installation health: every skill linked in every runtime, no dangling links, pointer
                            files present, always-on sections consistent across AGENTS.md / Copilot / Cursor / Gemini,
                            extern skills updatable, STATE.md consistent, Python and PATH. Prints a fix per problem.
                            validate = is what we wrote right; doctor = is the tooling around it right.
  aix coverage              regenerate docs/tests/coverage-matrix.md
  aix graph [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report]
                            the modularity metric (alias: aix complexity). Builds the dependency graph (modules:
                            Python, JS/TS, Rust, Java via imports; --functions: Python call graph), collapses
                            re-export facades, sets leaves aside (reusing a leaf is free), then compares the
                            inner graph's complexity (its edges) with its ideal complexity: the transitive
                            reduction (Aho, Garey & Ullman 1972), the smallest graph with the same reachability.
                            reducible % = what could be removed today without losing a dependency: shortcuts
                            (layer skips) and cycle edges. 0 % = ideal. Also cycles, hubs, propagation cost and
                            the diamond shape (circuit rank) for the trend. `aix help graph` explains it fully.
  aix validate              documentation integrity check described in section 5; exit 1 on errors
  aix doctor                installation health: every skill linked in every runtime, no dangling links, pointer
                            files present, always-on sections consistent across AGENTS.md / Copilot / Cursor / Gemini,
                            extern skills updatable, STATE.md consistent, Python and PATH. Prints a fix per problem.
                            validate = is what we wrote right; doctor = is the tooling around it right.
  aix coverage              regenerate docs/tests/coverage-matrix.md
  aix security [open|validated] [--gate]
                            state of the vulnerability register: rows not validated (expected, unverified,
                            confirmed, mitigated; worst first) with the audit skill to run, rows validated
                            (addressed, accepted, not-applicable), and rows whose status has no evidence (an
                            audit report in docs/security/audits/, plus an ADR for `accepted`). The audits are
                            done by the security-audit-* skills; this only reports. --gate is the release check.

  aix task new "Title" [--bucket next|backlog|ideas]
                            create pending/<bucket>/TASK-nnnn-title.md from the template
  aix task start TASK-nnnn  move to going-on/, set status, point STATE.md at it
  aix task block TASK-nnnn "reason"
                            move to blocked/, note the reason, clear the active task
  aix task done TASK-nnnn   move to completed/YYYY-MM/, stamp the date, clear the active task
  aix task list             one line per task with status

  aix skills [list [category]]
                            every skill with its activation level, enabled/disabled state and the runtimes it
                            is installed in. Levels are derived, not configured:
                              always        named in AGENTS.md, so every session runs or may need them
                                            (session-resume, sdd-workflow, session-handoff, conflict-resolution)
                              orchestrator  entry points that chain other skills
                              on-demand     invoked by an orchestrator, by you, or when the description matches
  aix skills show NAME      print the skill's SKILL.md
  aix skills disable NAME   unlink it from every runtime and record it in framework.yaml `disabled_skills`
                            (aix install keeps it unlinked); warns if AGENTS.md depends on it
  aix skills enable NAME    the reverse

8. GETTING STARTED
------------------
  New project:      git clone <aix> my-app && cd my-app && ./aix install
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
    return sum(1 for _ in (ROOT / "skills").rglob("SKILL.md"))


ANYWHERE = {"help", "-h", "--help", "about", "version", "-V", "--version"}  # need no project


def reexec_in_project(argv):
    """Run the project's own copy of the CLI so every module resolves ROOT to the project, not to this checkout."""
    if argv[:1] == ["upgrade"]:
        return  # upgrade must run from THIS checkout's scripts, not the project's older copy
    project = find_project(Path.cwd())
    if project is None:
        if argv and argv[0] in ANYWHERE or (argv[:1] == ["install"] and "--into" in argv) or argv[:2] == ["skills", "registry"]:
            return
        sys.exit("aix: not inside an AIX project (no framework.yaml here or above). "
                 "Use `aix install --into DIR` to add AIX to a project, or cd into one.")
    own = project / "scripts" / "aix.py"
    if project != ROOT and own.exists():
        os.execv(sys.executable, [sys.executable, str(own), *argv])
    if project != ROOT:
        sys.exit(f"aix: {project} has framework.yaml but no scripts/aix.py; run `aix install --into {project}`")



TOPICS = {
"install": """aix install [--copy] [--into DIR] [--replace-all|--skip-all|--merge-all]

Links every enabled skill from skills/ into the folders each agent runtime reads (.opencode/skills, .claude/skills,
.github/skills, .agents/skills, .cursor/skills), writes the pointer files for Copilot, Cursor and Gemini CLI if
missing, creates docs/road-map/going-on/STATE.md if missing, prunes dangling links, and on Linux/macOS links `aix`
into ~/.local/bin when that folder exists. Idempotent: run it after adding, removing or editing skills.
  --copy         copy skill folders instead of symlinking (filesystems or Windows setups without symlinks)
  --into DIR     first copy the kit payload (AGENTS.md, CLAUDE.md, GEMINI.md, framework.yaml, docs/, skills/,
                 templates/, scripts/, aix, aix.cmd) into an existing project, asking per existing item:
                 [r]eplace (yours kept as <item>.bak)  [s]kip  [m]erge (folders: add missing files only)
                 [R]/[S]/[M] same answer for the rest  [a]bort
  --replace-all | --skip-all | --merge-all   answer every collision without a terminal (CI)
Related: aix upgrade (update an already installed project), aix doctor (check the result).""",

"upgrade": """aix upgrade [PROJECT] [--dry-run] [--yes]   (experimental)

Brings a project created with `aix install --into` up to the kit version of the `aix` you run. Run the KIT's aix
(the one on PATH) from inside the project; the project's own copy refuses, because the newest logic must come
from the kit. Ownership decides what happens:
  kit-owned, overwritten, removed if gone from the kit:
                 scripts/, aix, aix.cmd, templates/, docs/meta-docs/, skills/<built-in categories>/, CLAUDE.md
  merged:        AGENTS.md and GEMINI.md (kit text + your "## Always-on skills" and "## Project notes"),
                 framework.yaml (your disabled_skills line kept)
  never touched: docs/requirements tests security conflicts operations road-map, skills/extern/, runtime folders,
                 your code
Prints the full plan, one line per file (line deltas, kept sections, removals), then warns and asks.
  --dry-run      plan only, nothing written        --yes   skip the question (scripts)
Afterwards it relinks skills; run `aix doctor` and `aix validate`. Your git history is the backup.""",

"validate": """aix validate

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
provenance, and STATE.md naming a task that exists in going-on/. `aix validate` is the counterpart for the docs.""",

"coverage": """aix coverage

Regenerates docs/tests/coverage-matrix.md: one row per requirement with the test specs that cover it (`covers:`
in TS files), the code that implements it (@implements markers) and the tests that exercise it (@tests markers),
plus a gap column: `no test spec`, `spec not automated`, `no code`. Pure regex scan, no model. Only as honest as
the markers: `aix validate` fails a status that claims more than the markers show.""",

"security": """aix security [open|validated] [--gate]

Where does the vulnerability register stand? Reads docs/security/vulnerability-register.md and the audit reports.
  NOT VALIDATED   rows still expected / unverified / confirmed / mitigated, worst first, with the audit skill to run
  VALIDATED       addressed with evidence, accepted by ADR, or not-applicable
  PROBLEM         a status beyond `expected` with no audit report mentioning the VUL (or `accepted` without ADR)
  --gate          release check: exit 1 if any row is open or lacks evidence
The audits themselves are done by the security-audit-* skills; this only reports and gates.""",

"graph": """aix graph [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report]     alias: aix complexity

THE MODULARITY METRIC. How much of the codebase's dependency complexity could be removed without losing a single
dependency: 0 % = you are at the ideal complexity for the dependencies you have.

What it builds
  modules (default)   nodes = source files; edges = imports between project files. Python, JavaScript/TypeScript,
                      Rust, Java. External packages ignored; unresolved imports ignored, never guessed.
  --functions         nodes = functions and methods (Python only, stdlib parser); edges = calls resolved by name
                      in the module, through imported names, and self.method(). Calls through typed objects
                      (repo.save()) cannot be resolved statically: the function graph is a lower bound.
  PATH...             restrict to these folders (default: backend frontend shared infra src app tests lib)

Two normalisations before measuring
  facades collapsed   an __init__.py / index.ts / mod.rs that only re-exports its own folder is a name, not a
                      module; edges into it go to what it re-exports. Importing a package and its submodule is
                      one dependency, not two.
  leaves excluded     a leaf (no dependencies: pure functions, value types, parsers) may be reused by anyone for
                      free (docs/meta-docs/architecture/modularity.md). Edges INTO leaves are not complexity.
                      What remains is the inner graph.

What it measures (inner graph, E edges)
  complexity          E, the edges of the inner graph.
  ideal complexity    the edges of its transitive reduction (Aho, Garey & Ullman 1972): the smallest graph with
                      exactly the same reachability. Every dependency path is kept; only two things go:
                        shortcuts   A -> C while A -> B -> C already exists: a layer skip, or a type that should
                                    arrive through B. Edges out of composition roots and tests are exempt (wiring).
                        cycles      each strongly connected component of k nodes keeps k-1 edges; the rest are
                                    defects (two nodes that depend on each other are one node in disguise).
  reducible           (complexity - ideal) / ideal in %. THE number. 10 % = one tenth of the edges could be
                      removed today without changing what depends on what. 0 % = nothing to reduce.
  propagation cost    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006):
                      how much of the system one change can touch. Invariant under shortcut removal, which is
                      why shortcuts are pure cost. Healthy systems sit low (~5-15 %).
  shape               circuit rank E - N + P (Berge; McCabe's number is the same formula inside one function),
                      shown as % above a forest. Diamonds, two genuine paths converging on one node, raise it and
                      are NOT reducible: a layered app is diamond-rich by design. Reported for the trend only.
  hubs                fan-in >= 3 AND fan-out >= 3; composition roots are labelled as hubs by design.

How to read the result
  cycles > 0                 fix first: extract the shared part into a leaf, or merge the two nodes
  SHORTCUT lines             each is one removable edge; either drop the direct import or make the target a leaf
  reducible rising           coupling is growing faster than the dependencies justify
  a hub that is not a root   split it: keep the pure part as a leaf, move the rest up to its callers

Options
  --gate                exit 1 on any cycle, or when reducible > --max-reducible PCT (CI)
  --report              also write docs/tests/dependency-graph.md (generated, git-ignored)

Examples
  aix graph                        whole project, module level
  aix graph backend --functions    Python call graph of the backend
  aix graph --gate --max-reducible 20
Used by: review-code-review on every diff (compare before/after), architecture-design-app, the definition of done.""",

"task": """aix task new "Title" [--bucket next|backlog|ideas] | start ID | block ID "reason" | done ID | list

Moves TASK-* files through the road-map and keeps docs/road-map/going-on/STATE.md in sync:
  pending/{ideas,backlog,next}  ->  going-on  <->  blocked  ->  completed/YYYY-MM/
  new     create pending/<bucket>/TASK-nnnn-title.md from templates/task.md
  start   move to going-on/, status going-on, STATE.md active_task = ID
  block   move to blocked/, note the reason, clear active_task
  done    move to completed/YYYY-MM/ (creating the month INDEX), stamp the date, clear active_task
  list    one line per task with status
Never move task files by hand; agents use this through the core-roadmap-task skill.""",

"skills": """aix skills [list|general|specific [category]] | info NAME | show NAME | enable|disable NAME...
           | registry [general|specific] | add NAME... [--on-demand|--always] [--extra a,b] | remove NAME... | update [NAME...]
           | always NAME | on-demand NAME

Catalogue: SKILL, STATE, DESCRIPTION (cut at the terminal width). States:
  recommended / available   known in skills/extern/registry.json, not downloaded (listed first)
  (*) always                named in AGENTS.md: applied in every session
  on-demand                 installed; invoked by name, by an orchestrator, or when its description matches
  disabled                  listed in framework.yaml disabled_skills; linked into no runtime
Groups (filters): general = behaviour that applies to every session (style, method); specific = one job.
  info      group, level (always/orchestrator/on-demand), category, runtimes it is linked into, source
  add       download a registry skill (GitHub tarball, no git) into skills/extern/NAME, bare name, linked
            everywhere; general skills become always-on unless --on-demand; --extra adds siblings from the repo
  always    write the "## Always-on skills" section into AGENTS.md, .github/copilot-instructions.md,
            .cursor/rules/aix.mdc and GEMINI.md (no runtime has an always-apply switch; the instruction files are
            the only mechanism every tool honours); on-demand removes it
  registry  the known third-party skills with their evidence line (only entries with evidence belong there)""",

"about": "aix about      prints the full description of the kit: purpose, workflow, folders, IDs, skills, every command.",
"version": "aix version    prints the kit version from framework.yaml.",
"help": "aix help [COMMAND]    this list, or the detailed help for one command (also: aix COMMAND --help).",
}
TOPICS["complexity"] = TOPICS["graph"]


def topic_help(name: str):
    text = TOPICS.get(name)
    if not text:
        print(f"aix: no help for '{name}'. Commands: " + ", ".join(k for k in TOPICS if k != "complexity"))
        sys.exit(1)
    print(text)


def usage(code=0):
    print(f"aix {version()}\n")
    print(__doc__.replace("{n}", str(skill_count())))
    sys.exit(code)


def run_script(name):
    """Run a sibling script in a subprocess so its module-level main() stays untouched."""
    return subprocess.call([sys.executable, str(HERE / name)])


def version():
    for line in (ROOT / "framework.yaml").read_text(encoding="utf-8").splitlines():
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
        print(f"PATH: {bin_dir} does not exist; call ./aix from the repo or add {ROOT} to PATH.")
        return
    link = bin_dir / "aix"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(ROOT / "aix")
    on_path = str(bin_dir) in os.environ.get("PATH", "").split(os.pathsep)
    print(f"PATH: linked {link} -> {ROOT / 'aix'}" + ("" if on_path else f" (add {bin_dir} to PATH)"))


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


def main(argv):
    if len(argv) >= 2 and argv[0] == "help":
        return topic_help(argv[1])
    if len(argv) >= 2 and argv[1] in ("--help", "-h"):
        return topic_help(argv[0])
    reexec_in_project(argv)
    if not argv or argv[0] in ("help", "-h", "--help"):
        usage(0)
    cmd, args = argv[0], argv[1:]
    if cmd == "complexity":
        cmd = "graph"
    if cmd == "about":
        print(ABOUT)
    elif cmd == "install":
        cmd_install(args)
    elif cmd == "validate":
        sys.exit(run_script("validate.py"))
    elif cmd == "upgrade":
        import upgrade
        upgrade.main(args)
    elif cmd == "doctor":
        sys.exit(run_script("doctor.py"))
    elif cmd == "security":
        import security
        security.main(args)
    elif cmd == "graph":
        import graph
        graph.main(args)
    elif cmd == "coverage":
        sys.exit(run_script("coverage_matrix.py"))
    elif cmd == "task":
        cmd_task(args)
    elif cmd == "skills":
        import skills
        skills.main(args)
    elif cmd in ("version", "-V", "--version"):
        print(f"aix {version()}")
    else:
        print(f"aix: unknown command '{cmd}'\n")
        usage(1)


if __name__ == "__main__":
    main(sys.argv[1:])
