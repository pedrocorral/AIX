"""Leaf: .aix/manifest.json, the sha256 of every kit-owned file in a project, so doctor and upgrade can tell a
local edit (lost on the next upgrade) from kit text."""
from pathlib import Path

import payload


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
