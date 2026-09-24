#!/usr/bin/env python3
"""Leaf: resolve where a project's kit comes from (`aix install --from`, `source:` in config.yaml).

A source is a path or a git URL. `--from SRC` names the ORIGIN: a kit checkout (has `.aix/`) whose `.aix/` is the
payload and whose `.aix/org/` and `.aix/custom/` are the layers; or a bare LAYER FOLDER (has `skills/`,
`instructions/`, `profiles/` or `templates/` at its top), taken as the org layer with the payload from the running kit.
`--from-org SRC` / `--from-custom SRC` point one layer elsewhere (a kit checkout's `.aix/<layer>/` or a bare folder).
Both layers follow one rule: copied on install when the source has the folder, replaced on upgrade when it has it,
left alone when it does not. Sources are recorded in config.yaml (`source:`, `source_org:`, `source_custom:`).
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


def is_kit(folder: Path) -> bool:
    return (folder / ".aix" / "config.yaml").exists()


def is_layer(folder: Path) -> bool:
    return any((folder / d).is_dir() for d in LAYER_DIRS) or (folder / "AGENTS.md").exists()


def classify(folder: Path):
    """('kit', payload_root, org_layer_or_None) | ('layer', None, folder)"""
    if is_kit(folder):
        return "kit", folder, filled(folder / ".aix" / "org")
    if is_layer(folder):
        return "layer", None, folder
    raise SystemExit(f"aix: {folder} is neither a kit checkout (.aix/) nor a customisation layer (skills/, instructions/, profiles/, templates/)")


def filled(folder: Path):
    """The folder when it holds at least one file, else None."""
    return folder if folder.is_dir() and any(p.is_file() for p in folder.rglob("*")) else None


def layer_folder(src_folder: Path, layer: str):
    """Where a source keeps the given layer: <kit>/.aix/<layer>/ for a kit checkout, the folder itself when bare."""
    return filled(src_folder / ".aix" / layer) if is_kit(src_folder) else filled(src_folder)


def resolve_layers(origin_kit: Path, sources: dict, refresh: bool = False):
    """{layer: (source label or None, folder or None)} for org and custom: an explicit source per layer wins, else the
    origin's own .aix/<layer>/. A bare --from layer folder counts as the org source."""
    out = {}
    for layer in ("org", "custom"):
        src = sources.get(layer)
        if src:
            out[layer] = (src, layer_folder(fetch(src, refresh), layer))
        else:
            out[layer] = (None, filled(origin_kit / ".aix" / layer))
    return out


def install_layers(project: Path, resolved: dict, dry: bool = False):
    """Apply resolve_layers(): replace each layer the source has; say what happened."""
    for layer, (src, folder) in resolved.items():
        if folder is None:
            continue
        if not dry:
            install_layer(project, layer, folder)
        print(f"  layer {layer}: {'from ' + src if src else 'from the origin'} -> .aix/{layer}/" + (" (dry run)" if dry else ""))


def record(project: Path, source: str, key: str = "source"):
    """Write `source:` (the origin, --from), `source_org:` or `source_custom:` (--from-org / --from-custom) into config.yaml."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import layers
    if Path(source).expanduser().exists():
        source = str(Path(source).expanduser().resolve())  # a relative path would break `aix upgrade` run from elsewhere
    what = {"source": "origin of the kit and its layers (aix install --from)", "source_org": "where .aix/org/ comes from (--from-org)",
            "source_custom": "where .aix/custom/ comes from (--from-custom)"}[key]
    layers.set_key(project, key, source, f"{what}; followed by aix upgrade")


def configured(project: Path, key: str = "source"):
    cfg = project / ".aix" / "config.yaml"
    m = re.search(rf"^{key}:\s*(\S+)", cfg.read_text(encoding="utf-8"), re.M) if cfg.exists() else None
    return m.group(1) if m else None


def layer_sources(project: Path, overrides: dict = None):
    """{layer: source} from --from-org / --from-custom (recorded) or config.yaml source_org / source_custom."""
    out = {}
    for layer in ("org", "custom"):
        src = (overrides or {}).get(layer)
        if src:
            record(project, src, f"source_{layer}")
        out[layer] = src or configured(project, f"source_{layer}")
    return out


def install_layer(project: Path, layer: str, folder: Path):
    """Replace the project's .aix/<layer>/ with the source's folder."""
    import shutil
    dst = project / ".aix" / layer
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(folder, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return dst
