#!/usr/bin/env python3
"""Leaf: THE list of what the kit puts into a project. `aix install`, `aix upgrade`, the kit-file manifest and `aix doctor`
all read it; nothing else decides what travels. Anything not listed here never leaves the kit checkout (tests/, examples/,
AIX-DEVELOPMENT.md, CHANGELOG.md, .aix/custom/, .aix/org/, .aix/index.json, .aix/manifest.json, caches).

Three modes:
  owned   copied on install; on upgrade overwritten, and removed when gone from the kit; hashed in .aix/manifest.json
          so `aix doctor` can report a local edit before an upgrade loses it
  merged  copied on install; on upgrade rebuilt from the kit text plus the project's own parts (managed sections of
          AGENTS.md / GEMINI.md, the project's keys in .aix/config.yaml)
  seeded  copied on install when absent; never touched by upgrade (the project's documentation)
  layer   .aix/org/ and .aix/custom/: copied on install when the origin has the folder, replaced on upgrade when the
          origin has it, left alone when it does not. The origin is the kit checkout that runs, unless `--from-org SRC`
          / `--from-custom SRC` (recorded as source_org / source_custom in config.yaml) point one of them elsewhere."""
from pathlib import Path

OWNED, MERGED, SEEDED, LAYER = "owned", "merged", "seeded", "layer"
LAYERS = ("org", "custom")
IGNORED_PARTS = {"__pycache__"}   # never payload, whatever folder they sit in
IGNORED_SUFFIXES = {".pyc"}


AGENT_OF = {"CLAUDE.md": "claude", "GEMINI.md": "gemini"}   # pointer files that travel only when their agent is selected


def items(kit: Path, agents: list = None):
    """[(path relative to the kit root, mode)] in install order. Skill categories are read from the kit, extern excepted:
    its registry is kit text, the downloads next to it belong to the project. With `agents`, pointer files of
    unselected agents are left out."""
    skills = kit / ".aix" / "skills"
    categories = sorted(p.name for p in skills.iterdir() if p.is_dir() and p.name != "extern") if skills.is_dir() else []
    out = ([(".aix/config.yaml", MERGED), (".aix/bin", OWNED), (".aix/scripts", OWNED), (".aix/templates", OWNED),
             (".aix/meta-docs", OWNED), (".aix/instructions", OWNED), (".aix/profiles", OWNED),
             (".aix/skills/INDEX.md", OWNED), (".aix/skills/extern/registry.json", OWNED)]
            + [(f".aix/skills/{c}", OWNED) for c in categories]
            + [("AGENTS.md", MERGED), ("CLAUDE.md", OWNED), ("GEMINI.md", MERGED), ("docs", SEEDED)]
            + [(f".aix/{l}", LAYER) for l in LAYERS])
    if agents is not None:
        out = [(rel, m) for rel, m in out if AGENT_OF.get(rel, None) in (None, *agents)]
    return out


def is_payload_file(path: Path) -> bool:
    return not (IGNORED_PARTS & set(path.parts)) and path.suffix not in IGNORED_SUFFIXES


def files(root: Path, mode: str = OWNED, agents: list = None):
    """Every payload file of the given mode under `root` (a kit checkout or an installed project), as (relative path)."""
    for rel, m in items(root, agents):
        if m != mode:
            continue
        p = root / rel
        if p.is_file():
            yield Path(rel)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and is_payload_file(f.relative_to(root)):
                    yield f.relative_to(root)


def owned_paths(kit: Path, agents: list = None):
    return [rel for rel, m in items(kit, agents) if m == OWNED]


def merged_paths(kit: Path, agents: list = None):
    return [rel for rel, m in items(kit, agents) if m == MERGED]
# edit
