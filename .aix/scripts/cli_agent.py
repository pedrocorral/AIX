"""`aix agent` (seats: claim, release, whoami, list, set/get total and lease) and `aix agents` (which tools the
project equips)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _agent_whoami(seats):
    me = seats.mine(ROOT)
    _, pid, tool = seats.session()
    print(me or f"no seat (this session: {tool}, {seats.user()}@{seats.host()}, process {pid}); `aix agent claim` takes one")


def _agent_set_total(seats, value: str):
    if not value.isdigit() or int(value) < 1:
        sys.exit("aix agent set total N: N must be 1 or more")
    n = int(value)
    taken = [name for name, s in seats.all_seats(ROOT).items() if s and int(name[6:]) > n]
    if taken:
        sys.exit(f"cannot shrink to {n}: {', '.join(taken)} still taken (release them first)")
    seats.set_setting(ROOT, "agents_total", str(n), "seats for agents working in this repository at once (aix agent)")


def _agent_set(seats, rest):
    if len(rest) != 2 or rest[0] not in ("total", "lease"):
        sys.exit("usage: aix agent set total N | set lease 4h")
    if rest[0] == "total":
        _agent_set_total(seats, rest[1])
    else:
        seats.parse_duration(rest[1])
        seats.set_setting(ROOT, "agents_lease", rest[1], "a seat on another machine with no heartbeat for this long counts as stale (aix agent)")
    print(f"agents_{rest[0]}: {rest[1]}")


def _agent_get(seats, rest):
    if rest[:1] not in (["total"], ["lease"]):
        sys.exit("usage: aix agent get total | get lease")
    print(seats.setting(ROOT, "agents_total", "1") if rest[0] == "total" else seats.setting(ROOT, "agents_lease", "4h"))


def run_agent(args):
    """aix agent claim [--force] | release | whoami | list | set total N | set lease 4h | get total|lease"""
    import seats
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    actions = {
        "claim": lambda: seats.claim(ROOT, "--force" in rest),
        "release": lambda: seats.release(ROOT),
        "whoami": lambda: _agent_whoami(seats),
        "list": lambda: seats.report(ROOT),
        "get": lambda: _agent_get(seats, rest),
        "set": lambda: _agent_set(seats, rest),
    }
    if sub not in actions:
        sys.exit("usage: aix agent claim [--force] | release | whoami | list | set total N | set lease 4h | get total | get lease")
    actions[sub]()


def run_agents(args):
    """aix agents [NAME... | all] [--list]: which agents the project equips; checklist in a terminal."""
    import agents, install_skills as inst
    if any(a.startswith("--") and a != "--list" for a in args):
        sys.exit("usage: aix agents [NAME... | all] [--list]   (names: " + ", ".join(agents.AGENTS) + ")")
    names = [a for a in args if not a.startswith("--")]
    changed = agents.run(ROOT, names, "--list" in args)
    if changed or names:
        for r in agents.remove_deselected(ROOT, agents.selected(ROOT)):
            print(f"  removed {r}")
        inst.install_into(ROOT, copy=False)
        import gitignore
        gitignore.ask_and_apply(ROOT, label="aix agents")
