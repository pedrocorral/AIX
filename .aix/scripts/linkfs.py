"""Leaf: the skill folders the agents read and how a skill gets there. Flat names (`security-audit-injection`),
the leaf skills of a tree, and one link or copy per skill into each selected agent's folder."""
import os, shutil
from pathlib import Path

import agents


TARGETS = [a["skills"] for a in agents.AGENTS.values() if a["skills"]]  # every folder the kit knows; a project links the selected ones


def flat_name(rel_parts):
    """.aix/skills/<cat>/<name> -> cat-name; .aix/skills/extern/<name> -> name (third-party skills keep their own name)."""
    return "-".join(rel_parts[1:]) if rel_parts[0] == "extern" else "-".join(rel_parts)


def leaf_skills(skills_dir: Path):
    for skill_md in sorted(skills_dir.rglob("SKILL.md")):
        rel = skill_md.parent.relative_to(skills_dir)
        yield skill_md.parent, flat_name(rel.parts)


def link_or_copy(src: Path, dst: Path, copy: bool):
    if not copy and dst.is_symlink() and dst.resolve() == src.resolve():
        return "linked"  # already right: touch nothing (the kit checkout may belong to another user)
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
