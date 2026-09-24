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
from codefiles import EXT, SKIP, ROOT

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
    shown = {"js": "js/ts"}  # the tools parse .js/.jsx/.ts/.tsx as one language
    langs = " · ".join(f"{n} {shown.get(l, l)}" for l, n in sorted(r["langs"].items(), key=lambda kv: -kv[1])) or "-"
    return langs, r["marker"], r["status"]


def checklist(rows, title, describe_row=None, footer="paths.code_roots in .aix/config.yaml"):
    """Toggle rows; return the selected names, or None when cancelled. curses when available, prompts otherwise.
    describe_row(row) -> three column strings; shared with `aix agents`."""
    describe_row = describe_row or describe
    try:
        import curses
    except ImportError:
        return prompt_list(rows, describe_row)
    try:
        return curses.wrapper(lambda scr: tui(scr, rows, title, describe_row, footer))
    except Exception:
        return prompt_list(rows, describe_row)


def prompt_list(rows, describe_row):
    out = []
    for r in rows:
        a, b, status = describe_row(r)
        ans = input(f"  {r['name']:24s} {a:22s} {b:15s} {status:22s} keep? [{'Y/n' if r['on'] else 'y/N'}] ").strip().lower()
        if ans in ("y", "yes") or (not ans and r["on"]):
            out.append(r["name"])
    return out


def _row_colour(curses, status: str) -> int:
    if status in ("new", "detected"):
        return curses.color_pair(1)
    if "not found" in status or status == "not selected":
        return curses.color_pair(3)
    return curses.color_pair(2) if "no code" in status else 0


class _Screen:
    """The checklist's screen: rows, how to describe one, the title and footer, the cursor and the scroll offset."""
    def __init__(self, rows, title, describe_row, footer):
        self.rows, self.title, self.describe_row, self.footer = rows, title, describe_row, footer
        self.cur, self.top = 0, 0

    def scroll(self, body: int):
        if self.cur < self.top:
            self.top = self.cur
        elif self.cur >= self.top + body:
            self.top = self.cur - body + 1

    def line(self, r) -> str:
        a, b, status = self.describe_row(r)
        return f"  {'[x]' if r['on'] else '[ ]'} {r['name']:<26.26s} {a:<24.24s} {b:<15.15s} {status}"


def _draw(scr, curses, s: "_Screen"):
    scr.erase()
    h, w = scr.getmaxyx()
    scr.addnstr(0, 0, f" {s.title}", w - 1, curses.A_BOLD)
    scr.addnstr(1, 0, "  space toggle · a all · n none · ↑↓/jk move · Enter apply · q cancel", w - 1, curses.color_pair(4))
    s.scroll(h - 4)
    for i, r in enumerate(s.rows[s.top:s.top + h - 4]):
        status = s.describe_row(r)[2]
        attr = curses.A_REVERSE if s.top + i == s.cur else 0
        scr.addnstr(3 + i, 0, s.line(r).ljust(w - 1), w - 1, attr | _row_colour(curses, status))
    on = sum(1 for r in s.rows if r["on"])
    scr.addnstr(h - 1, 0, f"  {on} of {len(s.rows)} selected -> {s.footer}", w - 1, curses.A_DIM)
    scr.refresh()


def _handle_key(curses, k: int, rows, cur: int):
    """(new cursor, result): result is None while browsing, a list on Enter, False on cancel."""
    if k in (curses.KEY_UP, ord("k")):
        return max(0, cur - 1), None
    if k in (curses.KEY_DOWN, ord("j")):
        return min(len(rows) - 1, cur + 1), None
    if k == ord(" "):
        rows[cur]["on"] = not rows[cur]["on"]
    elif k in (ord("a"), ord("n")):
        for r in rows:
            r["on"] = k == ord("a")
    elif k in (10, 13, curses.KEY_ENTER):
        return cur, [r["name"] for r in rows if r["on"]]
    elif k in (27, ord("q")):
        return cur, False
    return cur, None


def tui(scr, rows, title, describe_row, footer):
    import curses
    curses.curs_set(0)
    curses.use_default_colors()
    for n, colour in ((1, curses.COLOR_GREEN), (2, curses.COLOR_YELLOW), (3, curses.COLOR_RED), (4, curses.COLOR_CYAN)):
        curses.init_pair(n, colour, -1)
    s = _Screen(rows, title, describe_row, footer)
    while True:
        _draw(scr, curses, s)
        s.cur, result = _handle_key(curses, scr.getch(), rows, s.cur)
        if result is not None:
            return result or None


def report(project: Path, rows):
    print(f"Code folders in {project}\n")
    print(f"  {'FOLDER':26s} {'FILES':24s} {'MARKER':15s} STATUS")
    for r in rows:
        langs, marker, status = describe(r)
        print(f"  {r['name']:26s} {langs:24s} {marker:15s} {status}")
    print(f"\n  configured: {current_roots(project) or '-'}")


def _interactive() -> bool:
    return sys.stdin.isatty() and not os.environ.get("CI")


def _report_only(project: Path, rows: list, list_only: bool, yes: bool) -> bool:
    """Print the report instead of asking; True when that is all this run can do."""
    if not list_only and (yes or _interactive()):
        return False
    report(project, rows)
    if not list_only:
        print("  (no terminal to ask: run `aix code find` interactively, or `aix code find --yes` to accept the suggestions)")
    return True


def run(project: Path, yes: bool = False, list_only: bool = False, title: str = "aix code find") -> bool:
    """Show the checklist and write code_roots. Returns True when config changed."""
    rows = rows_for(project)
    if not rows:
        print(f"aix code find: no source files ({', '.join(sorted(EXT))}) under {project}")
        return False
    if _report_only(project, rows, list_only, yes):
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
