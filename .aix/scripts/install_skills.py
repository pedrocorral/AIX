#!/usr/bin/env python3
"""Install AIX skills into agent runtime folders (and optionally copy the kit into an existing project).

Source of truth: .aix/skills/<category>/<name>/SKILL.md  (nested, human-organised)
Runtimes expect:  <target>/<flat-name>/SKILL.md      (flat, one folder per skill)
flat-name = path components joined with '-'  (.aix/skills/security/audit-injection -> security-audit-injection)
The `name:` in each SKILL.md front-matter MUST equal the flat name (validate.py checks this).
"""
import argparse, os, shutil, sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
import agents  # which agents (Claude, Copilot, Cursor, Gemini, OpenCode, Codex) the project equips: folders and pointer files
TARGETS = [a["skills"] for a in agents.AGENTS.values() if a["skills"]]  # every folder the kit knows; a project links the selected ones
import payload  # THE list of what travels into a project (shared with upgrade, manifest, doctor)
from seed import POINTERS, copy_kit_into, pointer_text, seed_project


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


def kit_owned_files(project: Path):
    """Files the kit owns inside a project: payload.py's `owned` items (never config.yaml, custom/, org/, extern downloads, index, manifest)."""
    for rel in payload.files(project, payload.OWNED):
        yield project / rel


def write_manifest(project: Path):
    """.aix/manifest.json: sha256 of every kit-owned file, so doctor and upgrade can see local edits."""
    import hashlib, json
    digest = {f.relative_to(project).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in kit_owned_files(project)}
    (project / ".aix" / "manifest.json").write_text(json.dumps({"files": digest}, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    return len(digest)


def modified_kit_files(project: Path):
    """Kit-owned files whose content differs from the manifest (edited locally: lost on the next upgrade)."""
    import hashlib, json
    m = project / ".aix" / "manifest.json"
    if not m.exists():
        return None
    recorded = json.loads(m.read_text(encoding="utf-8")).get("files", {})
    out = []
    for f in kit_owned_files(project):
        rel = f.relative_to(project).as_posix()
        key = rel if rel in recorded else rel[5:] if rel.startswith(".aix/") and rel[5:] in recorded else None  # manifests before 2.12.0 were .aix-relative
        if key and hashlib.sha256(f.read_bytes()).hexdigest() != recorded[key]:
            out.append(rel)
    return sorted(out)


def install_into(project: Path, copy: bool):
    skills_dir = project / ".aix" / "skills"
    if not skills_dir.exists():
        sys.exit(f"no .aix/skills folder in {project}")
    try:
        if not (project / "AIX-DEVELOPMENT.md").exists():
            seed_project(project)  # a project without docs/ (e.g. installed before the seed existed) gets it now
        for rel, bak in agents.backup_foreign(project):
            print(f"  {rel} was not AIX's: kept as {bak}")
        prune_dangling(project)
        n = _install_links(project, skills_dir, copy, disabled_skills(project))
        _pointer_files(project)
    except PermissionError as e:
        sys.exit(f"aix install: cannot write {e.filename}: {project} belongs to another user, whose skill links are already in place "
                 f"(they run `aix install` there). Your PATH link is done; your own projects need `aix install --into DIR`.")
    print(f"installed {n} skills into {project} for {', '.join(agents.selected(project))}")


def _unlink_everywhere(project: Path, targets, flat: str):
    import catalog
    catalog.unlink_everywhere(flat, project, targets)


def _link_one(project: Path, targets, flat: str, info: dict, copy: bool):
    mode = "-"
    for t in targets:
        mode = link_or_copy(info["path"], project / t / flat, copy)
    origin = "" if info["layer"] == "kit" and not info["chosen_by"].startswith("config") else f"  [{info['chosen_by']}]"
    print(f"  {flat:40s} -> {', '.join(targets) or 'AGENTS.md only'} ({mode}){origin}")


def _install_links(project: Path, skills_dir: Path, copy: bool, off) -> int:
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


INS_HEADER = "## Scoped instructions"


MANAGED = ("## Organisation", "## Scoped instructions", "## Cycle", "## Always-on skills", "## Project notes")


def render_agents(project: Path, profile) -> bool:
    """Assemble AGENTS.md from the instruction blocks (kit defaults, overridden or extended by layers); the managed
    sections written by other commands are kept as they are. Returns True when the file changed."""
    import layers
    blocks = sorted((v for v in layers.instructions(project, profile).values() if v["block"]), key=lambda v: (v["order"], v["section"]))
    if not blocks:
        return False
    out = []
    for b in blocks:
        body = b["path"].read_text(encoding="utf-8")
        body = body[body.find("\n---", 3) + 4:].strip("\n") if body.startswith("---") else body.strip("\n")
        out.append((f"## {b['section']}\n" if b["section"] else "") + body + "\n")
    text = "\n".join(out)
    f = project / "AGENTS.md"
    old = f.read_text(encoding="utf-8") if f.exists() else ""
    for header in MANAGED:
        kept = _section_text(old, header)
        if kept:
            text = text.rstrip("\n") + "\n\n" + kept
    changed = text != old
    f.write_text(text, encoding="utf-8")
    return changed


def _section_text(text: str, header: str) -> str:
    if header not in text:
        return ""
    body = text.split(header, 1)[1].split("\n## ", 1)[0]
    return header + body.rstrip("\n") + "\n"


def _instruction_body(v: dict) -> str:
    body = v["path"].read_text(encoding="utf-8")
    return body[body.find("\n---", 3) + 4:].lstrip("\n") if body.startswith("---") else body


def _render_native(project: Path, chosen, iid: str, v: dict):
    """The Copilot and Cursor files for one scoped instruction, when those agents are selected."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", iid.lower()).strip("-")
    slug = slug[4:] if slug.startswith("aix-") else slug  # the file already carries the aix- prefix
    body, apply = _instruction_body(v), (",".join(v["applyTo"]) if v["applyTo"] else "**")
    if "copilot" in chosen:
        gh = project / ".github" / "instructions"
        gh.mkdir(parents=True, exist_ok=True)
        (gh / f"aix-{slug}.instructions.md").write_text(f"---\ndescription: \"{v['description']}\"\napplyTo: \"{apply}\"\n---\n{body}", encoding="utf-8")
    if "cursor" in chosen:
        cur = project / ".cursor" / "rules"
        cur.mkdir(parents=True, exist_ok=True)
        always = "true" if v["always"] or not v["applyTo"] else "false"
        (cur / f"aix-{slug}.mdc").write_text(f"---\ndescription: {v['description']}\nglobs: {apply}\nalwaysApply: {always}\n---\n{body}", encoding="utf-8")


def _instruction_line(project: Path, iid: str, v: dict) -> str:
    shown = v["path"].relative_to(project) if v["path"].is_relative_to(project) else v["path"]
    scope = "always" if v["always"] or not v["applyTo"] else "when touching " + ", ".join(v["applyTo"])
    return f"- `{iid}` ({scope}): read `{shown}` — {v['description']}"


def _write_section(project: Path, files, header: str, section: str):
    for name in files:
        f = project / name
        if f.exists():
            f.write_text(_replace_section(f.read_text(encoding="utf-8"), header, section), encoding="utf-8")


def _clear_rendered(project: Path):
    for d, pat in ((project / ".github" / "instructions", "aix-*.instructions.md"), (project / ".cursor" / "rules", "aix-*.mdc")):
        for old in (d.glob(pat) if d.is_dir() else []):
            old.unlink()


def _rendered_where(chosen) -> list:
    return [x for x, ok in (("AGENTS.md", True), (".github/instructions/aix-*.instructions.md", "copilot" in chosen), (".cursor/rules/aix-*.mdc", "cursor" in chosen)) if ok]


def render_instructions(project: Path, profile):
    """Scoped instructions -> native files per agent (git-ignored, regenerated) + managed sections in AGENTS.md/GEMINI.md."""
    import layers, policy
    if render_agents(project, profile):
        print("  AGENTS.md assembled from instruction blocks")
    ins = {k: v for k, v in layers.instructions(project, profile).items() if not v["block"]}
    chosen = agents.selected(project)
    _clear_rendered(project)
    lines = []
    for iid, v in sorted(ins.items()):
        _render_native(project, chosen, iid, v)
        lines.append(_instruction_line(project, iid, v))
    section = (INS_HEADER + "\nRead these before working on matching files:\n" + "\n".join(lines) + "\n\n") if lines else ""
    _write_section(project, ("AGENTS.md", "GEMINI.md"), INS_HEADER, section)
    _write_section(project, ("AGENTS.md",), "## Cycle", policy.cycle_section(project))
    org = (profile or {}).get("router") or _org_fragment(project)
    _write_section(project, ("AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md"), "## Organisation", ("## Organisation\n" + org.strip() + "\n\n") if org else "")
    if lines:
        print(f"  rendered {len(lines)} scoped instruction(s) -> {', '.join(_rendered_where(chosen))}")


def _org_fragment(project: Path) -> str:
    for d in (project / ".aix" / "custom", project / ".aix" / "org"):
        f = d / "AGENTS.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return ""


def _replace_section(text: str, header: str, section: str) -> str:
    """Replace (or append, or remove when empty) the managed H2 `header` block."""
    if header in text:
        head, rest = text.split(header, 1)
        tail = rest.split("\n## ", 1)
        remainder = ("## " + tail[1]) if len(tail) > 1 else ""
        return head + section + remainder
    return (text.rstrip("\n") + "\n\n" + section) if section else text


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
