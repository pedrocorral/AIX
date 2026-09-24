#!/usr/bin/env python3
"""Leaf: resolve skills, scoped instructions and profiles across the customisation layers.

Layers, later wins (AIX-DEVELOPMENT.md §11-12):
  kit       <project>/.aix/{skills,instructions,profiles}
  org       <project>/.aix/org/...          the organisation's custom/, vendored (`aix install --from`)
  user      ~/.config/aix/skills            the person; SKILLS ONLY (instructions would end up committed); skipped
                                            without a terminal, in CI, or with AIX_NO_USER=1; forced with AIX_USER=1
  project   <project>/.aix/custom/...       this project, committed with it

Skills: a folder is an implementation of a CLASS. The class is `class:` in its front matter (e.g. `testing/write-unit-tests`)
or, when absent, its path. Its `name:` must equal the class flat name (the runtimes link by it); `id:`/`version:`
name the implementation. Same class in a higher layer replaces; a new class adds; an empty `DISABLED` file removes.
Several implementations of one class may coexist; `config.yaml`  use: {class: id}  or a profile picks one; otherwise
the highest layer wins, and inside a layer the canonical path (the class path) wins.
Instructions: `instructions/**/*.md` with front matter `id`, `description`; either SCOPED (`applyTo` globs, `always`)
and rendered per runtime, or a BLOCK (`block: true`, `section`, `order`) assembled into AGENTS.md itself. The kit's
own AGENTS.md is the blocks under `.aix/instructions/agents/`; a layer replaces a block by id or adds a section.
Profiles: `profiles/<name>.yaml` = a saved set of choices (instructions, skills, always-on, router)."""
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_DIR = Path(os.environ.get("AIX_USER_DIR") or (Path.home() / ".config" / "aix"))
LAYER_NAMES = ("kit", "org", "user", "project")
from yamlmini import front_matter, parse_yaml



# ---- layers -------------------------------------------------------------------------------------------------------

def user_layer_enabled() -> bool:
    if os.environ.get("AIX_NO_USER") == "1":
        return False
    if os.environ.get("AIX_USER") == "1":
        return True
    return not os.environ.get("CI") and sys.stdin.isatty()


def layer_roots(project: Path = ROOT):
    """(layer, root folder holding skills/, instructions/, profiles/, templates/)"""
    roots = [("kit", project / ".aix"), ("org", project / ".aix" / "org")]
    if user_layer_enabled():
        roots.append(("user", USER_DIR))
    roots.append(("project", project / ".aix" / "custom"))
    return [(n, r) for n, r in roots if r.is_dir()]


def config(project: Path = ROOT) -> dict:
    f = project / ".aix" / "config.yaml"
    return parse_yaml(f.read_text(encoding="utf-8")) if f.exists() else {}


def set_key(project: Path, key: str, value, comment: str = ""):
    """Write one top-level `key: value` line into .aix/config.yaml (replacing the line when present); value None
    removes the line. The one writer every `aix ... use|set` command goes through."""
    import re
    cfg = project / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    line = "" if value is None else f"{key}: {value}" + (f"   # {comment}" if comment else "")
    if re.search(rf"^{key}:.*$", text, re.M):
        text = re.sub(rf"^{key}:.*\n?", (line + "\n") if line else "", text, count=1, flags=re.M)
    elif line:
        text = text.rstrip("\n") + "\n" + line + "\n"
    cfg.write_text(text, encoding="utf-8")


def class_of_path(rel_parts) -> str:
    return "-".join(rel_parts[1:]) if rel_parts[0] == "extern" else "-".join(rel_parts)


def flat(cls: str) -> str:
    """'testing/write-unit-tests' -> 'testing-write-unit-tests'; 'extern/ponytail' -> 'ponytail'."""
    parts = cls.split("/")
    return class_of_path(parts) if len(parts) > 1 else cls


def content_hash(folder: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(f.relative_to(folder).as_posix().encode()); h.update(b"\0"); h.update(f.read_bytes()); h.update(b"\0")
    return h.hexdigest()


# ---- skills -------------------------------------------------------------------------------------------------------

def implementations(project: Path = ROOT):
    """class -> [impl, ...] in layer order; impl = {path, layer, id, version, manual, canonical, fm}."""
    found, disabled = {}, {}
    for layer, root in layer_roots(project):
        base = root / "skills"
        if not base.is_dir():
            continue
        for marker in base.rglob("DISABLED"):
            cls = class_of_path(marker.parent.relative_to(base).parts)
            disabled[cls] = layer
        for md in sorted(base.rglob("SKILL.md")):
            fm = front_matter(md)
            rel = md.parent.relative_to(base).parts
            cls = flat(fm["class"]) if fm.get("class") else class_of_path(rel)
            found.setdefault(cls, []).append({
                "path": md.parent, "layer": layer, "id": fm.get("id") or cls, "version": fm.get("version", ""),
                "manual": fm.get("disable-model-invocation") is True, "canonical": class_of_path(rel) == cls, "fm": fm})
    return found, disabled


def _use_map(cfg: dict, profile: dict) -> dict:
    """class -> implementation id: the config's `use:` over the profile's `skills:`."""
    use = {flat(k): v for k, v in (cfg.get("use") or {}).items()}
    if profile and isinstance(profile.get("skills"), dict):
        return {**{flat(k): v for k, v in profile["skills"].items()}, **use}
    return use


def _disabled_on_top(cls: str, impls: list, disabled: dict) -> bool:
    """A DISABLED file wins only when it sits in the highest layer that mentions the class."""
    if cls not in disabled:
        return False
    top = max(LAYER_NAMES.index(i["layer"]) for i in impls)
    return LAYER_NAMES.index(disabled[cls]) >= top


def _top_layer_choice(impls: list):
    """The canonical implementation of the highest layer, and the reason."""
    top_layer = max(impls, key=lambda i: LAYER_NAMES.index(i["layer"]))["layer"]
    top = [i for i in impls if i["layer"] == top_layer]
    chosen = next((i for i in top if i["canonical"]), top[0])
    override = " override" if top_layer != "kit" and len(impls) > 1 else ""
    return chosen, f"{top_layer} layer{override}"


def _choose(cls: str, impls: list, use: dict):
    """(implementation, why): the pinned id when it exists, else the canonical one of the highest layer."""
    pinned = next((i for i in impls if i["id"] == use.get(cls)), None) if cls in use else None
    if pinned:
        return pinned, f"config use: {use[cls]}"
    return _top_layer_choice(impls)


def resolve(project: Path = ROOT, profile: dict = None):
    """class -> {path, layer, id, version, manual, shadowed, chosen_by}; plus disabled {class: layer}."""
    found, disabled = implementations(project)
    use = _use_map(config(project), profile)
    active = {}
    for cls, impls in found.items():
        if _disabled_on_top(cls, impls, disabled):
            continue
        chosen, why = _choose(cls, impls, use)
        others = [i for i in impls if i is not chosen]
        active[cls] = {**chosen, "chosen_by": why, "shadowed": [(i["layer"], i["path"], i["id"]) for i in others]}
    return active, {c: l for c, l in disabled.items() if c not in active}


# ---- instructions -------------------------------------------------------------------------------------------------

def _instruction_files(project: Path):
    """(layer, path, front matter) for every instruction file of every layer but the user's, kit first."""
    for layer, root in layer_roots(project):
        base = root / "instructions"
        if layer == "user" or not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            fm = front_matter(md)
            if fm.get("id"):
                yield layer, md, fm


def _instruction_record(layer: str, md: Path, fm: dict) -> dict:
    globs = fm.get("applyTo", "")
    globs = [g.strip() for g in (globs if isinstance(globs, list) else str(globs).split(",")) if g.strip()]
    return {"path": md, "layer": layer, "name": fm.get("name", fm["id"]), "description": fm.get("description", ""),
            "applyTo": globs, "always": fm.get("always") is True, "block": fm.get("block") is True,
            "section": str(fm.get("section", "")), "order": int(fm.get("order", 100) or 100), "optional": fm.get("optional") is True}


def _wanted_instructions(cfg: dict, profile) -> set:
    wanted = set(cfg.get("instructions") or [])
    if profile and isinstance(profile.get("instructions"), list):
        wanted |= set(profile["instructions"])
    return wanted


def _keep_instruction(record: dict, key: str, wanted: set, off: set, listed: bool) -> bool:
    """Optional instructions need to be wanted; a profile that lists instructions keeps only those and the kit's."""
    if key in off or (record["optional"] and key not in wanted):
        return False
    return not listed or key in wanted or record["layer"] == "kit"


def instructions(project: Path = ROOT, profile: dict = None):
    """id -> {path, layer, description, applyTo: [globs], always}. Later layer wins per id. No user layer."""
    out = {fm["id"]: _instruction_record(layer, md, fm) for layer, md, fm in _instruction_files(project)}
    cfg = config(project)
    wanted = _wanted_instructions(cfg, profile)
    off = set(cfg.get("disabled_instructions") or [])
    listed = bool(profile) and isinstance(profile.get("instructions"), list)
    return {k: v for k, v in out.items() if _keep_instruction(v, k, wanted, off, listed)}


def _instruction_state(iid: str, v: dict, active: dict, off: set) -> str:
    if iid in active:
        return "active"
    if iid in off:
        return "disabled"
    return "optional (off)" if v["optional"] else "not in profile"


def all_instructions(project: Path = ROOT):
    """Every instruction any layer offers, with its state: active | optional (off) | disabled | not in profile."""
    active = instructions(project, active_profile(project))
    off = set(config(project).get("disabled_instructions") or [])
    everything = {}
    for layer, md, fm in _instruction_files(project):
        everything[fm["id"]] = {"path": md, "layer": layer, "description": fm.get("description", ""), "applyTo": fm.get("applyTo", ""),
                                "block": fm.get("block") is True, "optional": fm.get("optional") is True, "section": str(fm.get("section", ""))}
    for iid, v in everything.items():
        v["state"] = _instruction_state(iid, v, active, off)
    return everything


# ---- profiles -----------------------------------------------------------------------------------------------------

def profiles(project: Path = ROOT):
    out = {}
    for layer, root in layer_roots(project):
        if layer == "user":
            continue
        for f in sorted((root / "profiles").glob("*.yaml")) if (root / "profiles").is_dir() else []:
            data = parse_yaml(f.read_text(encoding="utf-8"))
            out[f.stem] = {**data, "layer": layer, "path": f}
    return out


def active_profile(project: Path = ROOT):
    name = config(project).get("profile")
    return profiles(project).get(name) if name else None


# ---- index ------------------------------------------------------------------------------------------------------------

def write_index(project: Path = ROOT):
    prof = active_profile(project)
    active, disabled = resolve(project, prof)
    ins = instructions(project, prof)
    entries = {cls: {"layer": i["layer"], "path": str(i["path"]), "id": i["id"], "version": i["version"], "manual": i["manual"],
                     "chosen_by": i["chosen_by"], "hash": content_hash(i["path"]),
                     "shadowed": [{"layer": l, "path": str(p), "id": d} for l, p, d in i["shadowed"]]} for cls, i in sorted(active.items())}
    data = {"skills": entries, "disabled": disabled, "user_layer": user_layer_enabled(),
            "instructions": {k: {"layer": v["layer"], "path": str(v["path"]), "applyTo": v["applyTo"], "always": v["always"], "block": v["block"]} for k, v in ins.items()},
            "profile": config(project).get("profile") or ""}
    (project / ".aix" / "index.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return active, disabled, ins


def read_index(project: Path = ROOT):
    f = project / ".aix" / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def drift(project: Path = ROOT):
    idx = read_index(project)
    if idx is None:
        return None
    return [cls for cls, rec in idx["skills"].items() if Path(rec["path"]).is_dir() and content_hash(Path(rec["path"])) != rec["hash"]]


if __name__ == "__main__":
    active, disabled = resolve()
    for cls, i in sorted(active.items()):
        print(f"{cls:40s} {i['layer']:8s} {i['id']:34s} {i['chosen_by']}")
    for cls, l in disabled.items():
        print(f"{cls:40s} DISABLED by {l}")
    for k, v in instructions().items():
        print(f"instruction {k:36s} {v['layer']:8s} always={v['always']} applyTo={','.join(v['applyTo'])}")


# ---- orphans: layer files that override nothing ---------------------------------------------------------------------

def _orphan_skills(project: Path, cutoff: float) -> list:
    found, _ = implementations(project)
    kit_classes = sorted(c for c, impls in found.items() if any(i["layer"] == "kit" for i in impls))
    out = []
    for cls, impls in sorted(found.items()):
        if cls in kit_classes:
            continue
        near = near_miss(cls, kit_classes, "-", cutoff)
        out += [("skill", cls, i["layer"], i["path"], near) for i in impls]
    return out


def _orphan_instructions(project: Path, cutoff: float) -> list:
    kit_ids, layer_ids = set(), []
    for layer, root in layer_roots(project):
        base = root / "instructions"
        for md in (sorted(base.rglob("*.md")) if base.is_dir() else []):
            iid = front_matter(md).get("id")
            if not iid:
                continue
            (kit_ids.add(iid) if layer == "kit" else layer_ids.append((iid, layer, md)))
    return [("instruction", iid, layer, md, near_miss(iid, sorted(kit_ids), "/", cutoff)) for iid, layer, md in layer_ids if iid not in kit_ids]


def orphans(project: Path = ROOT, cutoff: float = 0.85) -> list:
    """Skills and instructions in org/ or custom/ (or the user layer) that match nothing in the kit: a genuine addition,
    or a typo one character away from a kit name. [(kind, name, layer, path, suggestion|None)]; `suggestion` is the
    closest kit name when it is close enough (difflib ratio >= cutoff) — almost always a typo."""
    return _orphan_skills(project, cutoff) + _orphan_instructions(project, cutoff)


def orphan_report(project: Path = ROOT):
    """(typos, additions): typos = [(kind, name, layer, shown path, suggestion)], additions = {(kind, layer): [names]}.
    Doctor turns typos into problems and additions into a note; validate into errors and a warning."""
    typos, additions = [], {}
    for kind, name, layer, path, near in orphans(project):
        shown = path.relative_to(project) if path.is_relative_to(project) else path
        if near:
            typos.append((kind, name, layer, shown, near))
        else:
            additions.setdefault((kind, layer), []).append(name)
    return typos, additions


def additions_line(kind: str, layer: str, names: list) -> str:
    return f"{len(names)} new {kind}{'s' if len(names) > 1 else ''} from the {layer} layer (override nothing in the kit): {', '.join(names)}"


def near_miss(name: str, known: list, sep: str, cutoff: float = 0.85):
    """The known name `name` is probably a typo of: same first segment (category, owner), remainder within the
    difflib cutoff and at least 4 characters long. `implement-tdd` is not a typo of `implement-ui`; `coach-grill_me`
    is one of `coach-grill-me`; `acme/x` is never a typo of `aix/y`."""
    import difflib
    head, _, rest = name.partition(sep)
    if not rest or len(rest) < 4:
        return None
    candidates = {k.partition(sep)[2]: k for k in known if k.partition(sep)[0] == head and k.partition(sep)[2]}
    hit = difflib.get_close_matches(rest, list(candidates), n=1, cutoff=cutoff)
    return candidates[hit[0]] if hit else None
