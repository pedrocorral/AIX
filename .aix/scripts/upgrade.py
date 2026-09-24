#!/usr/bin/env python3
"""aix upgrade — bring a project's copy of the kit up to this kit checkout, without touching the project's own work.

What may change is decided by payload.py, the same list `aix install` copies (nothing else is ever touched):
  owned   overwritten, removed if gone from the kit (scripts, bin, templates, meta-docs, instructions, profiles,
          skill categories, skills/INDEX.md, skills/extern/registry.json, policies, CLAUDE.md)
  merged  AGENTS.md, GEMINI.md (kit text + project's "## Always-on skills" and "## Project notes" sections)
          .aix/config.yaml (kit text + project's disabled_skills, instructions, profile, use, source, paths.code_roots lines and style: block)
  seeded  docs/ (never touched)
  layer   .aix/org/, .aix/custom/: replaced when the origin (or --from-org / --from-custom SRC) has the folder, else left
  Unlisted, therefore never touched: .aix/skills/extern downloads, runtime folders, code.
  1.x layout  a root framework.yaml: kit-owned folders are moved under .aix/ first (migrate_layout)
Runs from the KIT's scripts (not the project's), so it always carries the newest logic."""
import filecmp, re, shutil, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import payload
MERGED_FILES = payload.merged_paths(KIT)
PROJECT_KEYS = ("disabled_skills", "instructions", "disabled_instructions", "profile", "use", "source", "source_org", "source_custom", "agents", "agents_total", "agents_lease", "policy", "style")  # config.yaml lines the project owns
OLD_LAYOUT = {"scripts": ".aix/scripts", "templates": ".aix/templates", "skills": ".aix/skills", "docs/meta-docs": ".aix/meta-docs",
              "framework.yaml": ".aix/config.yaml"}
OLD_TEXT = [("docs/meta-docs/", ".aix/meta-docs/"), ("`skills/INDEX.md`", "`.aix/skills/INDEX.md`"), ("`skills/`", "`.aix/skills/`"),
            ("| `meta-docs/` |", "| `../.aix/meta-docs/` |"), ("`meta-docs/INDEX.md`", "`.aix/meta-docs/INDEX.md`"),
            ("`meta-docs/conventions/", "`.aix/meta-docs/conventions/"), ("framework.yaml", ".aix/config.yaml")]
KEEP_SECTIONS = ("## Always-on skills", "## Project notes")


def version_of(root: Path) -> str:
    m = re.search(r"^version:\s*([^\s#]+)", (root / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "?"


def diff_dir(src: Path, dst: Path):
    """Return (added, updated, removed) file lists comparing kit dir `src` with project dir `dst`."""
    added, updated, removed = [], [], []
    src_files = {p.relative_to(src) for p in src.rglob("*") if p.is_file() and payload.is_payload_file(p.relative_to(src))}
    dst_files = {p.relative_to(dst) for p in dst.rglob("*") if p.is_file() and payload.is_payload_file(p.relative_to(dst))} if dst.exists() else set()
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
    sys.path.insert(0, str(KIT / ".aix" / "scripts"))
    import agents as agmod
    chosen = agmod.selected(project)
    for d in payload.owned_paths(KIT, chosen):
        src, dst = KIT / d, project / d
        if src.is_dir():
            a, u, r = diff_dir(src, dst)
            rows += [(d, "add", x) for x in a] + [(d, "update", x) for x in u] + [(d, "remove", x) for x in r]
        elif src.exists() and (not dst.exists() or not filecmp.cmp(src, dst, shallow=False)):
            rows.append((".", "update" if dst.exists() else "add", Path(d)))
    for f in payload.merged_paths(KIT, chosen):
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
    if name in ("CLAUDE.md", "GEMINI.md"):  # pointer files: the template inside .aix/, a layer's copy winning
        import install_skills as inst
        agent = payload.AGENT_OF[name]
        kit_text = inst.pointer_text(project, name, inst.POINTERS[agent][1])
    else:
        kit_text = (KIT / name).read_text(encoding="utf-8")
    proj_text = (project / name).read_text(encoding="utf-8") if (project / name).exists() else ""
    if name in ("AGENTS.md", "GEMINI.md", "CLAUDE.md"):
        out = kit_text
        for h in KEEP_SECTIONS:
            keep = section(proj_text, h)
            if keep and h not in out:
                out = out.rstrip("\n") + "\n\n" + keep
        return out
    out = kit_text  # config.yaml: kit text, but the project's disabled_skills line and style: block win
    proj_text = proj_text.replace("aix/stacks/", "aix/frameworks/")  # 2.8.3 renamed the kit's framework standards
    for key in PROJECT_KEYS:  # a key and, for maps such as use: and style:, its indented body
        pat = rf"^{key}:.*\n(?:[ \t]+\S.*\n?)*"
        m = re.search(pat, proj_text, re.M)
        if m:
            block = m.group(0) if m.group(0).endswith("\n") else m.group(0) + "\n"
            out = re.sub(pat, lambda _: block, out, count=1, flags=re.M) if re.search(rf"^{key}:", out, re.M) else out.rstrip("\n") + "\n" + block
    m = re.search(r"^[ \t]+code_roots:.*$", proj_text, re.M)  # nested under paths:, set by `aix code find`
    if m:
        out = re.sub(r"^[ \t]+code_roots:.*$", lambda _: m.group(0), out, count=1, flags=re.M)
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
    warn = "  !! LOCAL EDIT WILL BE LOST (move the change to the kit)" if shown in edited else ""
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
            keep = ", keeping your disabled_skills, instructions, profile, use, source and style limits"
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
    global KIT
    yes, dry = "--yes" in args, "--dry-run" in args
    args = [a for a in args if a not in ("--yes", "--dry-run")]
    layer_src = {}
    for layer in ("org", "custom"):
        flag = f"--from-{layer}"
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                sys.exit(f"aix upgrade {flag} SOURCE needs a source")
            layer_src[layer] = args[i + 1]; del args[i:i + 2]
    from project import find_project
    project = Path(args[0]).resolve() if args else find_project(Path.cwd())
    if project is None or not ((project / ".aix" / "config.yaml").exists() or (project / "framework.yaml").exists()):
        sys.exit("aix upgrade: no project found (nearest .aix/config.yaml, or a 1.x framework.yaml); pass the project path")
    import source as srcmod
    src = srcmod.configured(project)
    origin = KIT
    if src:
        kind, payload_root, bare = srcmod.classify(srcmod.fetch(src, refresh=not dry))
        if kind == "kit":
            KIT = origin = payload_root
        else:
            layer_src.setdefault("org", None)
            layer_src["org"] = layer_src["org"] or src
        print(f"  origin: {src} ({kind})")
    srcmod.install_layers(project, srcmod.resolve_layers(origin, srcmod.layer_sources(project, layer_src), refresh=not dry), dry=dry)
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
        print("  already up to date")
        if not dry:
            import gitignore
            gitignore.ask_and_apply(project, yes=yes, label="aix upgrade")
        return
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
    import gitignore
    gitignore.ask_and_apply(project, yes=yes, label="aix upgrade")  # after the files, so the agents line is final
    print(f"  applied {len(rows)} changes; relinking skills in the project")
    subprocess.call([sys.executable, str(project / ".aix" / "scripts" / "aix.py"), "install"], cwd=project, stdout=subprocess.DEVNULL)
    print("  done. Run `aix doctor` and `aix docs validate` in the project.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:])
