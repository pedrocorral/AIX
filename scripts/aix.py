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
      --into asks per existing item: [r]eplace [s]kip [m]erge [R/S/M] all [a]bort  (replace keeps <item>.bak)
      --replace-all | --skip-all | --merge-all   answer for every collision without asking (CI, no terminal)
  aix validate                        are the DOCS right? IDs, links, indexes, front-matter. CI gate, exit 1 on errors
  aix doctor                          is the INSTALL right? skill links, pointer files, always-on wiring, STATE.md,
                                      Python, PATH. Each problem comes with its fix
  aix coverage                        regenerate docs/tests/coverage-matrix.md (requirement -> test -> code gaps)
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
  aix help

Launchers: `aix` (bash, Linux/macOS) and `aix.cmd` (Windows) simply call this file with python3."""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))


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
AGENTS.md at the repository root is the contract every agent reads first (CLAUDE.md, .github/copilot-instructions.md
and .cursor/rules/aix.mdc just point to it). It fits in about 3k tokens and stays in context permanently. Everything
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
.opencode/skills, .claude/skills, .github/skills, .agents/skills and .cursor/skills. Never edit the installed
copies; they are ignored by git. Some skills bundle deterministic scripts/ (regex scans that are cheaper than
having the model read code) and references/.

7. THE CLI
----------
`aix` is a bash launcher (Linux, macOS) and `aix.cmd` a batch launcher (Windows). Both run scripts/aix.py with
Python 3.9+ and no third-party dependencies.

  aix                       version and command list (same as `aix help`)
  aix about                 this text
  aix version               kit version from framework.yaml

  aix install               link all skills into the five runtime folders of the current kit checkout; write
                            pointer files for Copilot and Cursor if missing; create road-map STATE.md if missing;
                            on Linux/macOS symlink `aix` into ~/.local/bin when that folder exists. Idempotent.
      --copy                copy skills instead of symlinking (filesystems without symlinks, some Windows setups)
      --into DIR            first copy the kit payload (AGENTS.md, CLAUDE.md, framework.yaml, docs/, skills/,
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

  aix validate              documentation integrity check described in section 5; exit 1 on errors
  aix doctor                installation health: every skill linked in every runtime, no dangling links, pointer
                            files present, always-on sections consistent across AGENTS.md / Copilot / Cursor,
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


ANYWHERE = {"help", "-h", "--help", "about", "version", "-V", "--version"}


def find_project(start: Path):
    """Nearest folder at or above `start` holding framework.yaml: that is the project aix operates on."""
    for d in [start, *start.parents]:
        if (d / "framework.yaml").exists():
            return d
    return None


def reexec_in_project(argv):
    """Run the project's own copy of the CLI so every module resolves ROOT to the project, not to this checkout."""
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
    reexec_in_project(argv)
    if not argv or argv[0] in ("help", "-h", "--help"):
        usage(0)
    cmd, args = argv[0], argv[1:]
    if cmd == "about":
        print(ABOUT)
    elif cmd == "install":
        cmd_install(args)
    elif cmd == "validate":
        sys.exit(run_script("validate.py"))
    elif cmd == "doctor":
        sys.exit(run_script("doctor.py"))
    elif cmd == "security":
        import security
        security.main(args)
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
