#!/usr/bin/env python3
"""aix doctor — installation health (not document content; that is `aix docs validate`).
Each finding comes with the fix. Exit 1 if anything is broken."""
import json, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_skills as inst
import catalog as sk
from extern import ALWAYS_FILES, always_on_names

problems = []


def problem(what, fix):
    problems.append((what, fix))


def check_python():
    if sys.version_info < (3, 9):
        problem(f"Python {sys.version.split()[0]} is too old", "install Python 3.9 or newer")


def check_path():
    if os.name != "nt" and not shutil.which("aix"):
        problem("`aix` is not on PATH", "run `aix self-install` from the kit clone (link + shell profile), then open a new terminal")


def check_pointers():
    import agents
    chosen = agents.selected(ROOT)
    print(f"agents: {', '.join(chosen)}" + ("" if agents.configured(ROOT) else " (all: no agents: line; `aix agents` chooses)"))
    for rel in agents.pointer_files(ROOT):
        f = ROOT / rel
        if not f.exists() or "AGENTS.md" not in f.read_text(encoding="utf-8"):
            problem(f"{rel} missing or not pointing at AGENTS.md", "run `aix install`")
    for n, a in agents.AGENTS.items():
        if n in chosen:
            continue
        left = [rel for rel in a["pointers"] if agents.is_aix_pointer(ROOT / rel)] + ([a["skills"]] if a["skills"] and (ROOT / a["skills"]).is_dir() else [])
        if left:
            problem(f"{n} is not selected but AIX files remain: {', '.join(left)}", "run `aix agents` (removes them) or select it")


def check_links():
    import agents
    agents_dirs = agents.skill_dirs(ROOT)
    cat, off = sk.catalogue(), sk.disabled()
    for flat, info in cat.items():
        if flat in off:
            continue
        missing = [t for t in agents_dirs if not (ROOT / t / flat / "SKILL.md").exists()]
        if missing:
            problem(f"skill {flat} not linked in {', '.join(missing)}", "run `aix install`")
    for t in agents_dirs:
        d = ROOT / t
        for p in d.iterdir() if d.is_dir() else []:
            if p.is_symlink() and not p.exists():
                problem(f"dangling link {p.relative_to(ROOT)}", "run `aix install` (prunes it)")
    for name in off - set(cat):
        problem(f"disabled_skills names unknown skill {name}", "edit .aix/config.yaml")


def check_always_on():
    per_file = {f.relative_to(ROOT): set(always_on_names(f.read_text(encoding="utf-8"))) for f in ALWAYS_FILES if f.exists()}
    union = set().union(*per_file.values()) if per_file else set()
    for f, names in per_file.items():
        for n in union - names:
            problem(f"{n} always-on in other files but not in {f}", f"run `aix skills always {n}`")
    for n in union:
        if n not in sk.catalogue():
            problem(f"always-on skill {n} is not installed", f"run `aix skills add {n}` or `aix skills on-demand {n}`")


def check_extern():
    ext = ROOT / ".aix" / "skills" / "extern"
    for d in ext.iterdir() if ext.is_dir() else []:
        if d.is_dir() and (d / "SKILL.md").exists() and not (d / ".aix-source").exists():
            problem(f".aix/skills/extern/{d.name} has no .aix-source (cannot `aix skills update` it)", "re-add it with `aix skills add`")


def check_state():
    state = ROOT / "docs" / "road-map" / "going-on" / "STATE.md"
    if not state.exists():
        return problem("docs/road-map/going-on/STATE.md missing", "run `aix install`")
    m = re.search(r"^active_task:\s*(TASK-\d+)", state.read_text(encoding="utf-8"), re.M)
    if m and not list((ROOT / "docs" / "road-map" / "going-on").glob(f"{m.group(1)}*.md")):
        problem(f"STATE.md names {m.group(1)} but it is not in going-on/", f"`aix task start {m.group(1)}` or set active_task: none")


def check_kit_edits():
    """Kit-owned files edited in this project: silently overwritten by the next `aix upgrade`."""
    if (ROOT / "AIX-DEVELOPMENT.md").exists():
        return  # the kit checkout itself
    edited = inst.modified_kit_files(ROOT)
    if edited is None:
        return problem(".aix/manifest.json missing (cannot detect local edits of kit files)", "run `aix install`")
    for f in edited:
        problem(f"{f} was edited locally; the next `aix upgrade` overwrites it", "make the change in the kit repository (or a skill under .aix/skills/extern), then `aix upgrade`")


def check_layers():
    """Overrides are fine; a linked implementation whose content changed since `aix install` is not (the index lies)."""
    import layers
    changed = layers.drift(ROOT)
    if changed is None:
        return problem(".aix/index.json missing (which implementation is active is unknown)", "run `aix install`")
    for cls in changed:
        problem(f"skill {cls}: linked content changed since the last install (index hash differs)", "run `aix install` to re-index (and review who changed it)")
    idx = layers.read_index(ROOT)
    if idx.get("profile"):
        print(f"profile: {idx['profile']}")
    ins = idx.get("instructions", {})
    if ins:
        blocks = sorted(k for k, v in ins.items() if (v["block"] if "block" in v else not (v.get("applyTo") or v.get("always"))))
        scoped = sorted(k for k in ins if k not in blocks)
        print(f"instructions: {len(blocks)} AGENTS.md blocks ({', '.join(blocks)})")
        if scoped:
            print(f"instructions: {len(scoped)} scoped ({', '.join(scoped)})")
    new = {}
    for kind, name, layer, path, near in layers.orphans(ROOT):
        shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if near:
            problem(f"{kind} {name} ({layer} layer, {shown}) overrides nothing; did you mean {near}?", f"rename it to {near} (a class or id must match character by character to replace the kit's)")
        else:
            new.setdefault((kind, layer), []).append(name)
    for (kind, layer), names in sorted(new.items()):
        print(f"note: {len(names)} new {kind}{'s' if len(names) > 1 else ''} from the {layer} layer (override nothing in the kit): {', '.join(names)}")
    over = [f"{c} ({r['layer']})" for c, r in idx["skills"].items() if r["layer"] != "kit" or r.get("chosen_by", "").startswith("config")]
    if over or idx["disabled"]:
        print("layers: " + (", ".join(over) if over else "no overrides") + (";  disabled by layers: " + ", ".join(idx["disabled"]) if idx["disabled"] else "")
              + ("" if idx.get("user_layer") else "  (user layer not applied: no terminal / AIX_NO_USER)"))


def check_agents_blocks():
    """AGENTS.md is assembled from .aix/instructions blocks; a hand edit outside the managed sections is lost on install."""
    import layers, tempfile, shutil
    blocks = [v for v in layers.instructions(ROOT, layers.active_profile(ROOT)).values() if v["block"]]
    if not blocks or not (ROOT / "AGENTS.md").exists():
        return
    expected_ids = {b["id"] if "id" in b else None for b in blocks}
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for b in sorted(blocks, key=lambda v: v["order"]):
        if b["section"] and f"## {b['section']}" not in text:
            problem(f"AGENTS.md lacks the block section '{b['section']}' ({b['layer']} layer)", "run `aix install` (AGENTS.md is assembled from .aix/instructions blocks)")
    for line in text.splitlines():
        if line.startswith("## ") and line.strip() not in inst_headers(blocks):
            problem(f"AGENTS.md has a section not produced by any block or managed by aix: '{line.strip()}'", "move its text into a block under .aix/custom/instructions/ (block: true, section, order) and run `aix install`")


def inst_headers(blocks):
    return {f"## {b['section']}" for b in blocks if b["section"]} | set(inst.MANAGED)


def main():
    for check in (check_python, check_path, check_pointers, check_links, check_always_on, check_extern, check_state, check_kit_edits, check_layers, check_agents_blocks):
        check()
    for what, fix in problems:
        print(f"PROBLEM {what}\n        fix: {fix}")
    print(f"{len(problems)} problems" if problems else "installation healthy")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
