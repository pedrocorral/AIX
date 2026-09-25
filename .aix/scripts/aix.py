#!/usr/bin/env python3
"""The AIX command line: `aix <group> <command>`. Thin: parse, find the project, hand off to the module that owns
the command. The usage screen and the help topics are Markdown under .aix/meta-docs/help/; `aix guide` is the long-form manual."""
import os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from project import find_project
import helptext
from cli_install import cmd_install
from cli_guide import run_guide
from cli_agent import run_agent, run_agents
from cli_instructions import run_instructions
from cli_policy import run_check, run_policy, run_profile


def skill_count():
    return sum(1 for _ in (ROOT / ".aix" / "skills").rglob("SKILL.md"))


ANYWHERE = {"help", "-h", "--help", "about", "version", "-V", "--version", "self-install", "self-update", "self-test", "guide", "newie"}  # need no project


def is_kit() -> bool:
    """This checkout is the kit itself (AIX-DEVELOPMENT.md is never copied into projects)."""
    return (ROOT / "AIX-DEVELOPMENT.md").exists()


def _runs_from_this_checkout(argv) -> bool:
    """Commands that act on or from THIS checkout (the kit on PATH), never a project's older copy."""
    return argv[:1] in (["upgrade"], ["self-install"], ["self-update"], ["self-test"]) or argv[:2] == ["install", "aix"]


def _allowed_outside_a_project(argv) -> bool:
    return bool(argv) and argv[0] in ANYWHERE or argv[:1] == ["install"] or argv[:2] == ["skills", "registry"]


def _handoff_to(project: Path, argv, plain_install: bool):
    """Run the project's own copy of the CLI, or explain why it cannot."""
    own = project / ".aix" / "scripts" / "aix.py"
    if own.exists():
        os.execv(sys.executable, [sys.executable, str(own), *argv])
    if (project / "framework.yaml").exists():
        if plain_install:
            print(f"note: {project} uses the 1.x layout; run `aix upgrade` there to migrate it to .aix/")
            return
        sys.exit(f"aix: {project} uses the 1.x layout; run `aix upgrade` (from this kit) to migrate it to .aix/")
    sys.exit(f"aix: {project} has .aix/ but no .aix/scripts/aix.py; run `aix install --into {project}`")


def reexec_in_project(argv):
    """Run the project's own copy of the CLI so every module resolves ROOT to the project, not to this checkout."""
    if _runs_from_this_checkout(argv):
        return
    plain_install = argv[:1] == ["install"] and "--into" not in argv
    if plain_install and is_kit():
        expose_on_path()  # the aix on PATH is always the kit's launcher, never a project's copy; fix it first, from anywhere
    project = find_project(Path.cwd())
    if project is None:
        if _allowed_outside_a_project(argv):
            return
        sys.exit("aix: not inside an AIX project (no .aix/config.yaml here or above). "
                 "Use `aix install --into DIR` to add AIX to a project, or cd into one.")
    if project != ROOT:
        _handoff_to(project, argv, plain_install)


def topic_help(name: str):
    text = helptext.topic(name)
    if not text:
        print(f"aix: no help for '{name}'. Topics: " + ", ".join(helptext.topics()))
        sys.exit(1)
    print(text, end="" if text.endswith("\n") else "\n")


def usage(code=0):
    print(f"AIX {version()}\n")
    print(helptext.text("usage").replace("{n}", str(skill_count())))
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
    """A plain `aix install` in the kit clone refreshes the link in ~/.local/bin when that folder exists; the full,
    profile-editing setup is `aix self-install`."""
    import selfinstall
    folder = selfinstall.bin_dir()
    if os.name == "nt" or not folder.is_dir():
        print("PATH: run `aix self-install` once to call `aix` from any terminal.")
        return
    actions = []
    selfinstall.write_link(folder / "aix", False, actions)
    print("PATH: " + actions[-1].strip() + ("" if selfinstall.on_path(folder) else "  (not on PATH yet: `aix self-install` fixes that)"))


def version_line() -> str:
    """The version of the copy that runs; inside a project also the kit on PATH, with a hint when they differ."""
    mine = version()
    if is_kit():
        return f"AIX {mine}"
    import shutil, re
    found = shutil.which("aix")
    kit_root = Path(found).resolve().parents[2] if found else None
    if not kit_root or not (kit_root / ".aix" / "config.yaml").exists() or kit_root == ROOT:
        return f"AIX {mine} (this project's copy)"
    m = re.search(r"^version:\s*([^\s#]+)", (kit_root / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    theirs = m.group(1) if m else "?"
    hint = "" if theirs == mine else "  -> run `aix upgrade` here (`--dry-run` shows the plan)"
    return f"AIX {mine} (this project's copy); kit on PATH: {theirs} at {kit_root}{hint}"


def cmd_task(args):
    import roadmap as rm
    sub, rest = (args[0], args[1:]) if args else ("", [])
    actions = {
        "new": lambda: rm.cmd_new(rest[0], rest[2] if len(rest) > 2 and rest[1] == "--bucket" else "next"),
        "start": lambda: rm.cmd_start(rest[0], "--force" in rest),
        "block": lambda: rm.cmd_block(rest[0], rest[1] if len(rest) > 1 else ""),
        "done": lambda: rm.cmd_done(rest[0], "--force" in rest),
        "list": rm.cmd_list,
    }
    if sub not in actions or (sub != "list" and not rest):
        usage(1)
    actions[sub]()


ALIASES = {"graph": ["code", "graph"], "complexity": ["code", "graph"], "validate": ["docs", "validate"],
           "coverage": ["docs", "coverage"], "security": ["docs", "security"], "rules": ["instructions"], "for-dummies": ["newie"], "basics": ["newie"]}
CODE_MODES = {"graph": [], "complexity": [], "dead": ["--dead"], "clones": ["--clones"]}


CODE_TOOLS = {"find": "codefind", "style": "style", "security": "codesecurity", "stats": "stats", "vulnerabilities": "vulnerabilities"}


def _graph_args(args):
    """(mode, rest) for the graph engine; an unknown word that is not a path is refused."""
    if not args or args[0] in CODE_MODES:
        return (args[0] if args else "graph"), (args[1:] if args else [])
    if args[0].startswith("-") or (ROOT / args[0]).exists():
        return "graph", args
    sys.exit(f"aix code: unknown command '{args[0]}'. Commands: find, graph, complexity, dead, clones, style, security, vulnerabilities, stats "
             f"(a path may follow the command, e.g. aix code graph backend)")


def run_code(args):
    """aix code <tool> ...: the tools with their own module, else the graph engine (graph, complexity, dead, clones)."""
    import importlib
    if args and args[0] in CODE_TOOLS:
        return importlib.import_module(CODE_TOOLS[args[0]]).main(args[1:])
    import graph
    mode, rest = _graph_args(args)
    graph.main(CODE_MODES[mode] + rest)


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


def _run_self(cmd, args):
    import selfinstall
    {"self-install": selfinstall.main, "self-update": selfinstall.self_update, "self-test": selfinstall.self_test}[cmd](args)


def _commands():
    """command -> handler(args). Built on demand so every handler is defined by then."""
    return {
        "about": lambda a: print(helptext.text("about"), end=""), "version": lambda a: print(version_line()), "-V": lambda a: print(version_line()), "--version": lambda a: print(version_line()),
        "self-install": lambda a: _run_self("self-install", a), "self-update": lambda a: _run_self("self-update", a), "self-test": lambda a: _run_self("self-test", a),
        "install": cmd_install, "upgrade": lambda a: __import__("upgrade").main(a), "doctor": lambda a: sys.exit(run_script("doctor.py")),
        "code": run_code, "docs": run_docs, "task": cmd_task, "skills": lambda a: __import__("skills").main(a),
        "profile": run_profile, "policy": run_policy, "check": run_check, "instructions": run_instructions,
        "agents": run_agents, "agent": run_agent, "guide": run_guide, "newie": lambda a: print(helptext.text("newie"), end=""),
    }


def _help_topic(argv):
    """The topic when the command line is a help request (`aix help X`, `aix X --help`), else None."""
    if len(argv) >= 2 and argv[0] == "help":
        return " ".join(argv[1:])
    if len(argv) >= 2 and argv[-1] in ("--help", "-h"):
        return " ".join(argv[:-1])
    return None


def main(argv):
    argv = list(argv)
    if argv and argv[0] in ALIASES:
        argv = ALIASES[argv[0]] + argv[1:]
    topic = _help_topic(argv)
    if topic is not None:
        argv = ["help", *topic.split(" ")]  # a help request has no side effect; the project's copy answers it with its layers
    reexec_in_project(argv)
    if topic is not None:
        return topic_help(topic)
    if not argv or argv[0] in ("help", "-h", "--help"):
        usage(0)
    handler = _commands().get(argv[0])
    if handler is None:
        print(f"aix: unknown command '{argv[0]}'\n")
        usage(1)
    if handler(argv[1:]) is True:
        _reapply(argv[0])


def _reapply(command: str):
    """A command changed a choice (skills, instructions, profile, policy, agents): the root applies it once, so no
    command needs to import the installer."""
    import install_skills as inst, gitignore
    inst.install_into(ROOT, copy=False)
    gitignore.ask_and_apply(ROOT, label=f"aix {command}")


if __name__ == "__main__":
    main(sys.argv[1:])
