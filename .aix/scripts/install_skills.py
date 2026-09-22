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
TARGETS = [".opencode/skills", ".claude/skills", ".github/skills", ".agents/skills", ".cursor/skills"]
import payload  # THE list of what travels into a project (shared with upgrade, manifest, doctor)


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
    """Remove runtime links whose skill folder no longer exists (skill removed or renamed)."""
    for t in TARGETS:
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
        prune_dangling(project)
        n = _install_links(project, skills_dir, copy, disabled_skills(project))
        _pointer_files(project)
    except PermissionError as e:
        sys.exit(f"aix install: cannot write {e.filename}: {project} belongs to another user, whose skill links are already in place "
                 f"(they run `aix install` there). Your PATH link is done; your own projects need `aix install --into DIR`.")
    print(f"installed {n} skills into {project}")


def _install_links(project: Path, skills_dir: Path, copy: bool, off) -> int:
    import layers
    profile = layers.active_profile(project)
    active, layer_disabled = layers.resolve(project, profile)
    for flat, layer in layer_disabled.items():  # removed by a DISABLED file in a higher layer
        for t in TARGETS:
            p = project / t / flat
            if p.is_symlink() or p.is_file(): p.unlink()
            elif p.is_dir(): shutil.rmtree(p)
        print(f"  {flat:40s} -> disabled by the {layer} layer")
    n = 0
    for flat, info in sorted(active.items()):
        src = info["path"]
        if flat in off:
            for t in TARGETS:
                p = project / t / flat
                if p.is_symlink() or p.is_file(): p.unlink()
                elif p.is_dir(): shutil.rmtree(p)
            print(f"  {flat:40s} -> disabled (.aix/config.yaml)")
            continue
        for t in TARGETS:
            mode = link_or_copy(src, project / t / flat, copy)
        n += 1
        origin = "" if info["layer"] == "kit" and not info["chosen_by"].startswith("config") else f"  [{info['chosen_by']}]"
        print(f"  {flat:40s} -> {', '.join(TARGETS)} ({mode}){origin}")
    render_instructions(project, profile)
    layers.write_index(project)
    return n


INS_HEADER = "## Scoped instructions"


MANAGED = ("## Organisation", "## Scoped instructions", "## Always-on skills", "## Project notes")


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


def render_instructions(project: Path, profile):
    if render_agents(project, profile):
        print("  AGENTS.md assembled from instruction blocks")
    """Scoped instructions -> native files per runtime (git-ignored, regenerated) + a managed section in AGENTS.md/GEMINI.md."""
    import layers, re
    ins = {k: v for k, v in layers.instructions(project, profile).items() if not v["block"]}
    gh, cur = project / ".github" / "instructions", project / ".cursor" / "rules"
    for d, pat in ((gh, "aix-*.instructions.md"), (cur, "aix-*.mdc")):
        for old in (d.glob(pat) if d.is_dir() else []):
            old.unlink()
    lines = []
    for iid, v in sorted(ins.items()):
        slug = re.sub(r"[^a-z0-9]+", "-", iid.lower()).strip("-")
        slug = slug[4:] if slug.startswith("aix-") else slug  # the file already carries the aix- prefix
        body = v["path"].read_text(encoding="utf-8")
        body = body[body.find("\n---", 3) + 4:].lstrip("\n") if body.startswith("---") else body
        gh.mkdir(parents=True, exist_ok=True); cur.mkdir(parents=True, exist_ok=True)
        apply = ",".join(v["applyTo"]) if v["applyTo"] else "**"
        (gh / f"aix-{slug}.instructions.md").write_text(f"---\ndescription: \"{v['description']}\"\napplyTo: \"{apply}\"\n---\n{body}", encoding="utf-8")
        (cur / f"aix-{slug}.mdc").write_text(f"---\ndescription: {v['description']}\nglobs: {apply}\nalwaysApply: {'true' if v['always'] or not v['applyTo'] else 'false'}\n---\n{body}", encoding="utf-8")
        shown = v["path"].relative_to(project) if v["path"].is_relative_to(project) else v["path"]
        scope = "always" if v["always"] or not v["applyTo"] else "when touching " + ", ".join(v["applyTo"])
        lines.append(f"- `{iid}` ({scope}): read `{shown}` — {v['description']}")
    section = (INS_HEADER + "\nRead these before working on matching files:\n" + "\n".join(lines) + "\n\n") if lines else ""
    for f in (project / "AGENTS.md", project / "GEMINI.md"):
        if f.exists():
            f.write_text(_replace_section(f.read_text(encoding="utf-8"), INS_HEADER, section), encoding="utf-8")
    org = (profile or {}).get("router") or _org_fragment(project)
    org_section = ("## Organisation\n" + org.strip() + "\n\n") if org else ""
    for f in (project / "AGENTS.md", project / "GEMINI.md", project / ".github" / "copilot-instructions.md"):
        if f.exists():
            f.write_text(_replace_section(f.read_text(encoding="utf-8"), "## Organisation", org_section), encoding="utf-8")
    if lines:
        print(f"  rendered {len(lines)} scoped instruction(s) -> .github/instructions/aix-*.instructions.md, .cursor/rules/aix-*.mdc, AGENTS.md")


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
    """Pointer files for runtimes that do not read AGENTS.md, STATE.md, and the kit-file manifest (projects only)."""
    gh = project / ".github" / "copilot-instructions.md"
    if not gh.exists():
        gh.parent.mkdir(parents=True, exist_ok=True)
        gh.write_text("Read and follow `AGENTS.md` at the repository root before doing anything.\n")
    cur = project / ".cursor" / "rules" / "aix.mdc"
    if not cur.exists():
        cur.parent.mkdir(parents=True, exist_ok=True)
        cur.write_text("---\ndescription: AIX agent contract\nalwaysApply: true\n---\nRead and follow `AGENTS.md` at the repository root before doing anything. Skills are in `.cursor/skills/`.\n")
    gem = project / "GEMINI.md"  # Gemini CLI reads GEMINI.md and .agents/skills; Antigravity reads AGENTS.md and .agents/skills natively
    if not gem.exists():
        gem.write_text("Read and follow `AGENTS.md` at the repository root. It is the single source of agent instructions for this project. Skills are available under `.agents/skills/` (installed from `.aix/skills/` by `aix install`).\n")
    state = project / "docs" / "road-map" / "going-on" / "STATE.md"
    if not state.exists():
        shutil.copy(project / ".aix" / "templates" / "session-state.md", state)
    if (project / ".aix").is_dir() and not (project / "AIX-DEVELOPMENT.md").exists():
        write_manifest(project)  # projects only: the kit checkout is edited by design


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
        if f.is_dir() or any(part in ("custom", "org", "__pycache__") for part in f.relative_to(src).parts) or f.name == "index.json":
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
    copy_item(src, dst)


def copy_item(src: Path, dst: Path):
    """Copy one payload item (file or folder) without the ignored parts (__pycache__, *.pyc)."""
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*payload.IGNORED_PARTS, *("*" + s for s in payload.IGNORED_SUFFIXES)))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def copy_kit_into(project: Path, on_collision: str = "ask"):
    """Copy payload.items() into project. on_collision: ask | replace | skip | merge."""
    project.mkdir(parents=True, exist_ok=True)
    remembered = {} if on_collision == "ask" else {"all": on_collision}
    for item, _mode in payload.items(KIT_ROOT):
        src, dst = KIT_ROOT / item, project / item
        if not src.exists():
            continue
        if not dst.exists():
            copy_item(src, dst)
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
