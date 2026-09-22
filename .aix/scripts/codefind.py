#!/usr/bin/env python3
"""aix code find — find the folders that hold code and set `paths.code_roots` in .aix/config.yaml.

Candidates: every top-level folder of the project with source files below it (hidden, docs/, .aix/, dependency and
build folders skipped), plus the project root itself when source files sit directly in it. A checklist (curses TUI;
plain y/N prompts where curses is missing) lets you keep or drop each; Enter writes the list. Configured roots that
do not exist on disk are shown and dropped. `--list` prints and changes nothing; `--yes` accepts every suggestion.
`aix install` runs the same step at the end of a fresh install (interactive terminals only)."""
import os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import EXT, SKIP, ROOT

MARKERS = {"pyproject.toml": "python project", "setup.py": "python project", "package.json": "node package", "Cargo.toml": "rust crate",
           "pom.xml": "maven project", "build.gradle": "gradle project", "build.gradle.kts": "gradle project", "go.mod": "go module"}


def source_count(folder: Path, recurse: bool = True):
    """{language: files} under folder (or directly in it), skipping hidden, SKIP and empty files."""
    out = {}
    walk = folder.rglob("*") if recurse else folder.iterdir()
    for f in walk:
        inner = f.relative_to(folder).parts[:-1]
        if f.is_file() and f.suffix in EXT and not any(p in SKIP or p.startswith(".") for p in inner) and f.stat().st_size > 0:
            out[EXT[f.suffix]] = out.get(EXT[f.suffix], 0) + 1
    return out


def candidates(project: Path):
    """[{name, langs, marker}] for '.' (files directly at the root) and every top-level folder with code below it."""
    rows = []
    direct = source_count(project, recurse=False)
    if direct:
        rows.append({"name": ".", "langs": direct, "marker": marker_of(project)})
    for d in sorted(project.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and d.name not in SKIP:
            langs = source_count(d)
            if langs:
                rows.append({"name": d.name, "langs": langs, "marker": marker_of(d)})
    return rows


def marker_of(folder: Path):
    return next((v for k, v in MARKERS.items() if (folder / k).exists()), "")


def current_roots(project: Path):
    cfg = project / ".aix" / "config.yaml"
    m = re.search(r"^\s+code_roots:\s*\[(.*?)\]", cfg.read_text(encoding="utf-8"), re.M) if cfg.exists() else None
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def write_roots(project: Path, roots):
    cfg = project / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    line = f"  code_roots: [{', '.join(roots)}]   # set by `aix code find`; the code tools scan these (none existing -> the whole project)"
    if re.search(r"^\s+code_roots:.*$", text, re.M):
        text = re.sub(r"^\s+code_roots:.*$", line, text, count=1, flags=re.M)
    else:
        text = re.sub(r"^paths:.*$", lambda m: m.group(0) + "\n" + line, text, count=1, flags=re.M)
    cfg.write_text(text, encoding="utf-8")


def rows_for(project: Path):
    """The checklist: candidates first (new ones preselected), then configured roots that do not exist (dropped)."""
    configured = current_roots(project)
    rows = []
    for c in candidates(project):
        rows.append({**c, "status": "configured" if c["name"] in configured else "new", "on": True})
    for r in configured:
        if r not in [x["name"] for x in rows]:
            rows.append({"name": r, "langs": {}, "marker": "", "status": "configured, not found" if not (project / r).exists() else "configured, no code", "on": False})
    return rows


def describe(r):
    langs = " · ".join(f"{n} {l}" for l, n in sorted(r["langs"].items(), key=lambda kv: -kv[1])) or "-"
    return langs, r["marker"], r["status"]


def checklist(rows, title):
    """Toggle rows; return the selected names, or None when cancelled. curses when available, prompts otherwise."""
    try:
        import curses
    except ImportError:
        return prompt_list(rows)
    try:
        return curses.wrapper(lambda scr: tui(scr, rows, title))
    except Exception:
        return prompt_list(rows)


def prompt_list(rows):
    out = []
    for r in rows:
        langs, marker, status = describe(r)
        ans = input(f"  {r['name']:24s} {langs:22s} {marker:15s} {status:22s} keep? [{'Y/n' if r['on'] else 'y/N'}] ").strip().lower()
        if ans in ("y", "yes") or (not ans and r["on"]):
            out.append(r["name"])
    return out


def tui(scr, rows, title):
    import curses
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1); curses.init_pair(2, curses.COLOR_YELLOW, -1); curses.init_pair(3, curses.COLOR_RED, -1); curses.init_pair(4, curses.COLOR_CYAN, -1)
    cur, top = 0, 0
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        scr.addnstr(0, 0, f" {title}", w - 1, curses.A_BOLD)
        scr.addnstr(1, 0, "  space toggle · a all · n none · ↑↓/jk move · Enter apply · q cancel", w - 1, curses.color_pair(4))
        body = h - 4
        if cur < top: top = cur
        if cur >= top + body: top = cur - body + 1
        for i, r in enumerate(rows[top:top + body]):
            idx = top + i
            langs, marker, status = describe(r)
            box = "[x]" if r["on"] else "[ ]"
            color = curses.color_pair(1) if status == "new" else curses.color_pair(3) if "not found" in status else curses.color_pair(2) if "no code" in status else 0
            attr = curses.A_REVERSE if idx == cur else 0
            line = f"  {box} {r['name']:<26.26s} {langs:<24.24s} {marker:<15.15s} {status}"
            scr.addnstr(3 + i, 0, line.ljust(w - 1), w - 1, attr | color)
        on = sum(1 for r in rows if r["on"])
        scr.addnstr(h - 1, 0, f"  {on} of {len(rows)} selected -> paths.code_roots in .aix/config.yaml", w - 1, curses.A_DIM)
        scr.refresh()
        k = scr.getch()
        if k in (curses.KEY_UP, ord("k")): cur = max(0, cur - 1)
        elif k in (curses.KEY_DOWN, ord("j")): cur = min(len(rows) - 1, cur + 1)
        elif k == ord(" "): rows[cur]["on"] = not rows[cur]["on"]
        elif k == ord("a"):
            for r in rows: r["on"] = True
        elif k == ord("n"):
            for r in rows: r["on"] = False
        elif k in (10, 13, curses.KEY_ENTER): return [r["name"] for r in rows if r["on"]]
        elif k in (27, ord("q")): return None


def report(project: Path, rows):
    print(f"Code folders in {project}\n")
    print(f"  {'FOLDER':26s} {'FILES':24s} {'MARKER':15s} STATUS")
    for r in rows:
        langs, marker, status = describe(r)
        print(f"  {r['name']:26s} {langs:24s} {marker:15s} {status}")
    print(f"\n  configured: {current_roots(project) or '-'}")


def run(project: Path, yes: bool = False, list_only: bool = False, title: str = "aix code find") -> bool:
    """Show the checklist and write code_roots. Returns True when config changed."""
    rows = rows_for(project)
    if not rows:
        print(f"aix code find: no source files ({', '.join(sorted(EXT))}) under {project}")
        return False
    if list_only or (not yes and not sys.stdin.isatty()):
        report(project, rows)
        if not list_only:
            print("  (no terminal to ask: run `aix code find` interactively, or `aix code find --yes` to accept the suggestions)")
        return False
    chosen = [r["name"] for r in rows if r["on"]] if yes else checklist(rows, f"{title} — folders with code in {project}")
    if chosen is None:
        print("aix code find: cancelled, config unchanged"); return False
    before = current_roots(project)
    write_roots(project, chosen)
    print(f"code_roots: {chosen}" + ("" if before != chosen else " (unchanged)"))
    return before != chosen


def main(args):
    if any(a not in ("--yes", "--list") for a in args):
        sys.exit("usage: aix code find [--list | --yes]")
    run(ROOT, yes="--yes" in args, list_only="--list" in args)


if __name__ == "__main__":
    main(sys.argv[1:])
