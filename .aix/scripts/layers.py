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
import hashlib, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_DIR = Path(os.environ.get("AIX_USER_DIR") or (Path.home() / ".config" / "aix"))
LAYER_NAMES = ("kit", "org", "user", "project")


# ---- tiny YAML subset (no dependency): scalars, lists, one-level maps, `key: |` blocks --------------------------------

def parse_yaml(text: str) -> dict:
    out, key, mode, buf = {}, None, None, []
    for raw in text.splitlines():
        if mode == "block":
            if not raw.strip() or raw.startswith(("  ", "\t")):
                buf.append(raw[2:] if raw.startswith("  ") else raw[1:]); continue
            out[key] = "\n".join(buf).rstrip() + "\n"; mode, buf = None, []
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  - "):
            if not isinstance(out.get(key), list):
                out[key] = []
            out[key].append(_scalar(raw[4:])); continue
        if raw.startswith(("  ", "\t")) and ":" in raw:
            k, v = raw.strip().split(":", 1)
            if not isinstance(out.get(key), dict):
                out[key] = {}
            out[key][k.strip()] = _scalar(v); continue
        if ":" in raw:
            key, v = raw.split(":", 1)
            key, v = key.strip(), _strip_comment(v)
            if v == "|":
                mode = "block"
            elif v == "":
                out[key] = None
            elif v.startswith("[") and v.endswith("]"):
                out[key] = [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
            else:
                out[key] = _scalar(v)
    if mode == "block":
        out[key] = "\n".join(buf).rstrip() + "\n"
    return out


def _strip_comment(v: str) -> str:
    v = v.strip()
    if v and v[0] in "\"'":
        end = v.find(v[0], 1)
        return v[:end + 1] if end > 0 else v
    return v.split("#", 1)[0].strip()


def _scalar(v: str):
    v = _strip_comment(v)
    if v and v[0] in "\"'" and v[-1] == v[0] and len(v) > 1:
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return v


def front_matter(md: Path) -> dict:
    text = md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    return parse_yaml(text[3:end]) if end > 0 else {}


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


def resolve(project: Path = ROOT, profile: dict = None):
    """class -> {path, layer, id, version, manual, shadowed, chosen_by}; plus disabled {class: layer}."""
    found, disabled = implementations(project)
    cfg = config(project)
    use = dict(cfg.get("use") or {})
    if profile and isinstance(profile.get("skills"), dict):
        use = {**{flat(k): v for k, v in profile["skills"].items()}, **{flat(k): v for k, v in use.items()}}
    else:
        use = {flat(k): v for k, v in use.items()}
    active = {}
    for cls, impls in found.items():
        if cls in disabled:
            top = max(LAYER_NAMES.index(i["layer"]) for i in impls)
            if LAYER_NAMES.index(disabled[cls]) >= top:
                continue  # DISABLED in the highest layer that mentions the class
        chosen, why = None, ""
        if cls in use:
            chosen = next((i for i in impls if i["id"] == use[cls]), None)
            why = f"config use: {use[cls]}" if chosen else ""
        if chosen is None:
            top_layer = max(impls, key=lambda i: LAYER_NAMES.index(i["layer"]))["layer"]
            top = [i for i in impls if i["layer"] == top_layer]
            chosen = next((i for i in top if i["canonical"]), top[0])
            why = f"{top_layer} layer" + (" override" if top_layer != "kit" and len(impls) > 1 else "")
        others = [i for i in impls if i is not chosen]
        active[cls] = {**chosen, "chosen_by": why, "shadowed": [(i["layer"], i["path"], i["id"]) for i in others]}
    return active, {c: l for c, l in disabled.items() if c not in active}


# ---- instructions -------------------------------------------------------------------------------------------------

def instructions(project: Path = ROOT, profile: dict = None):
    """id -> {path, layer, description, applyTo: [globs], always}. Later layer wins per id. No user layer."""
    out = {}
    for layer, root in layer_roots(project):
        if layer == "user":
            continue
        base = root / "instructions"
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            fm = front_matter(md)
            if not fm.get("id"):
                continue
            globs = fm.get("applyTo", "")
            globs = [g.strip() for g in (globs if isinstance(globs, list) else str(globs).split(",")) if g.strip()]
            out[fm["id"]] = {"path": md, "layer": layer, "name": fm.get("name", fm["id"]), "description": fm.get("description", ""),
                             "applyTo": globs, "always": fm.get("always") is True,
                             "block": fm.get("block") is True, "section": str(fm.get("section", "")), "order": int(fm.get("order", 100) or 100),
                             "optional": fm.get("optional") is True}
    cfg = config(project)
    wanted = set(cfg.get("instructions") or [])
    off = set(cfg.get("disabled_instructions") or [])
    if profile and isinstance(profile.get("instructions"), list):
        wanted |= set(profile["instructions"])
        out = {k: v for k, v in out.items() if k in wanted or v["layer"] == "kit"}
    return {k: v for k, v in out.items() if (not v["optional"] or k in wanted) and k not in off}


def all_instructions(project: Path = ROOT):
    """Every instruction any layer offers, with its state: active | optional (off) | disabled | not in profile."""
    prof = active_profile(project)
    active = instructions(project, prof)
    cfg = config(project)
    off = set(cfg.get("disabled_instructions") or [])
    everything = {}
    for layer, root in layer_roots(project):
        if layer == "user":
            continue
        base = root / "instructions"
        for md in (sorted(base.rglob("*.md")) if base.is_dir() else []):
            fm = front_matter(md)
            if fm.get("id"):
                everything[fm["id"]] = {"path": md, "layer": layer, "description": fm.get("description", ""),
                                        "applyTo": fm.get("applyTo", ""), "block": fm.get("block") is True, "optional": fm.get("optional") is True,
                                        "section": str(fm.get("section", ""))}
    for iid, v in everything.items():
        v["state"] = "active" if iid in active else "disabled" if iid in off else "optional (off)" if v["optional"] else "not in profile"
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
            "instructions": {k: {"layer": v["layer"], "path": str(v["path"]), "applyTo": v["applyTo"], "always": v["always"]} for k, v in ins.items()},
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
