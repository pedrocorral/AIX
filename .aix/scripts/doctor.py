#!/usr/bin/env python3
"""aix doctor — installation health (not document content; that is `aix docs validate`).
Each finding comes with the fix. Exit 1 if anything is broken."""
import json, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_skills as inst
import catalog as sk
from extern import ALWAYS_FILES, always_on_names

problems = []


def problem(what, fix):
    problems.append((what, fix))


def check_python():
    if sys.version_info < (3, 9):
        problem(f"Python {sys.version.split()[0]} is too old", "install Python 3.9 or newer")


def check_path():
    if os.name != "nt" and not shutil.which("aix"):
        problem("`aix` is not on PATH", "run `aix install` (links ~/.local/bin/aix) or add the kit folder to PATH")


def check_pointers():
    wanted = {ROOT / "CLAUDE.md": "AGENTS.md", ROOT / ".github" / "copilot-instructions.md": "AGENTS.md",
              ROOT / ".cursor" / "rules" / "aix.mdc": "AGENTS.md", ROOT / "GEMINI.md": "AGENTS.md"}
    for f, needle in wanted.items():
        if not f.exists() or needle not in f.read_text(encoding="utf-8"):
            problem(f"{f.relative_to(ROOT)} missing or not pointing at AGENTS.md", "run `aix install`")


def check_links():
    cat, off = sk.catalogue(), sk.disabled()
    for flat, info in cat.items():
        if flat in off:
            continue
        missing = [t for t in inst.TARGETS if not (ROOT / t / flat / "SKILL.md").exists()]
        if missing:
            problem(f"skill {flat} not linked in {', '.join(missing)}", "run `aix install`")
    for t in inst.TARGETS:
        d = ROOT / t
        for p in d.iterdir() if d.is_dir() else []:
            if p.is_symlink() and not p.exists():
                problem(f"dangling link {p.relative_to(ROOT)}", "run `aix install` (prunes it)")
    for name in off - set(cat):
        problem(f"disabled_skills names unknown skill {name}", "edit .aix/config.yaml")


def check_always_on():
    per_file = {f.relative_to(ROOT): set(always_on_names(f.read_text(encoding="utf-8"))) for f in ALWAYS_FILES if f.exists()}
    union = set().union(*per_file.values()) if per_file else set()
    for f, names in per_file.items():
        for n in union - names:
            problem(f"{n} always-on in other files but not in {f}", f"run `aix skills always {n}`")
    for n in union:
        if n not in sk.catalogue():
            problem(f"always-on skill {n} is not installed", f"run `aix skills add {n}` or `aix skills on-demand {n}`")


def check_extern():
    ext = ROOT / ".aix" / "skills" / "extern"
    for d in ext.iterdir() if ext.is_dir() else []:
        if d.is_dir() and (d / "SKILL.md").exists() and not (d / ".aix-source").exists():
            problem(f".aix/skills/extern/{d.name} has no .aix-source (cannot `aix skills update` it)", "re-add it with `aix skills add`")


def check_state():
    state = ROOT / "docs" / "road-map" / "going-on" / "STATE.md"
    if not state.exists():
        return problem("docs/road-map/going-on/STATE.md missing", "run `aix install`")
    m = re.search(r"^active_task:\s*(TASK-\d+)", state.read_text(encoding="utf-8"), re.M)
    if m and not list((ROOT / "docs" / "road-map" / "going-on").glob(f"{m.group(1)}*.md")):
        problem(f"STATE.md names {m.group(1)} but it is not in going-on/", f"`aix task start {m.group(1)}` or set active_task: none")


def main():
    for check in (check_python, check_path, check_pointers, check_links, check_always_on, check_extern, check_state):
        check()
    for what, fix in problems:
        print(f"PROBLEM {what}\n        fix: {fix}")
    print(f"{len(problems)} problems" if problems else "installation healthy")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
