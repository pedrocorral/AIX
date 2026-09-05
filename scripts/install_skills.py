#!/usr/bin/env python3
"""Install AIX skills into agent runtime folders (and optionally copy the kit into an existing project).

Source of truth: skills/<category>/<name>/SKILL.md  (nested, human-organised)
Runtimes expect:  <target>/<flat-name>/SKILL.md      (flat, one folder per skill)
flat-name = path components joined with '-'  (skills/security/audit-injection -> security-audit-injection)
The `name:` in each SKILL.md front-matter MUST equal the flat name (validate.py checks this).
"""
import argparse, os, shutil, sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
TARGETS = [".opencode/skills", ".claude/skills", ".github/skills", ".agents/skills", ".cursor/skills"]
KIT_PAYLOAD = [  # AIX-DEVELOPMENT.md is intentionally NOT here (kit-development only)
    "AGENTS.md", "CLAUDE.md", "framework.yaml", "docs", "skills", "templates", "scripts", "aix", "aix.cmd"]


def flat_name(rel_parts):
    """skills/<cat>/<name> -> cat-name; skills/extern/<name> -> name (third-party skills keep their own name)."""
    return "-".join(rel_parts[1:]) if rel_parts[0] == "extern" else "-".join(rel_parts)


def leaf_skills(skills_dir: Path):
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        rel = skill_md.parent.relative_to(skills_dir)
        yield skill_md.parent, flat_name(rel.parts)


def link_or_copy(src: Path, dst: Path, copy: bool):
    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        shutil.copytree(src, dst)
        return "copied"
    try:
        os.symlink(os.path.relpath(src, dst.parent), dst, target_is_directory=True)
        return "linked"
    except (OSError, NotImplementedError):
        shutil.copytree(src, dst)
        return "copied (symlink unavailable)"


def disabled_skills(project: Path):
    import re
    m = re.search(r"^disabled_skills:\s*\[(.*?)\]", (project / "framework.yaml").read_text(encoding="utf-8"), re.M)
    return {s.strip() for s in m.group(1).split(",") if s.strip()} if m else set()


def prune_dangling(project: Path):
    """Remove runtime links whose skill folder no longer exists (skill removed or renamed)."""
    for t in TARGETS:
        d = project / t
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_symlink() and not p.exists():
                p.unlink(); print(f"  {p.name:40s} -> pruned (source gone)")


def install_into(project: Path, copy: bool):
    skills_dir = project / "skills"
    if not skills_dir.exists():
        sys.exit(f"no skills/ folder in {project}")
    n = 0
    off = disabled_skills(project)
    prune_dangling(project)
    for src, flat in leaf_skills(skills_dir):
        if flat in off:
            for t in TARGETS:
                p = project / t / flat
                if p.is_symlink() or p.is_file(): p.unlink()
                elif p.is_dir(): shutil.rmtree(p)
            print(f"  {flat:40s} -> disabled (framework.yaml)")
            continue
        for t in TARGETS:
            mode = link_or_copy(src, project / t / flat, copy)
        n += 1
        print(f"  {flat:40s} -> {', '.join(TARGETS)} ({mode})")
    # pointer files for runtimes that do not read AGENTS.md
    gh = project / ".github" / "copilot-instructions.md"
    if not gh.exists():
        gh.parent.mkdir(parents=True, exist_ok=True)
        gh.write_text("Read and follow `AGENTS.md` at the repository root before doing anything.\n")
    cur = project / ".cursor" / "rules" / "aix.mdc"
    if not cur.exists():
        cur.parent.mkdir(parents=True, exist_ok=True)
        cur.write_text("---\ndescription: AIX agent contract\nalwaysApply: true\n---\nRead and follow `AGENTS.md` at the repository root before doing anything. Skills are in `.cursor/skills/`.\n")
    state = project / "docs" / "road-map" / "going-on" / "STATE.md"
    if not state.exists():
        shutil.copy(project / "templates" / "session-state.md", state)
    print(f"installed {n} skills into {project}")


CHOICES = "[r]eplace  [s]kip  [m]erge  [R]eplace all  [S]kip all  [M]erge all  [a]bort"


def ask_collision(item: str, is_dir: bool, remembered: dict) -> str:
    """Return one of replace/skip/merge/abort for an existing payload item; honours 'all' answers."""
    if remembered.get("all"):
        return remembered["all"]
    if not sys.stdin.isatty():
        sys.exit(f"'{item}' already exists and no terminal to ask; rerun with --replace-all, --skip-all or --merge-all")
    kind = "folder" if is_dir else "file"
    while True:
        ans = input(f"  {item} ({kind}) exists. {CHOICES}: ").strip()
        table = {"r": "replace", "s": "skip", "m": "merge", "a": "abort"}
        if ans in ("R", "S", "M"):
            remembered["all"] = table[ans.lower()]
            return remembered["all"]
        if ans in table:
            return table[ans]
        print("    please answer r, s, m, R, S, M or a")


def merge_dir(src: Path, dst: Path):
    """Add files from src that dst lacks; never overwrite. Returns number of files added."""
    added = 0
    for f in src.rglob("*"):
        if f.is_dir():
            continue
        target = dst / f.relative_to(src)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, target)
            added += 1
    return added


def replace_item(src: Path, dst: Path):
    """Move the existing item to <name>.bak (previous .bak removed) and copy the kit's version in."""
    bak = dst.with_name(dst.name + ".bak")
    if bak.is_dir() and not bak.is_symlink():
        shutil.rmtree(bak)
    elif bak.exists() or bak.is_symlink():
        bak.unlink()
    dst.rename(bak)
    shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)


def copy_kit_into(project: Path, on_collision: str = "ask"):
    """Copy KIT_PAYLOAD into project. on_collision: ask | replace | skip | merge."""
    project.mkdir(parents=True, exist_ok=True)
    remembered = {} if on_collision == "ask" else {"all": on_collision}
    for item in KIT_PAYLOAD:
        src, dst = KIT_ROOT / item, project / item
        if not dst.exists():
            shutil.copytree(src, dst) if src.is_dir() else shutil.copy(src, dst)
            print(f"  added: {item}")
            continue
        choice = ask_collision(item, src.is_dir(), remembered)
        if choice == "abort":
            sys.exit("aborted; items already added above were left in place")
        if choice == "skip":
            print(f"  skipped: {item}")
        elif choice == "merge" and src.is_dir():
            print(f"  merged: {item} (+{merge_dir(src, dst)} files, nothing overwritten)")
        elif choice == "merge":
            print(f"  skipped: {item} (files cannot be merged)")
        else:
            replace_item(src, dst)
            print(f"  replaced: {item} (old kept as {item}.bak)")
    if (project / "AGENTS.md").exists() and on_collision != "replace":
        print("NOTE: if the project already had agent instructions, merge them into AGENTS.md section 5.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--copy", action="store_true", help="copy skills instead of symlinking")
    ap.add_argument("--into", type=Path, help="install the whole kit into an existing project")
    ap.add_argument("--replace-all", action="store_true"); ap.add_argument("--skip-all", action="store_true"); ap.add_argument("--merge-all", action="store_true")
    a = ap.parse_args()
    if a.into:
        mode = "replace" if a.replace_all else "skip" if a.skip_all else "merge" if a.merge_all else "ask"
        copy_kit_into(a.into.resolve(), mode)
        install_into(a.into.resolve(), a.copy)
    else:
        install_into(KIT_ROOT, a.copy)
