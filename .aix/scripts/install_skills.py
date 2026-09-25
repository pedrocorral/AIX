#!/usr/bin/env python3
"""Apply the kit to a project: links or copies of every chosen skill into the selected agents' folders, AGENTS.md and
the instruction files rendered, pointer files and STATE.md laid down, the manifest written. `install_into` is the one
operation; the commands that change a choice return True and aix.py runs it once (composition at the root).

Source of truth: .aix/skills/<category>/<name>/SKILL.md  (nested, human-organised)
Runtimes expect:  <target>/<flat-name>/SKILL.md      (flat, one folder per skill)
flat-name = path components joined with '-'  (.aix/skills/security/audit-injection -> security-audit-injection)
The `name:` in each SKILL.md front-matter MUST equal the flat name (validate.py checks this).
"""
import argparse, shutil, sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
import agents  # which agents (Claude, Copilot, Cursor, Gemini, OpenCode, Codex) the project equips: folders and pointer files
from agentsmd import render_instructions
from linkfs import link_or_copy
from manifest import write_manifest
from seed import POINTERS, copy_kit_into, pointer_text, seed_project


def disabled_skills(project: Path):
    import re
    m = re.search(r"^disabled_skills:\s*\[(.*?)\]", (project / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    return {s.strip() for s in m.group(1).split(",") if s.strip()} if m else set()


def prune_dangling(project: Path):
    """Remove agent links whose skill folder no longer exists (skill removed or renamed)."""
    for t in agents.skill_dirs(project):
        d = project / t
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if p.is_symlink() and not p.exists():
                p.unlink(); print(f"  {p.name:40s} -> pruned (source gone)")


def _prepare(project: Path):
    """What must be in place before the links: the seeded docs, the foreign files backed up, dangling links gone."""
    if not (project / "AIX-DEVELOPMENT.md").exists():
        seed_project(project)  # a project without docs/ (e.g. installed before the seed existed) gets it now
    for rel, bak in agents.backup_foreign(project):
        print(f"  {rel} was not AIX's: kept as {bak}")
    prune_dangling(project)


def _apply(project: Path, copy: bool):
    """The links, the rendered files, the pointer files and STATE.md; says what it did."""
    n = _install_links(project, copy, disabled_skills(project))
    _pointer_files(project)
    print(f"installed {n} skills into {project} for {', '.join(agents.selected(project))}")


def install_into(project: Path, copy: bool):
    """The one operation that applies the kit to a project; aix.py runs it after any command that changed a choice."""
    if not (project / ".aix" / "skills").exists():
        sys.exit(f"no .aix/skills folder in {project}")
    try:
        _prepare(project)
        _apply(project, copy)
    except PermissionError as e:
        sys.exit(f"aix install: cannot write {e.filename}: {project} belongs to another user, whose skill links are already in place "
                 f"(they run `aix install` there). Your PATH link is done; your own projects need `aix install --into DIR`.")


def _unlink_everywhere(project: Path, targets, flat: str):
    import catalog
    catalog.unlink_everywhere(flat, project, targets)


def _link_one(project: Path, targets, flat: str, info: dict, copy: bool):
    mode = "-"
    for t in targets:
        mode = link_or_copy(info["path"], project / t / flat, copy)
    origin = "" if info["layer"] == "kit" and not info["chosen_by"].startswith("config") else f"  [{info['chosen_by']}]"
    print(f"  {flat:40s} -> {', '.join(targets) or 'AGENTS.md only'} ({mode}){origin}")


def _install_links(project: Path, copy: bool, off) -> int:
    import layers
    profile = layers.active_profile(project)
    active, layer_disabled = layers.resolve(project, profile)
    targets = agents.skill_dirs(project)
    for flat, layer in layer_disabled.items():  # removed by a DISABLED file in a higher layer
        _unlink_everywhere(project, targets, flat)
        print(f"  {flat:40s} -> disabled by the {layer} layer")
    n = 0
    for flat, info in sorted(active.items()):
        if flat in off:
            _unlink_everywhere(project, targets, flat)
            print(f"  {flat:40s} -> disabled (.aix/config.yaml)")
            continue
        _link_one(project, targets, flat, info, copy)
        n += 1
    render_instructions(project, profile)
    layers.write_index(project)
    return n


def _pointer_files(project: Path):
    """Pointer files for the selected agents that do not read AGENTS.md by themselves (text from templates/pointers/, a
    layer's copy winning), STATE.md, and the kit-file manifest (projects only)."""
    for agent, (rel, text) in POINTERS.items():
        f = project / rel
        if agent in agents.selected(project) and not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(pointer_text(project, Path(rel).name, text), encoding="utf-8")
    state = project / "docs" / "road-map" / "going-on" / "STATE.md"
    if not state.exists():
        state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(project / ".aix" / "templates" / "session-state.md", state)
    if (project / ".aix").is_dir() and not (project / "AIX-DEVELOPMENT.md").exists():
        write_manifest(project)  # projects only: the kit checkout is edited by design


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
