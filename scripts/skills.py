#!/usr/bin/env python3
"""`aix skills` commands. Data lives in catalog.py (leaf); third-party operations in extern.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import (ROOT, SKILLS, catalogue, always_on, disabled, set_disabled, installed_in, unlink_everywhere)
import install_skills as inst


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


def cmd_disable(flat):
    cat = catalogue()
    if flat not in cat:
        sys.exit(f"unknown skill '{flat}'")
    if flat in always_on():
        print(f"warning: AGENTS.md names {flat}; agents will look for it every session")
    set_disabled(disabled() | {flat}); unlink_everywhere(flat)
    print(f"disabled {flat} (unlinked from all runtimes, recorded in framework.yaml)")


def cmd_enable(flat):
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
