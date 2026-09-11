#!/usr/bin/env python3
"""Leaf: resolve which implementation of every skill class is active, across the customisation layers.

Layers, later wins (AIX-DEVELOPMENT.md §11-12):
  kit       <project>/.aix/skills           what the kit ships (plus skills/extern, project-owned, bare names)
  org       <project>/.aix/org/skills       the organisation's custom/, vendored (later slice: `aix install --from`)
  user      ~/.config/aix/skills            the person; uncommitted places only; skipped without a terminal, in CI, or with AIX_NO_USER=1; forced on with AIX_USER=1
  project   <project>/.aix/custom/skills    this project, committed with it
A folder at the same class path replaces; a new path adds; an empty `DISABLED` file in a class folder removes.
The runtime always links one folder per class under the class name."""
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_DIR = Path(os.environ.get("AIX_USER_DIR") or (Path.home() / ".config" / "aix"))
LAYER_NAMES = ("kit", "org", "user", "project")


def user_layer_enabled() -> bool:
    """Personal overrides apply to a person's session only: never in CI, never when asked not to."""
    if os.environ.get("AIX_NO_USER") == "1":
        return False
    if os.environ.get("AIX_USER") == "1":
        return True  # a script that wants the personal layer on purpose
    return not os.environ.get("CI") and sys.stdin.isatty()


def layer_dirs(project: Path = ROOT):
    dirs = [("kit", project / ".aix" / "skills"), ("org", project / ".aix" / "org" / "skills")]
    if user_layer_enabled():
        dirs.append(("user", USER_DIR / "skills"))
    dirs.append(("project", project / ".aix" / "custom" / "skills"))
    return [(name, d) for name, d in dirs if d.is_dir()]


def class_name(rel_parts) -> str:
    """skills/<cat>/<name> -> cat-name; skills/extern/<name> -> name (third-party skills keep their own name)."""
    return "-".join(rel_parts[1:]) if rel_parts[0] == "extern" else "-".join(rel_parts)


def content_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(f.relative_to(folder).as_posix().encode()); h.update(b"\0"); h.update(f.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def front_matter_value(md: Path, key: str) -> str:
    for line in md.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def resolve(project: Path = ROOT):
    """class -> {path, layer, shadowed: [(layer, path)...], disabled_by}. Later layers override earlier ones."""
    active, disabled = {}, {}
    for layer, base in layer_dirs(project):
        for marker in base.rglob("DISABLED"):
            cls = class_name(marker.parent.relative_to(base).parts)
            disabled[cls] = layer
            active.pop(cls, None)
        for md in sorted(base.rglob("SKILL.md")):
            cls = class_name(md.parent.relative_to(base).parts)
            if cls in disabled and disabled[cls] != layer:
                continue
            disabled.pop(cls, None)
            prev = active.get(cls)
            active[cls] = {"path": md.parent, "layer": layer,
                           "shadowed": ([(prev["layer"], prev["path"])] + prev["shadowed"]) if prev else []}
    return active, disabled


def index_entries(project: Path = ROOT):
    active, disabled = resolve(project)
    out = {}
    for cls, info in sorted(active.items()):
        md = info["path"] / "SKILL.md"
        out[cls] = {"layer": info["layer"], "path": str(info["path"]), "id": front_matter_value(md, "id") or cls,
                    "version": front_matter_value(md, "version"), "hash": content_hash(info["path"]),
                    "shadowed": [{"layer": l, "path": str(p)} for l, p in info["shadowed"]]}
    return out, {cls: layer for cls, layer in disabled.items()}


def write_index(project: Path = ROOT):
    entries, disabled = index_entries(project)
    (project / ".aix" / "index.json").write_text(json.dumps({"skills": entries, "disabled": disabled, "user_layer": user_layer_enabled()}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return entries, disabled


def read_index(project: Path = ROOT):
    f = project / ".aix" / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def drift(project: Path = ROOT):
    """Classes whose linked implementation changed since `aix install` wrote the index (content hash differs)."""
    idx = read_index(project)
    if idx is None:
        return None
    out = []
    for cls, rec in idx["skills"].items():
        p = Path(rec["path"])
        if p.is_dir() and content_hash(p) != rec["hash"]:
            out.append(cls)
    return out


if __name__ == "__main__":
    entries, disabled = index_entries()
    for cls, rec in entries.items():
        mark = "" if rec["layer"] == "kit" else f"  <- {rec['layer']} override" + (f" of {rec['shadowed'][0]['layer']}" if rec["shadowed"] else " (new)")
        print(f"{cls:40s} {rec['layer']:8s} {rec['hash'][:12]}{mark}")
    for cls, layer in disabled.items():
        print(f"{cls:40s} DISABLED by {layer}")
