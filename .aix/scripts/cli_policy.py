"""`aix policy` (the development cycle; anarchy = none), `aix check` (run its checks) and `aix profile` (a saved
set of choices from a layer)."""
import sys
from pathlib import Path

from cli_install import cmd_install

ROOT = Path(__file__).resolve().parents[2]


def _policy_list(pol, pols, name, source):
    mark = "*" if name == pol.ANARCHY else " "
    print(f"{mark} {pol.ANARCHY:12s} {'-':8s} no cycle: nothing checked, nobody stopped (also: none, nothing, freedom)")
    for n, pp in pols.items():
        print(f"{'*' if n == name else ' '} {n:12s} {pp['layer']:8s} {pp.get('description', '')}")
    print(f"\n* = active ({source}). aix policy use NAME | aix policy off (= anarchy); a task may set its own `policy:` line; a layer its default in defaults.yaml")


def _policy_show(pol, pols, wanted: str):
    if pol.canonical(wanted) == pol.ANARCHY:
        print("anarchy (also: none, nothing, freedom): no file, no steps. Nothing is checked, nobody is stopped."); return
    pp = pols.get(wanted) or sys.exit(f"no policy '{wanted}' (aix policy list)")
    print(pp["path"].read_text(encoding="utf-8"))
    for sid, kind, what, label, level in pol.steps_of(pp):
        print(f"  {sid:16s} {level:9s} {kind:5s} {what}")


def _policy_use(pol, pols, want: str):
    import layers, install_skills as inst
    if want != pol.ANARCHY and want not in pols:
        sys.exit(f"no policy '{want}' (aix policy list)")
    layers.set_key(ROOT, "policy", want, "the development cycle (aix policy use|off); anarchy = none")
    print(f"policy: {want}; updating AGENTS.md")
    inst.install_into(ROOT, copy=False)


def run_policy(args):
    """aix policy [list] | show NAME | use NAME | off  — the development cycle; anarchy = none."""
    import policy as pol
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    pols = pol.policies(ROOT)
    name, source = pol.active_name(ROOT)
    if sub == "list":
        _policy_list(pol, pols, name, source)
    elif sub == "show" and rest:
        _policy_show(pol, pols, rest[0])
    elif sub in ("use", "off"):
        _policy_use(pol, pols, pol.canonical(rest[0]) if sub == "use" and rest else pol.ANARCHY)
    else:
        sys.exit("usage: aix policy [list] | show NAME | use NAME | off")


def run_check(args):
    """aix check [--step ID] [--task TASK-ID]: run the active policy's checks in order."""
    import policy as pol
    only = args[args.index("--step") + 1] if "--step" in args and args.index("--step") + 1 < len(args) else None
    task_policy = None
    if "--task" in args and args.index("--task") + 1 < len(args):
        import roadmap
        tp = roadmap.find(args[args.index("--task") + 1]).read_text(encoding="utf-8")
        task_policy = roadmap.field(tp, "policy") or None
    sys.exit(0 if pol.check(ROOT, task_policy, only) else 1)


def _profile_list(profs, current):
    for name, p in profs.items():
        print(f"{'*' if name == current else ' '} {name:20s} {p['layer']:8s} {p.get('description', '')}")
    print("\n* = active (aix profile use NAME | aix profile off)" if profs else "no profiles (a layer ships them in profiles/<name>.yaml)")


def _profile_use(profs, name: str):
    import layers
    if name and name not in profs:
        sys.exit(f"no profile '{name}' (aix profile list)")
    layers.set_key(ROOT, "profile", name or None, "managed by `aix profile use|off`")
    print(f"profile {'set to ' + name if name else 'cleared'}; applying")
    cmd_install([])


def run_profile(args):
    """aix profile [list] | show NAME | use NAME | off  — a profile is a saved set of choices from a layer."""
    import layers
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    profs = layers.profiles(ROOT)
    if sub == "list":
        _profile_list(profs, layers.config(ROOT).get("profile") or "")
    elif sub == "show" and rest:
        p = profs.get(rest[0]) or sys.exit(f"no profile '{rest[0]}'")
        print(p["path"].read_text(encoding="utf-8"))
    elif sub in ("use", "off"):
        _profile_use(profs, rest[0] if sub == "use" and rest else "")
    else:
        sys.exit("usage: aix profile [list] | show NAME | use NAME | off")
