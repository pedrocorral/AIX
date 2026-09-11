#!/usr/bin/env python3
"""Leaf: resolve where a project's kit comes from (`aix install --from`, `source:` in config.yaml).

A source is a path or a git URL. It is either a KIT CHECKOUT (has `.aix/`): its `.aix/` is the payload and its
`.aix/custom/` is the organisation layer; or a bare LAYER FOLDER (has `skills/`, `instructions/`, `profiles/` or
`templates/` at its top): the payload comes from the running kit and the folder is the organisation layer.
Git URLs are cloned shallow into ~/.cache/aix/sources/<slug> and refreshed with `git pull` on upgrade."""
import os, re, subprocess
from pathlib import Path

CACHE = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix" / "sources"))
LAYER_DIRS = ("skills", "instructions", "profiles", "templates", "meta-docs")


def is_git_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "git@", "ssh://", "git://")) or s.endswith(".git")


def fetch(source: str, refresh: bool = False) -> Path:
    """Return a local folder for the source; clone or pull git URLs."""
    if not is_git_url(source):
        p = Path(source).expanduser().resolve()
        if not p.is_dir():
            raise SystemExit(f"aix: source {source} is not a folder")
        return p
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", source.split("://")[-1]).strip("-")
    dest = CACHE / slug
    if dest.is_dir():
        if refresh:
            subprocess.run(["git", "-C", str(dest), "pull", "-q", "--ff-only"], check=False)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", source, str(dest)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"aix: cannot clone {source}: {r.stderr.strip()}")
    return dest


def classify(folder: Path):
    """('kit', payload_root, org_layer_or_None) | ('layer', None, folder)"""
    if (folder / ".aix" / "config.yaml").exists():
        custom = folder / ".aix" / "custom"
        return "kit", folder, (custom if custom.is_dir() and any(custom.iterdir()) else None)
    if any((folder / d).is_dir() for d in LAYER_DIRS) or (folder / "AGENTS.md").exists():
        return "layer", None, folder
    raise SystemExit(f"aix: {folder} is neither a kit checkout (.aix/) nor a customisation layer (skills/, instructions/, profiles/, templates/)")


def record(project: Path, source: str):
    cfg = project / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    line = f"source: {source}   # organisation layer origin (aix install --from); refreshed by aix upgrade"
    text = re.sub(r"^source:.*$", line, text, count=1, flags=re.M) if re.search(r"^source:", text, re.M) else text.rstrip("\n") + "\n" + line + "\n"
    cfg.write_text(text, encoding="utf-8")


def configured(project: Path):
    m = re.search(r"^source:\s*(\S+)", (project / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M) if (project / ".aix" / "config.yaml").exists() else None
    return m.group(1) if m else None


def install_org(project: Path, layer: Path):
    """Replace the project's .aix/org/ with the organisation layer (kit-owned from the project's point of view)."""
    import shutil
    dst = project / ".aix" / "org"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(layer, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dst
