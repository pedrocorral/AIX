#!/usr/bin/env python3
"""aix doctor — installation health (not document content; that is `aix docs validate`).
Each finding comes with the fix. Exit 1 if anything is broken."""
import os, re, shutil, sys
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


def _leftovers_of(agents, a: dict) -> list:
    left = [rel for rel in a["pointers"] if agents.is_aix_pointer(ROOT / rel)]
    if a["skills"] and (ROOT / a["skills"]).is_dir():
        left.append(a["skills"])
    return left


def check_pointers():
    import agents
    chosen = agents.selected(ROOT)
    print(f"agents: {', '.join(chosen)}" + ("" if agents.configured(ROOT) else " (all: no agents: line; `aix agents` chooses)"))
    for rel in agents.pointer_files(ROOT):
        f = ROOT / rel
        if not f.exists() or "AGENTS.md" not in f.read_text(encoding="utf-8"):
            problem(f"{rel} missing or not pointing at AGENTS.md", "run `aix install`")
    for n, a in agents.AGENTS.items():
        left = [] if n in chosen else _leftovers_of(agents, a)
        if left:
            problem(f"{n} is not selected but AIX files remain: {', '.join(left)}", "run `aix agents` (removes them) or select it")


def _dangling(agents_dirs):
    for t in agents_dirs:
        d = ROOT / t
        for p in (d.iterdir() if d.is_dir() else []):
            if p.is_symlink() and not p.exists():
                yield p


def check_links():
    import agents
    agents_dirs = agents.skill_dirs(ROOT)
    cat, off = sk.catalogue(), sk.disabled()
    for flat in (f for f in cat if f not in off):
        missing = [t for t in agents_dirs if not (ROOT / t / flat / "SKILL.md").exists()]
        if missing:
            problem(f"skill {flat} not linked in {', '.join(missing)}", "run `aix install`")
    for p in _dangling(agents_dirs):
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


def _report_instructions(ins: dict):
    blocks = sorted(k for k, v in ins.items() if (v["block"] if "block" in v else not (v.get("applyTo") or v.get("always"))))
    scoped = sorted(k for k in ins if k not in blocks)
    print(f"instructions: {len(blocks)} AGENTS.md blocks ({', '.join(blocks)})")
    if scoped:
        print(f"instructions: {len(scoped)} scoped ({', '.join(scoped)})")


def _report_orphans(layers):
    typos, additions = layers.orphan_report(ROOT)
    for kind, name, layer, shown, near in typos:
        problem(f"{kind} {name} ({layer} layer, {shown}) overrides nothing; did you mean {near}?", f"rename it to {near} (a class or id must match character by character to replace the kit's)")
    for (kind, layer), names in sorted(additions.items()):
        print("note: " + layers.additions_line(kind, layer, names))


def _report_overrides(idx: dict):
    over = [f"{c} ({r['layer']})" for c, r in idx["skills"].items() if r["layer"] != "kit" or r.get("chosen_by", "").startswith("config")]
    if not over and not idx["disabled"]:
        return
    disabled = ";  disabled by layers: " + ", ".join(idx["disabled"]) if idx["disabled"] else ""
    user = "" if idx.get("user_layer") else "  (user layer not applied: no terminal / AIX_NO_USER)"
    print("layers: " + (", ".join(over) if over else "no overrides") + disabled + user)


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
    if idx.get("instructions"):
        _report_instructions(idx["instructions"])
    _report_orphans(layers)
    _report_overrides(idx)


def _owner_of(task_file) -> str:
    import re
    m = re.search(r"^owner:\s*(agent-\d+)", task_file.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def _report_stale_seats(seats):
    for name, s in seats.stale(ROOT):
        problem(f"seat {name} is {s['state']}: {s.get('tool')} {s.get('user')}@{s.get('host')} left without `aix agent release`",
                "the next `aix agent claim` takes it over (a seat expired on another machine needs --force)")


def _report_orphan_tasks(going, all_seats: dict):
    for f in sorted(going.glob("TASK-*.md")):
        owner = _owner_of(f)
        holder = all_seats.get(owner) if owner else None
        if owner and (holder is None or holder["state"] not in ("live", "remote")):
            problem(f"{f.name[:9]} is going-on but its owner {owner} is not a live seat", "`aix task start` it from a live session (--force if held), or `aix task block` it")


def check_seats():
    """Seats nobody is sitting on any more, and going-on tasks whose owner is not a live seat."""
    import seats
    going = ROOT / "docs" / "road-map" / "going-on"
    if not going.is_dir():
        return
    all_ = seats.all_seats(ROOT)
    _report_stale_seats(seats)
    _report_orphan_tasks(going, all_)
    if seats.total(ROOT) > 1:
        taken = sum(1 for s in all_.values() if s)
        live = sum(1 for s in all_.values() if s and s["state"] == "live")
        print(f"seats: {seats.total(ROOT)} total, {taken} taken, {live} live here")


def _missing_block_sections(blocks, text: str):
    for b in sorted(blocks, key=lambda v: v["order"]):
        if b["section"] and f"## {b['section']}" not in text:
            problem(f"AGENTS.md lacks the block section '{b['section']}' ({b['layer']} layer)", "run `aix install` (AGENTS.md is assembled from .aix/instructions blocks)")


def check_agents_blocks():
    """AGENTS.md is assembled from .aix/instructions blocks; a hand edit outside the managed sections is lost on install."""
    import layers
    blocks = [v for v in layers.instructions(ROOT, layers.active_profile(ROOT)).values() if v["block"]]
    if not blocks or not (ROOT / "AGENTS.md").exists():
        return
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    _missing_block_sections(blocks, text)
    known = inst_headers(blocks)
    for line in text.splitlines():
        if line.startswith("## ") and line.strip() not in known:
            problem(f"AGENTS.md has a section not produced by any block or managed by aix: '{line.strip()}'", "move its text into a block under .aix/custom/instructions/ (block: true, section, order) and run `aix install`")


def inst_headers(blocks):
    return {f"## {b['section']}" for b in blocks if b["section"]} | set(inst.MANAGED)


def main():
    for check in (check_python, check_path, check_pointers, check_links, check_always_on, check_extern, check_state, check_kit_edits, check_layers, check_seats, check_agents_blocks):
        check()
    for what, fix in problems:
        print(f"PROBLEM {what}\n        fix: {fix}")
    print(f"{len(problems)} problems" if problems else "installation healthy")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
