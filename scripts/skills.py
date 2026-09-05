#!/usr/bin/env python3
"""Skill catalogue and enable/disable management for `aix skills`.

Activation levels (derived, not configured):
  always       named in AGENTS.md, so every session runs or may need them (resume, workflow, handoff, conflicts)
  orchestrator entry-point skills that chain other skills
  on-demand    invoked by an orchestrator, the user, or the agent when the description matches
Disabled skills are listed in framework.yaml under `disabled_skills:` and are not linked by `aix install`."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "framework.yaml"
AGENTS = ROOT / "AGENTS.md"
TARGETS = [".opencode/skills", ".claude/skills", ".github/skills", ".agents/skills", ".cursor/skills"]
RUNTIME = {".opencode/skills": "opencode", ".claude/skills": "claude", ".github/skills": "copilot",
           ".agents/skills": "agents", ".cursor/skills": "cursor"}


def front_matter(text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def registry_groups():
    import json
    reg = SKILLS / "extern" / "registry.json"
    if not reg.exists():
        return {}
    return {k: v.get("group", "specific") for k, v in json.loads(reg.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def skill_group(md: Path, text: str, flat: str, reg: dict) -> str:
    """general = behaviour for every session; specific = one job. Front-matter `group:` wins, then .aix-source, then registry."""
    import json
    g = front_matter(text, "group")
    if not g and (md.parent / ".aix-source").exists():
        g = json.loads((md.parent / ".aix-source").read_text(encoding="utf-8")).get("group", "")
    return g or reg.get(flat, "specific")


def catalogue():
    """All leaf skills: dict flat-name -> {path, category, group, description, orchestrator}."""
    out, reg = {}, registry_groups()
    for md in sorted(SKILLS.rglob("SKILL.md")):
        rel = md.parent.relative_to(SKILLS)
        text = md.read_text(encoding="utf-8")
        flat = "-".join(rel.parts[1:]) if rel.parts[0] == "extern" else "-".join(rel.parts)
        out[flat] = {
            "path": md.parent, "category": rel.parts[0],
            "group": skill_group(md, text, flat, reg),
            "description": front_matter(text, "description"),
            "orchestrator": "orchestrator" in text.lower()[:600],
        }
    return out


def always_on():
    """Skills AGENTS.md names explicitly: the agent contract requires them regardless of the request."""
    return set(re.findall(r"`([a-z][a-z0-9-]+)`", AGENTS.read_text(encoding="utf-8")))


def disabled():
    m = re.search(r"^disabled_skills:\s*\[(.*?)\]", MANIFEST.read_text(encoding="utf-8"), re.M)
    return {s.strip() for s in m.group(1).split(",") if s.strip()} if m else set()


def set_disabled(names):
    line = "disabled_skills: [" + ", ".join(sorted(names)) + "]   # managed by `aix skills enable|disable`"
    text = MANIFEST.read_text(encoding="utf-8")
    if re.search(r"^disabled_skills:", text, re.M):
        text = re.sub(r"^disabled_skills:.*$", line, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    MANIFEST.write_text(text, encoding="utf-8")


def installed_in(flat: str):
    return [RUNTIME[t] for t in TARGETS if (ROOT / t / flat).exists()]


def level(flat, info, always):
    return "always" if flat in always else "orchestrator" if info["orchestrator"] else "on-demand"


def state_of(flat, always, off):
    return "disabled" if flat in off else "always" if flat in always else "on-demand"


def available_from_registry(cat):
    """Registry skills not yet downloaded, so they show up in the list with state `available`."""
    import json
    reg = SKILLS / "extern" / "registry.json"
    if not reg.exists():
        return {}
    entries = json.loads(reg.read_text(encoding="utf-8"))
    return {n: {"category": "extern", "group": e.get("group", "specific"), "description": e["description"],
                "available": "recommended" if e.get("recommended") else "available"}
            for n, e in entries.items() if not n.startswith("_") and n not in cat}


def cmd_list(group=None, category=None):
    import shutil
    cat, always, off = catalogue(), always_on(), disabled()
    avail = available_from_registry(cat)
    order = sorted(avail, key=lambda n: avail[n]["available"] != "recommended") + list(cat)  # recommended, available, rest
    cat = dict(cat, **avail)
    width = shutil.get_terminal_size((100, 20)).columns
    head = f"{'SKILL':42s} {'STATE':11s} "
    room = width - len(head)
    print(head + ("DESCRIPTION" if room > 20 else ""))
    n = 0
    for flat in order:
        info = cat[flat]
        if (group and info["group"] != group) or (category and info["category"] != category):
            continue
        n += 1
        state = info.get("available") or state_of(flat, always, off)
        line = f"{flat:42s} {state:11s} "
        if state == "always":  # marker starts two columns early, overwriting the end of the name if needed
            line = f"{line[:39]}{'(*) always':16s}"
        print(line + (info["description"][:room] if room > 20 else ""))
    print(f"\n{n} of {len(cat)} skills. (*) always = applied in every session; recommended / available = known, "
          "not downloaded (aix skills add NAME). Details: aix skills info NAME")


def cmd_info(flat):
    cat, always, off = catalogue(), always_on(), disabled()
    if flat not in cat and flat in available_from_registry(cat):
        import extern
        return extern.cmd_registry(only=flat)
    info = cat.get(flat) or sys.exit(f"unknown skill '{flat}' (see `aix skills list`)")
    src = info["path"] / ".aix-source"
    print(f"{flat}\n  state:       {state_of(flat, always, off)}\n  group:       {info['group']}"
          f"\n  level:       {level(flat, info, always)}\n  category:    {info['category']}"
          f"\n  installed:   {', '.join(installed_in(flat)) or '-'}\n  path:        {info['path'].relative_to(ROOT)}")
    if src.exists():
        print(f"  source:      {src.read_text(encoding='utf-8').strip()}")
    print(f"  description: {info['description']}")


def cmd_show(flat):
    info = catalogue().get(flat) or sys.exit(f"unknown skill '{flat}' (see `aix skills list`)")
    print((info["path"] / "SKILL.md").read_text(encoding="utf-8"))


def unlink_everywhere(flat):
    import shutil
    for t in TARGETS:
        p = ROOT / t / flat
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)


def cmd_disable(flat):
    cat = catalogue()
    if flat not in cat:
        sys.exit(f"unknown skill '{flat}'")
    if flat in always_on():
        print(f"warning: AGENTS.md names {flat}; agents will look for it every session")
    set_disabled(disabled() | {flat}); unlink_everywhere(flat)
    print(f"disabled {flat} (unlinked from all runtimes, recorded in framework.yaml)")


def cmd_enable(flat):
    import install_skills as inst
    cat = catalogue()
    if flat not in cat:
        sys.exit(f"unknown skill '{flat}'")
    set_disabled(disabled() - {flat})
    for t in TARGETS:
        inst.link_or_copy(cat[flat]["path"], ROOT / t / flat, copy=False)
    print(f"enabled {flat} (linked into all runtimes)")


GROUPS = ("general", "specific")


def split_filters(rest):
    """Pull group (general|specific) and category words out of a filter list."""
    group = next((r for r in rest if r in GROUPS), None)
    category = next((r for r in rest if r not in GROUPS), None)
    return group, category


def main(args):
    sub, rest = (args[0], list(args[1:])) if args else ("list", [])
    categories = {d.name for d in SKILLS.iterdir() if d.is_dir()}
    if sub in GROUPS or sub in categories:
        sub, rest = "list", [sub] + rest
    if sub == "list":
        cmd_list(*split_filters(rest))
    elif sub == "show" and rest:
        cmd_show(rest[0])
    elif sub == "info" and rest:
        cmd_info(rest[0])
    elif sub == "disable" and rest:
        for f in rest: cmd_disable(f)
    elif sub == "enable" and rest:
        for f in rest: cmd_enable(f)
    elif sub == "registry":
        import extern
        extern.cmd_registry(split_filters(rest)[0])
    elif sub in ("add", "remove", "update", "always", "on-demand"):
        import extern
        extern.main(args)
    else:
        sys.exit("usage: aix skills [list|general|specific [category] | info NAME | show NAME | enable|disable NAME... | registry | add NAME [--always] | remove NAME | update | always|on-demand NAME]")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1:])
