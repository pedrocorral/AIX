AIX is a spec-driven development kit (SDDK) for AI coding agents: documentation is the ground truth,
code is its implementation, and every change leaves a traceable trail. `aix install` puts everything
an agent needs to build any application into your project: {n} skills for specifying, designing,
implementing, testing, auditing and reviewing; design patterns and architecture guides (MVC,
frontend/backend split, persistence abstraction, ORM, testing, security); document templates; and
the road-map that lets work resume across sessions. `aix` then keeps the documentation consistent
and moves tasks between states. Run `aix about` for the full story.

Usage: aix <group> <command> [args]   (no command = this help; aix help <command> for details)
aix acts on the nearest project at or above the current folder (the one holding .aix/config.yaml).

The kit
  aix newie [2|3]                     AIX one screen at a time: the basics; then the loop; then making it yours
  aix guide [CHAPTER]                 the user guide: start, concepts, install, agents, skills, instructions, ...
  aix self-install                    make `aix` callable from any terminal (link + PATH in your shell profile)
  aix self-test [NAME...]             run the kit's own tests (from the clone)
  aix install [--into DIR] [--copy]   link skills into agent runtimes; --into copies the kit into DIR first
      --from SOURCE                   with --into: the origin is SOURCE (a path or git URL: an organisation's kit
                                      checkout, or a bare layer folder taken as .aix/org/); recorded as source:
      --from-org SRC | --from-custom SRC   take one layer (.aix/org/, .aix/custom/) from SRC instead of the origin
      --agents a,b                    equip only these agents (else: a checklist in a terminal, all without one)
      --into asks per existing item: [r]eplace [s]kip [m]erge [R/S/M] all [a]bort  (replace keeps <item>.bak)
      --replace-all | --skip-all | --merge-all   answer for every collision without asking (CI, no terminal)
  aix upgrade [PROJECT] [--dry-run] [--yes]
                                      bring a project's kit files up to this checkout: overwrites kit-owned paths,
                                      merges AGENTS.md and .aix/config.yaml, never touches your docs, code or extern skills
  aix doctor                          is the INSTALL right? skill links, pointer files, always-on wiring, STATE.md,
                                      Python, PATH. Each problem comes with its fix
  aix about | version | help [CMD]    the full story | kit version | detailed help (e.g. aix help code dead)

The code                              (aix code ...; all four: Python, JS/TS, Rust, Java; --report writes docs/tests/)
  aix code graph [PATH...]            the modularity metric (alias: aix code complexity): A, the dependency graph
                                      of the code; B, the ideal shape on the same nodes (leaves and composers, arcs
                                      downward, no cycle, no hub); the distance = the edits (CUT, SPLIT) with reasons
      --functions                     the call graph (functions and methods, four languages) instead of modules; says how many
                                      calls it resolved.  --roles lists every node's level in B and role in A
      --gate [--max-distance N]       CI: exit 1 on any CUT (cycle, upward dependency), or past N edits
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
  aix code licenses [--gate] [--report]  every installed dependency's licence (Python, npm, Cargo, Maven), classed;
                                      exceptions in .aix/config.yaml `licenses_allow`, `licenses_known`
  aix code stats [PATH...] [--metric lines|cognitive|cyclomatic|nesting|params] [--report]
                                      distribution of function sizes as a terminal histogram scaled to the window,
                                      mean, sd, median, p90/p95, max, share over the limit; the largest functions
                                      and the files and folders pushing most functions over the limit
  aix code vulnerabilities [PATH...] [--taint] [--cve] [--history] [--commits N] [--strict] [--gate] [--audit]
                                      the deep security layer: Python taint paths (input sources to shell, eval,
                                      SQL, file, redirect, template, deserialisation, outbound-request sinks; one
                                      call deep, per file), known CVEs for pinned dependencies via the OSV database
                                      (network), and secrets in git history. Evidence to review; --audit writes it
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

The instructions                      (aix instructions ...)
  aix agents [NAME...|all|--list]     which agents this project equips (claude, copilot, cursor, gemini, opencode,
                                      codex): a checklist, detected ones preselected; writes agents: to config;
                                      install links folders and pointer files only for those. No line = all
  aix agent claim|release|whoami|list  a seat (agent-001 ...) for this session when several agents share the repo;
      set total N | get total         how many seats; set lease 4h | get lease
  aix policy [list|show|use|off]      the development cycle: minimal, standard, hotfix, release, or anarchy (none)
  aix check [--step ID] [--task ID]   run the active policy's checks in order; aix task done runs it first
  aix instructions [list]             every instruction any layer offers: state (active / optional off / disabled /
                                      not in profile), layer, kind (block that builds AGENTS.md, scoped by globs, always)
  aix instructions info ID | show ID  details | the file
  aix instructions enable|disable ID  turn one on (optional kit standards such as aix/frameworks/fastapi-backend) or off;
                                      remembered in .aix/config.yaml; profiles are for switching whole sets
  aix rules ...                       the same command; Cursor, Claude Code and Windsurf call these files rules

Profiles and overrides                (aix profile ...; .aix/custom/, ~/.config/aix/)
  aix profile [list] | show NAME | use NAME | off
                                      a profile is a saved set of choices shipped by a layer (profiles/NAME.yaml):
                                      which scoped instructions apply, which implementation of each skill class,
                                      the organisation router text
  .aix/custom/skills/<class>/         override a skill for this project (same class replaces, new adds, DISABLED removes)
  .aix/custom/instructions/*.md       scoped instructions (front matter id, description, applyTo globs) rendered
                                      natively for Copilot and Cursor and listed in AGENTS.md
  ~/.config/aix/skills/<class>/       your personal skill overrides (terminal sessions only, never committed)

The skills                            (aix skills ...)
  aix skills [general|specific] [cat] catalogue: name, state (always / on-demand / disabled), description
  aix skills info NAME | show NAME    details (group, level, runtimes, layer, id, hash, source) | the SKILL.md
                                      overrides: .aix/custom/skills/<class>/ (project) or ~/.config/aix/skills/<class>/ (you)
  aix skills enable|disable NAME...   link/unlink a skill everywhere; remembered in .aix/config.yaml
  aix skills registry                 known third-party skills (caveman, ponytail, mattpocock/skills, ...) with evidence
  aix skills add NAME [--on-demand]   download a registry skill into .aix/skills/extern/, link it everywhere;
                                      general skills become always-on unless --on-demand
  aix skills remove|update NAME       drop it / re-download it;  aix skills always|on-demand NAME
  aix skills refactor                 the seven fix skills, one per aix code finding (aix help refactor)

Old forms still work: aix graph|complexity|validate|coverage|security = aix code graph | aix docs ...

Launchers: `aix` (bash, Linux/macOS) and `aix.cmd` (Windows) simply call this file with python3.
