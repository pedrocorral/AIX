#!/usr/bin/env python3
"""aix upgrade — bring a project's copy of the kit up to this kit checkout, without touching the project's own work.

Ownership decides what happens to each path:
  kit-owned   (overwritten, removed if gone from the kit): .aix/scripts, .aix/templates, .aix/meta-docs, .aix/bin,
              .aix/skills/<every category except extern>, CLAUDE.md
  project-own (never touched): docs/requirements, tests, security, conflicts, operations, road-map, .aix/skills/extern,
              runtime folders, code
  merged:     AGENTS.md, GEMINI.md (kit text + project's "## Always-on skills" and "## Project notes" sections)
              .aix/config.yaml (kit text + project's disabled_skills line and style: block)
  1.x layout  a root framework.yaml: kit-owned folders are moved under .aix/ first (migrate_layout)
Runs from the KIT's scripts (not the project's), so it always carries the newest logic."""
import filecmp, re, shutil, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
KIT_OWNED_DIRS = [".aix/scripts", ".aix/templates", ".aix/meta-docs", ".aix/bin"]
KIT_OWNED_FILES = ["CLAUDE.md"]
MERGED_FILES = ["AGENTS.md", "GEMINI.md", ".aix/config.yaml"]  # GEMINI.md carries the always-on section like AGENTS.md
OLD_LAYOUT = {"scripts": ".aix/scripts", "templates": ".aix/templates", "skills": ".aix/skills", "docs/meta-docs": ".aix/meta-docs",
              "framework.yaml": ".aix/config.yaml"}
OLD_TEXT = [("docs/meta-docs/", ".aix/meta-docs/"), ("`skills/INDEX.md`", "`.aix/skills/INDEX.md`"), ("`skills/`", "`.aix/skills/`"),
            ("| `meta-docs/` |", "| `../.aix/meta-docs/` |"), ("`meta-docs/INDEX.md`", "`.aix/meta-docs/INDEX.md`"),
            ("`meta-docs/conventions/", "`.aix/meta-docs/conventions/"), ("framework.yaml", ".aix/config.yaml")]
KEEP_SECTIONS = ("## Always-on skills", "## Project notes")


def version_of(root: Path) -> str:
    m = re.search(r"^version:\s*([^\s#]+)", (root / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "?"


def skill_categories(root: Path):
    d = root / ".aix" / "skills"
    return [p.name for p in d.iterdir() if p.is_dir() and p.name != "extern"] if d.is_dir() else []


def kit_owned_paths():
    """Directories (kit-relative) that the kit owns outright inside a project."""
    return KIT_OWNED_DIRS + [f".aix/skills/{c}" for c in skill_categories(KIT)]


def diff_dir(src: Path, dst: Path):
    """Return (added, updated, removed) file lists comparing kit dir `src` with project dir `dst`."""
    added, updated, removed = [], [], []
    src_files = {p.relative_to(src) for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    dst_files = {p.relative_to(dst) for p in dst.rglob("*") if p.is_file() and "__pycache__" not in p.parts} if dst.exists() else set()
    for rel in sorted(src_files - dst_files):
        added.append(rel)
    for rel in sorted(src_files & dst_files):
        if not filecmp.cmp(src / rel, dst / rel, shallow=False):
            updated.append(rel)
    for rel in sorted(dst_files - src_files):
        removed.append(rel)
    return added, updated, removed


def plan(project: Path):
    """Everything the upgrade would do, as (label, action, path) rows."""
    rows = []
    for d in kit_owned_paths():
        a, u, r = diff_dir(KIT / d, project / d)
        rows += [(d, "add", x) for x in a] + [(d, "update", x) for x in u] + [(d, "remove", x) for x in r]
    for f in KIT_OWNED_FILES:
        src, dst = KIT / f, project / f
        if src.exists() and (not dst.exists() or not filecmp.cmp(src, dst, shallow=False)):
            rows.append((".", "update" if dst.exists() else "add", Path(f)))
    for f in MERGED_FILES:
        current = (project / f).read_text(encoding="utf-8") if (project / f).exists() else None
        if merged_text(project, f) != current:
            rows.append((".", "merge" if current is not None else "add", Path(f)))
    return rows


def section(text: str, header: str) -> str:
    """The section starting at `header` up to the next H2 (or end), or ''."""
    if header not in text:
        return ""
    rest = text.split(header, 1)[1]
    body = rest.split("\n## ", 1)[0]
    return header + body.rstrip("\n") + "\n\n"


def merged_text(project: Path, name) -> str:
    name = str(name)
    kit_text = (KIT / name).read_text(encoding="utf-8")
    proj_text = (project / name).read_text(encoding="utf-8") if (project / name).exists() else ""
    if name in ("AGENTS.md", "GEMINI.md"):
        out = kit_text
        for h in KEEP_SECTIONS:
            keep = section(proj_text, h)
            if keep and h not in out:
                out = out.rstrip("\n") + "\n\n" + keep
        return out
    out = kit_text  # config.yaml: kit text, but the project's disabled_skills line and style: block win
    m = re.search(r"^disabled_skills:.*$", proj_text, re.M)
    if m:
        out = re.sub(r"^disabled_skills:.*$", lambda _: m.group(0), out, count=1, flags=re.M) if re.search(r"^disabled_skills:", out, re.M) else out.rstrip("\n") + "\n" + m.group(0) + "\n"
    s = re.search(r"^style:\s*\n((?:[ \t]+\S.*\n?)+)", proj_text, re.M)
    if s:
        out = re.sub(r"^style:\s*\n((?:[ \t]+\S.*\n?)+)", lambda _: s.group(0), out, count=1, flags=re.M) if re.search(r"^style:", out, re.M) else out.rstrip("\n") + "\n" + s.group(0)
    return out


def apply(project: Path, rows):
    for d, action, rel in rows:
        src, dst = KIT / d / rel, project / d / rel
        if action == "remove":
            dst.unlink()
            parent = dst.parent
            while parent != project and not any(parent.iterdir()):
                parent.rmdir(); parent = parent.parent
        elif action == "merge" or (d == "." and str(rel) in MERGED_FILES):
            dst.write_text(merged_text(project, rel), encoding="utf-8")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy_content(src, dst)


def copy_content(src: Path, dst: Path):
    """Copy bytes and the executable bit only. Never copy ownership or timestamps: the project's files may belong
    to another user (shared checkout, /tmp copy) and utime/chown would fail there."""
    import os, stat
    shutil.copyfile(src, dst)
    if os.access(src, os.X_OK):
        try:
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError:
            pass


def line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def line_delta(src: Path, dst: Path, new_text: str = None) -> str:
    """'+a -r lines' from the project's file to what the upgrade would write (the kit file, or `new_text`)."""
    import difflib
    a = dst.read_text(encoding="utf-8", errors="replace").splitlines() if dst.exists() else []
    b = new_text.splitlines() if new_text is not None else src.read_text(encoding="utf-8", errors="replace").splitlines()
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    return f"+{added} -{removed} lines"


def describe(project: Path, d: str, action: str, rel: Path, edited=()) -> str:
    """One verbose line for the dry run: what happens to this file and how big the change is."""
    src, dst = KIT / d / rel, project / d / rel
    shown = f"{d}/{rel}" if d != "." else str(rel)
    warn = "  !! LOCAL EDIT WILL BE LOST (move the change to the kit)" if shown.startswith(".aix/") and shown[5:] in edited else ""
    if warn and action == "update":
        return f"  update  {shown}  ({line_delta(src, dst)}){warn}"
    if action == "add":
        return f"  add     {shown}  ({line_count(src)} lines, new in kit)"
    if action == "remove":
        return f"  remove  {shown}  ({line_count(dst)} lines, no longer in kit)"
    if action == "merge":
        kept = [h for h in KEEP_SECTIONS if section(dst.read_text(encoding="utf-8"), h)] if dst.exists() else []
        keep = ", keeping your " + " and ".join(f"'{h[3:]}'" for h in kept) if kept else ""
        if rel.name == "config.yaml":
            keep = ", keeping your disabled_skills and style limits"
        return f"  merge   {shown}  (kit text{keep}; {line_delta(src, dst, merged_text(project, rel))})"
    return f"  update  {shown}  ({line_delta(src, dst)})"


def confirm(question: str) -> bool:
    if not sys.stdin.isatty():
        sys.exit("no terminal to confirm; rerun with --yes")
    return input(question).strip().lower() in ("y", "yes")


def old_layout(project: Path) -> bool:
    return (project / "framework.yaml").exists() and not (project / ".aix" / "config.yaml").exists()


def migrate_layout(project: Path, dry: bool):
    """1.x layout -> 2.0: kit-owned folders move under .aix/, root launchers go, pointer texts are rewritten.
    Project-owned docs, code, runtime folders and git history are untouched (moves are plain renames)."""
    moves = [(project / src, project / dst) for src, dst in OLD_LAYOUT.items() if (project / src).exists()]
    print("  1.x layout detected: migrating to .aix/ (kit-owned folders move; only the root launchers are deleted)")
    for src, dst in moves:
        print(f"    move    {src.relative_to(project)} -> {dst.relative_to(project)}")
    for f in ("aix", "aix.cmd"):
        if (project / f).exists():
            print(f"    remove  {f}  (the aix on PATH runs .aix/scripts/aix.py)")
    if dry:
        return
    (project / ".aix").mkdir(exist_ok=True)
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
    for f in ("aix", "aix.cmd"):
        if (project / f).exists():
            (project / f).unlink()
    for f in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md", ".cursor/rules/aix.mdc", "docs/INDEX.md"):
        p = project / f
        if p.exists():
            text = p.read_text(encoding="utf-8")
            for a, b in OLD_TEXT:
                text = text.replace(a, b)
            p.write_text(text, encoding="utf-8")


def main(args):
    yes, dry = "--yes" in args, "--dry-run" in args
    args = [a for a in args if a not in ("--yes", "--dry-run")]
    from project import find_project
    project = Path(args[0]).resolve() if args else find_project(Path.cwd())
    if project is None or not ((project / ".aix" / "config.yaml").exists() or (project / "framework.yaml").exists()):
        sys.exit("aix upgrade: no project found (nearest .aix/config.yaml, or a 1.x framework.yaml); pass the project path")
    if old_layout(project):
        if not dry and not yes and not confirm("  Migrate this project's kit files into .aix/ (2.0 layout)? [y/N] "):
            sys.exit("aborted")
        migrate_layout(project, dry)
        if dry:
            print("  (after the migration, the plan below would apply)")
            return
    if project == KIT:
        sys.exit("aix upgrade: you are running this project's own copy of aix, which cannot upgrade itself. "
                 "Run the kit checkout's aix (the one on PATH, or /path/to/kit/aix upgrade) from inside the project.")
    rows = plan(project)
    print(f"upgrade {project}\n  kit {version_of(KIT)} (this checkout: {KIT})  ->  project {version_of(project)}")
    if not rows:
        print("  already up to date"); return
    counts = {a: sum(1 for _, x, _ in rows if x == a) for a in ("add", "update", "remove", "merge")}
    print("  plan: " + ", ".join(f"{n} {a}" for a, n in counts.items() if n) + (" (dry run, nothing written)" if dry else ""))
    import install_skills as inst
    edited = set(inst.modified_kit_files(project) or [])
    for area in dict.fromkeys(d for d, _, _ in rows):
        print(f"  [{area if area != '.' else 'root'}]")
        for d, action, rel in rows:
            if d == area:
                print("  " + describe(project, d, action, rel, edited))
    if edited:
        print(f"  !! {len(edited)} kit-owned file(s) were edited in this project; upgrade overwrites them (see lines above)")
    print("  untouched: docs/ (requirements, tests, security, conflicts, operations, road-map), .aix/skills/extern, your config values, runtime folders, your code")
    if dry:
        print("  then: relink skills in the project (aix install) and suggest aix doctor + aix docs validate")
        return
    print("\n  WARNING: `aix upgrade` is an experimental feature. Kit-owned files listed above are overwritten;\n"
          "  your git history is the backup. Review the plan before answering.")
    if not yes and not confirm("  Are you sure you want to use this? [y/N] "):
        sys.exit("aborted")
    apply(project, rows)
    inst.write_manifest(project)
    print(f"  applied {len(rows)} changes; relinking skills in the project")
    subprocess.call([sys.executable, str(project / ".aix" / "scripts" / "aix.py"), "install"], cwd=project, stdout=subprocess.DEVNULL)
    print("  done. Run `aix doctor` and `aix docs validate` in the project.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:])
