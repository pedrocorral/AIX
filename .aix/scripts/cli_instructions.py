"""`aix instructions` (alias `aix rules`): list, info, show, enable, disable; a switch is remembered in config.yaml
and applied at once."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


INSTRUCTIONS_USAGE = "usage: aix instructions [list] | info ID | show ID | enable ID | disable ID"


def _instructions_list(allins):
    import shutil
    width = shutil.get_terminal_size((100, 20)).columns
    print(f"{'INSTRUCTION':36s} {'STATE':14s} DESCRIPTION")
    for iid, v in sorted(allins.items(), key=lambda kv: (kv[1]["block"], kv[0])):
        print(f"{iid:36s} {v['state']:14s} {v['description'][:max(10, width - 52)]}")
    active = sum(1 for v in allins.values() if v["state"] == "active")
    print(f"\n{active} of {len(allins)} instructions active. optional (off) = enable with aix instructions enable ID or a profile; "
          "disabled = switched off here. Details (layer, kind, path): aix instructions info ID")


def _instruction_info(iid, v):
    shown = v["path"].relative_to(ROOT) if v["path"].is_relative_to(ROOT) else v["path"]
    kind = "block (AGENTS.md section " + repr(v["section"]) + ")" if v["block"] else ("scoped to " + str(v["applyTo"]) if v["applyTo"] else "always")
    print(f"{iid}\n  state:       {v['state']}\n  layer:       {v['layer']}\n  kind:        {kind}"
          f"\n  optional:    {v['optional']}\n  path:        {shown}\n  description: {v['description']}")


def _edit_config_list(text: str, key: str, add, remove) -> str:
    """Add or remove one item of a `key: [a, b]` line in config text; the line is created when missing."""
    import re
    m = re.search(rf"^{key}:\s*\[(.*?)\]", text, re.M)
    items = [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []
    items = [x for x in items if x != remove] + ([add] if add and add not in items else [])
    line = f"{key}: [" + ", ".join(items) + "]"
    if m:
        return re.sub(rf"^{key}:.*$", line, text, count=1, flags=re.M)
    return text.rstrip("\n") + "\n" + line + "   # managed by `aix instructions enable|disable`\n"


def _instruction_switch(sub: str, iid: str, v):
    cfg = ROOT / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    if sub == "enable":
        text = _edit_config_list(text, "disabled_instructions", None, iid)
        if v["optional"]:
            text = _edit_config_list(text, "instructions", iid, None)
    else:
        text = _edit_config_list(text, "disabled_instructions", iid, None)
        text = _edit_config_list(text, "instructions", None, iid)
    cfg.write_text(text, encoding="utf-8")
    print(f"{iid}: {sub}d; applying")
    return True   # aix.py re-applies the installation


def run_instructions(args):
    """aix instructions [list] | info ID | show ID | enable ID | disable ID"""
    import layers
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    allins = layers.all_instructions(ROOT)
    if sub == "list":
        return _instructions_list(allins)
    if sub not in ("show", "info", "enable", "disable") or not rest:
        sys.exit(INSTRUCTIONS_USAGE)
    iid = rest[0]
    if iid not in allins:
        sys.exit(f"unknown instruction '{iid}' (aix instructions)")
    v = allins[iid]
    if sub == "show":
        print(v["path"].read_text(encoding="utf-8"))
    elif sub == "info":
        _instruction_info(iid, v)
    else:
        return _instruction_switch(sub, iid, v)
