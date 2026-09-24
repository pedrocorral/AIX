#!/usr/bin/env python3
"""Leaf: the agents AIX equips (the tools that read the files, whatever model they run) and which of them a project
selected. `agents: [claude, copilot]` in .aix/config.yaml; no line means all of them. `aix agents` sets the line;
install, upgrade, doctor and the skills commands read it here."""
import re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = {  # name -> label, skills folder, pointer files, rendered folders, commands that reveal it on PATH
    "claude":   {"label": "Claude Code, Claude desktop", "skills": ".claude/skills", "pointers": ["CLAUDE.md"], "rendered": [], "detect": ["claude"]},
    "copilot":  {"label": "GitHub Copilot (VS Code, CLI, cloud agent)", "skills": ".github/skills", "pointers": [".github/copilot-instructions.md"],
                 "rendered": [".github/instructions"], "detect": ["code", "code-insiders", "copilot"]},
    "cursor":   {"label": "Cursor", "skills": ".cursor/skills", "pointers": [".cursor/rules/aix.mdc"], "rendered": [".cursor/rules"], "detect": ["cursor"]},
    "gemini":   {"label": "Gemini CLI, Antigravity", "skills": ".agents/skills", "pointers": ["GEMINI.md"], "rendered": [], "detect": ["gemini", "antigravity"]},
    "opencode": {"label": "OpenCode", "skills": ".opencode/skills", "pointers": [], "rendered": [], "detect": ["opencode"]},
    "codex":    {"label": "Codex (reads AGENTS.md only)", "skills": None, "pointers": [], "rendered": [], "detect": ["codex"]},
}
ALIASES = {"vscode": "copilot", "vs-code": "copilot", "github": "copilot", "claude-code": "claude", "claude-desktop": "claude",
           "antigravity": "gemini", "gemini-cli": "gemini", "open-code": "opencode"}
POINTER_MARK = "Read and follow `AGENTS.md`"   # every pointer file AIX writes starts with this sentence


def canonical(name: str) -> str:
    n = name.strip().lower()
    n = ALIASES.get(n, n)
    if n not in AGENTS:
        raise SystemExit(f"aix: unknown agent '{name}'. Known: {', '.join(AGENTS)} (aliases: {', '.join(ALIASES)})")
    return n


def configured(project: Path = ROOT):
    """The names in config.yaml `agents:`, or None when the line is absent (= all)."""
    cfg = project / ".aix" / "config.yaml"
    m = re.search(r"^agents:\s*\[(.*?)\]", cfg.read_text(encoding="utf-8"), re.M) if cfg.exists() else None
    if not m:
        return None
    names = [canonical(x) for x in m.group(1).split(",") if x.strip()]
    return names or None


def selected(project: Path = ROOT) -> list:
    return configured(project) or list(AGENTS)


def set_agents(project: Path, names) -> list:
    """Write `agents: [...]` (all names, or 'all' = remove the line)."""
    names = [canonical(n) for n in names]
    if names and set(names) == set(AGENTS):
        names = []
    cfg = project / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    line = f"agents: [{', '.join(n for n in AGENTS if n in names)}]   # the agents this project equips (aix agents); no line = all"
    if re.search(r"^agents:.*$", text, re.M):
        text = re.sub(r"^agents:.*\n", (line + "\n") if names else "", text, count=1, flags=re.M)
    elif names:
        text = text.rstrip("\n") + "\n" + line + "\n"
    cfg.write_text(text, encoding="utf-8")
    return names or list(AGENTS)


def skill_dirs(project: Path = ROOT) -> list:
    """The skills folders (project-relative) of the selected agents, in the kit's order."""
    return [AGENTS[n]["skills"] for n in selected(project) if AGENTS[n]["skills"]]


def pointer_files(project: Path = ROOT) -> list:
    return [p for n in selected(project) for p in AGENTS[n]["pointers"]]


def detect(project: Path = ROOT) -> set:
    """Agents present on this machine (command on PATH) or already equipped in the project (folder present)."""
    found = set()
    for n, a in AGENTS.items():
        if any(shutil.which(c) for c in a["detect"]) or (a["skills"] and (project / a["skills"]).is_dir()) \
                or any((project / p).exists() for p in a["pointers"]):
            found.add(n)
    return found


def is_aix_pointer(path: Path) -> bool:
    """True when AIX wrote this pointer (a person's own file is never removed)."""
    try:
        return path.is_file() and POINTER_MARK in path.read_text(encoding="utf-8", errors="replace")[:400]
    except OSError:
        return False


def _remove_links(project: Path, a: dict, removed: list):
    d = project / a["skills"] if a["skills"] else None
    if not d or not d.is_dir():
        return
    known = _indexed(project) if (project / ".aix" / "index.json").exists() else set()
    for p in d.iterdir():
        if p.is_symlink():
            p.unlink(); removed.append(str(p.relative_to(project)))
        elif p.is_dir() and (p / "SKILL.md").exists() and p.name in known:
            shutil.rmtree(p); removed.append(str(p.relative_to(project)))
    _rmdir_empty(d, project)


def _remove_pointers(project: Path, a: dict, removed: list):
    for rel in a["pointers"]:
        p = project / rel
        if is_aix_pointer(p):
            p.unlink(); removed.append(rel)
            _rmdir_empty(p.parent, project)


def _remove_rendered(project: Path, a: dict, removed: list):
    for rel in a["rendered"]:
        d = project / rel
        if not d.is_dir():
            continue
        for p in d.glob("aix-*"):
            p.unlink(); removed.append(str(p.relative_to(project)))
        _rmdir_empty(d, project)


def remove_deselected(project: Path, keep: list) -> list:
    """Drop what AIX created for agents no longer selected: skill links, AIX pointer files, rendered aix-* files.
    Returns what was removed (project-relative)."""
    removed = []
    for n, a in AGENTS.items():
        if n in keep:
            continue
        _remove_links(project, a, removed)
        _remove_pointers(project, a, removed)
        _remove_rendered(project, a, removed)
    return removed


def _indexed(project: Path) -> set:
    import json
    try:
        return set(json.loads((project / ".aix" / "index.json").read_text(encoding="utf-8")).get("skills", {}))
    except (OSError, ValueError):
        return set()


def _rmdir_empty(d: Path, stop: Path):
    while d != stop and d.is_dir() and not any(d.iterdir()):
        d.rmdir(); d = d.parent


def _row_status(name: str, conf, det) -> str:
    if conf:
        return "configured" if name in conf else "not selected"
    return "detected" if name in det else "-"


def rows(project: Path = ROOT) -> list:
    """Checklist rows: every agent, preselected when configured (or, without a line, when detected; nothing detected = all)."""
    conf, det = configured(project), detect(project)
    out = []
    for n, a in AGENTS.items():
        on = (n in conf) if conf else (n in det if det else True)
        files = ", ".join(x for x in [a["skills"], *a["pointers"]] if x) or "AGENTS.md"
        out.append({"name": n, "label": a["label"], "files": files, "status": _row_status(n, conf, det), "on": on})
    return out


def describe(r):
    return r["label"], r["files"], r["status"]


def report(project: Path, rs):
    print(f"Agents equipped in {project}\n")
    print(f"  {'AGENT':10s} {'':3s} {'WHAT':44s} {'FILES':46s} STATUS")
    for r in rs:
        print(f"  {r['name']:10s} {'[x]' if r['on'] else '[ ]':3s} {r['label']:44s} {r['files']:46s} {r['status']}")
    conf = configured(project)
    print(f"\n  configured: {conf or 'all (no agents: line)'}")


def run(project: Path, names=None, list_only=False, title="aix agents") -> bool:
    """Choose the agents (names, or the checklist in a terminal, or the table without one); write config; relink."""
    import sys, os as _os
    rs = rows(project)
    if list_only:
        report(project, rs); return False
    if names:
        chosen = list(AGENTS) if names == ["all"] else [canonical(n) for n in names]
    elif sys.stdin.isatty() and not _os.environ.get("CI"):
        import codefind
        chosen = codefind.checklist(rs, f"{title} — which agents does this project equip? ({project})", describe, "agents: in .aix/config.yaml")
        if chosen is None:
            print("aix agents: cancelled, config unchanged"); return False
        if not chosen:
            print("aix agents: nothing selected; keeping the current choice"); return False
    else:
        report(project, rs)
        print("  (no terminal to ask: all agents are equipped; `aix agents NAME...` or `aix install --agents a,b` chooses)")
        return False
    before = selected(project)
    now = set_agents(project, chosen)
    print(f"agents: {now}" + (" (unchanged)" if set(before) == set(now) else ""))
    return set(before) != set(now)


def _is_aix_entry(p: Path, known: set) -> bool:
    """A link into .aix/, an AIX-indexed skill folder, or a backup AIX made."""
    if p.is_symlink():
        try:
            return ".aix" in p.resolve().parts
        except OSError:
            return True  # a broken link is nobody's work worth keeping
    return p.name in known or p.name.endswith("-bak")


def _foreign_skills_dir(d: Path, project: Path) -> bool:
    """A skills folder someone else made: has entries that are neither links into .aix/ nor AIX-indexed skills."""
    known = _indexed(project)
    return any(not _is_aix_entry(p, known) for p in d.iterdir())


def _bak_name(p: Path) -> Path:
    bak, i = p.with_name(p.name + "-bak"), 2
    while bak.exists():
        bak = p.with_name(f"{p.name}-bak{i}"); i += 1
    return bak


def _is_foreign(p: Path, project: Path) -> bool:
    if not p.exists() or p.is_symlink():
        return False
    return _foreign_skills_dir(p, project) if p.is_dir() else not is_aix_pointer(p)


def backup_foreign(project: Path, names=None) -> list:
    """Move aside what a person wrote where AIX writes for the selected agents: `<path>-bak`. Returns the moves."""
    moved = []
    for n in (names or selected(project)):
        a = AGENTS[n]
        for rel in ([a["skills"]] if a["skills"] else []) + a["pointers"]:
            p = project / rel
            if _is_foreign(p, project):
                bak = _bak_name(p)
                p.rename(bak)
                moved.append((rel, str(bak.relative_to(project))))
    return moved
