"""Leaf over payload: what `aix install --into` lays down in a project. The kit payload copied item by item with the
collision dialogue (replace / skip / merge, `.bak` kept), the seeded docs/ overlaid layer by layer, and the pointer
files' text (templates/pointers/, a layer's copy winning)."""
import shutil, sys
from pathlib import Path

import payload

KIT_ROOT = Path(__file__).resolve().parents[2]


POINTERS = {  # agent -> (file, text) for the agents that do not read AGENTS.md by themselves
    "claude": ("CLAUDE.md", "Read and follow `AGENTS.md` at the repository root. It is the single source of agent instructions for this project. Skills are available under `.claude/skills/` (installed from `.aix/skills/` by `aix install`).\n"),
    "copilot": (".github/copilot-instructions.md", "Read and follow `AGENTS.md` at the repository root before doing anything.\n"),
    "cursor": (".cursor/rules/aix.mdc", "---\ndescription: AIX agent contract\nalwaysApply: true\n---\nRead and follow `AGENTS.md` at the repository root before doing anything. Skills are in `.cursor/skills/`.\n"),
    "gemini": ("GEMINI.md", "Read and follow `AGENTS.md` at the repository root. It is the single source of agent instructions for this project. Skills are available under `.agents/skills/` (installed from `.aix/skills/` by `aix install`).\n"),
}


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


def seed_sources(project: Path, name: str) -> list:
    """The template folders for a seeded item, lowest layer first: the kit's .aix/templates/<name>, then org/, then custom/."""
    import layers
    out = []
    for layer, root in layers.layer_roots(project):
        if layer == "user":
            continue
        d = root / "templates" / name
        if d.is_dir():
            out.append((layer, d))
    return out


def _copy_tree_over(src: Path, dst_root: Path):
    for f in sorted(src.rglob("*")):
        if f.is_file() and payload.is_payload_file(f.relative_to(src)):
            dst = dst_root / f.relative_to(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, dst)


def seed_project(project: Path, kit: Path = KIT_ROOT) -> list:
    """Lay down the seeded payload items that are absent (docs/): kit template overlaid by the layers, file by file."""
    done = []
    for item, mode in payload.items(kit):
        if mode != payload.SEEDED or (project / item).exists():
            continue
        sources = seed_sources(project, Path(payload.source_of(item)).name)
        for _layer, d in sources:
            _copy_tree_over(d, project / item)
        if sources:
            done.append((item, [l for l, _ in sources]))
            print(f"  seeded: {item} ({' < '.join(l for l, _ in sources)})")
    return done


def pointer_text(project: Path, name: str, fallback: str) -> str:
    """The pointer file's text: the highest layer's templates/pointers/<name>, else the kit's, else the built-in."""
    text = fallback
    for _layer, d in seed_sources(project, "pointers"):
        f = d / name
        if f.is_file():
            text = f.read_text(encoding="utf-8")
    return text


def copy_item(src: Path, dst: Path):
    """Copy one payload item (file or folder) without the ignored parts (__pycache__, *.pyc)."""
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*payload.IGNORED_PARTS, *("*" + s for s in payload.IGNORED_SUFFIXES)))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)


def _apply_choice(item: str, src: Path, dst: Path, choice: str):
    if choice == "abort":
        sys.exit("aborted; items already added above were left in place")
    if choice == "skip" or (choice == "merge" and not src.is_dir()):
        print(f"  skipped: {item}" + ("" if choice == "skip" else " (files cannot be merged)"))
    elif choice == "merge":
        print(f"  merged: {item} (+{merge_dir(src, dst)} files, nothing overwritten)")
    else:
        replace_item(src, dst)
        print(f"  replaced: {item} (old kept as {item}.bak)")


def copy_kit_into(project: Path, on_collision: str = "ask", kit: Path = KIT_ROOT):
    """Copy payload.items() of `kit` into project. on_collision: ask | replace | skip | merge."""
    project.mkdir(parents=True, exist_ok=True)
    remembered = {} if on_collision == "ask" else {"all": on_collision}
    for item, mode in payload.items(kit):
        src, dst = kit / payload.source_of(item), project / item
        if not src.exists() or mode == payload.SEEDED or item in payload.AGENT_OF:
            continue  # seeded items (docs/) and pointer files are laid down once the layers are in place (seed_project, _pointer_files)
        if dst.exists():
            _apply_choice(item, src, dst, ask_collision(item, src.is_dir(), remembered))
            continue
        copy_item(src, dst)
        if item == ".aix/config.yaml":
            dst.write_text(payload.clean_config(dst.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"  added: {item}")
    if (project / "AGENTS.md").exists() and on_collision != "replace":
        print("NOTE: if the project already had agent instructions, merge them into AGENTS.md section 5.")
