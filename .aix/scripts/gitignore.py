#!/usr/bin/env python3
"""Leaf: the .gitignore entries a project needs for AIX, and the y/N step that adds the missing ones.

Ignored: `.aix/` (the whole kit copy, by decision of 2026-09-22), the skills folders of the selected agents, the
rendered `aix-*` instruction files, the reports the code tools write. Entries are appended once, under a marker
comment; existing lines are never edited. `aix install`, `aix upgrade` and `aix agents` show the missing lines and
ask in a terminal (`--yes` answers yes on upgrade); without a terminal they print the lines and touch nothing."""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agents

MARK = "# AIX: generated per machine by `aix install` (kit copy, agent links, rendered files)"
REPORTS = []   # nothing under docs/ is ever proposed (decision 2026-09-23): the generated reports there are the project's to commit or not


def wanted(project: Path) -> list:
    out = [".aix/"]
    for n in agents.selected(project):
        a = agents.AGENTS[n]
        if a["skills"]:
            out.append(a["skills"] + "/")
        out += [f"{d}/aix-*" for d in a["rendered"]]
    return out + REPORTS


def _norm(line: str) -> str:
    return line.strip().rstrip("/")


def missing(project: Path) -> list:
    gi = project / ".gitignore"
    have = {_norm(l) for l in gi.read_text(encoding="utf-8", errors="replace").splitlines()} if gi.exists() else set()
    return [w for w in wanted(project) if _norm(w) not in have]


def apply(project: Path, entries: list):
    gi = project / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    if MARK not in text:
        text += ("\n" if text else "") + MARK + "\n"
    text += "".join(e + "\n" for e in entries)
    gi.write_text(text, encoding="utf-8")


def ask_and_apply(project: Path, yes: bool = False, label: str = "aix") -> bool:
    """Show the missing lines; add them on yes (flag or answer). Returns True when .gitignore changed."""
    if (project / "AIX-DEVELOPMENT.md").exists():
        return False  # the kit checkout commits its .aix/
    todo = missing(project)
    if not todo:
        return False
    where = ".gitignore" if (project / ".gitignore").exists() else ".gitignore (new file)"
    print(f"  {where} lacks {len(todo)} AIX entr{'y' if len(todo) == 1 else 'ies'}:")
    for e in todo:
        print(f"    {e}")
    if not yes:
        if not (sys.stdin.isatty() and not os.environ.get("CI")):
            print(f"  (no terminal to ask: add them by hand, or rerun `{label}` in a terminal)")
            return False
        if input("  add them to .gitignore? [y/N] ").strip().lower() not in ("y", "yes"):
            print("  .gitignore left as it is")
            return False
    apply(project, todo)
    print(f"  added {len(todo)} line(s) to .gitignore")
    return True
