AIX — a spec-driven development kit (SDDK) for coding agents
============================================================

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
organised in ten categories:

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
  workflow/      plan-feature, to-tickets, triage, wayfinder, research, prototype, setup-tracker, wizard
  debug/         diagnose, merge-conflicts
  coach/         grill, grill-me, grill-with-docs, teach, questionnaire, wait-what, scaffold-exercises
  plus           core/which-skill; spec/write-skill, write-for-agents, plain-language; architecture/trace,
                 deep-modules, domain-model, improve; implement/code-python, code-typescript; testing/validate-ui

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
  aix self-install          make `aix` callable from any terminal: ~/.local/bin/aix -> this clone, PATH line in your
                            shell profiles (bash, zsh, fish; Windows: user PATH), verified. Idempotent, --dry-run.
                            alias: aix install aix.   aix self-update = git pull of the clone.
  aix self-test [NAME...]   the kit's own test suite from the clone (tests/); NAME = one file (agents, layers, ...);
                            --network adds the registry downloads; -q hides the per-test lines
  aix guide [CHAPTER|--all] the user guide, eleven chapters in plain language (.aix/meta-docs/guide/); no argument
                            lists them; a key or number opens one (aix guide skills, aix guide 5)
  aix install               link all skills into the five runtime folders; write pointer files for Copilot, Cursor
                            and Gemini CLI if missing; create road-map STATE.md if missing; refresh the ~/.local/bin
                            link when that folder exists. Idempotent.
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
  aix code vulnerabilities  the deep security layer: Python taint paths from input sources to dangerous sinks
                            (with the chain), known CVEs for pinned dependencies via the OSV database, secrets in
                            git history. Evidence to review, never proof; --audit writes the report the register
                            needs. Not an authorisation/logic review: that stays with the security-audit-* skills.
  aix code find             which folders hold code -> paths.code_roots (checklist; also run by aix install)
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
