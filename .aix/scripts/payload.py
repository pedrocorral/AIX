#!/usr/bin/env python3
"""Leaf: THE list of what the kit puts into a project. `aix install`, `aix upgrade`, the kit-file manifest and `aix doctor`
all read it; nothing else decides what travels. Anything not listed here never leaves the kit checkout (tests/, examples/,
AIX-DEVELOPMENT.md, CHANGELOG.md, .aix/custom/, .aix/org/, .aix/index.json, .aix/manifest.json, caches).

Three modes:
  owned   copied on install; on upgrade overwritten, and removed when gone from the kit; hashed in .aix/manifest.json
          so `aix doctor` can report a local edit before an upgrade loses it
  merged  copied on install; on upgrade rebuilt from the kit text plus the project's own parts (managed sections of
          AGENTS.md / GEMINI.md, the project's keys in .aix/config.yaml)
  seeded  copied on install when absent, from a template inside .aix/ (`.aix/templates/docs` -> `docs/`) overlaid by the
          layers' `templates/docs/`; never touched by upgrade (the project's documentation)
  layer   .aix/org/ and .aix/custom/: copied on install when the origin has the folder, replaced on upgrade when the
          origin has it, left alone when it does not. The origin is the kit checkout that runs, unless `--from-org SRC`
          / `--from-custom SRC` (recorded as source_org / source_custom in config.yaml) point one of them elsewhere."""
from pathlib import Path

OWNED, MERGED, SEEDED, LAYER = "owned", "merged", "seeded", "layer"
LAYERS = ("org", "custom")
IGNORED_PARTS = {"__pycache__"}   # never payload, whatever folder they sit in
IGNORED_SUFFIXES = {".pyc"}


AGENT_OF = {"CLAUDE.md": "claude", "GEMINI.md": "gemini"}   # pointer files that travel only when their agent is selected
SEED_SOURCE = {"docs": ".aix/templates/docs", "CLAUDE.md": ".aix/templates/pointers/CLAUDE.md", "GEMINI.md": ".aix/templates/pointers/GEMINI.md"}
# seeded items and pointer files come from inside .aix/ so a layer (org/, custom/) can overlay them; the pointer files are
# written by install (templates/pointers/, a layer's copy winning) and merged on upgrade, never copied from the kit root


def source_of(rel: str) -> str:
    """Where a payload item is read from in the kit: itself, except seeded items whose template lives under .aix/."""
    return SEED_SOURCE.get(rel, rel)


def items(kit: Path, agents: list = None):
    """[(path relative to the kit root, mode)] in install order. Skill categories are read from the kit, extern excepted:
    its registry is kit text, the downloads next to it belong to the project. With `agents`, pointer files of
    unselected agents are left out."""
    skills = kit / ".aix" / "skills"
    categories = sorted(p.name for p in skills.iterdir() if p.is_dir() and p.name != "extern") if skills.is_dir() else []
    out = ([(".aix/config.yaml", MERGED), (".aix/bin", OWNED), (".aix/scripts", OWNED), (".aix/templates", OWNED),
             (".aix/meta-docs", OWNED), (".aix/instructions", OWNED), (".aix/profiles", OWNED), (".aix/policies", OWNED),
             (".aix/skills/INDEX.md", OWNED), (".aix/skills/extern/registry.json", OWNED)]
            + [(f".aix/skills/{c}", OWNED) for c in categories]
            + [("AGENTS.md", MERGED), ("CLAUDE.md", MERGED), ("GEMINI.md", MERGED), ("docs", SEEDED)]
            + [(f".aix/{l}", LAYER) for l in LAYERS])
    if agents is not None:
        out = [(rel, m) for rel, m in out if AGENT_OF.get(rel, None) in (None, *agents)]
    return out


PROJECT_KEYS = ("disabled_skills", "instructions", "disabled_instructions", "profile", "use", "source", "source_org", "source_custom",
                "agents", "agents_total", "agents_lease", "policy", "style", "licenses_allow", "licenses_known")   # config.yaml lines a project owns (kept by upgrade)


def clean_config(text: str) -> str:
    """The kit's config.yaml without the kit's own project choices (its policy, profile, agents, pins): what a fresh
    project starts from. `style:` stays, it is the kit's default limits."""
    import re
    for key in PROJECT_KEYS:
        if key == "style":
            continue
        text = re.sub(rf"^{key}:.*\n(?:[ \t]+\S.*\n?)*", "", text, flags=re.M)
    return text


def is_payload_file(path: Path) -> bool:
    return not (IGNORED_PARTS & set(path.parts)) and path.suffix not in IGNORED_SUFFIXES


def _files_under(root: Path, rel: str):
    for f in sorted((root / rel).rglob("*")):
        if f.is_file() and is_payload_file(f.relative_to(root)):
            yield f.relative_to(root)


def files(root: Path, mode: str = OWNED, agents: list = None):
    """Every payload file of the given mode under `root` (a kit checkout or an installed project), as (relative path)."""
    for rel, m in items(root, agents):
        p = root / rel
        if m != mode or not p.exists():
            continue
        if p.is_file():
            yield Path(rel)
        elif m != SEEDED:
            yield from _files_under(root, rel)


def owned_paths(kit: Path, agents: list = None):
    return [rel for rel, m in items(kit, agents) if m == OWNED]


def merged_paths(kit: Path, agents: list = None):
    return [rel for rel, m in items(kit, agents) if m == MERGED]
# edit
