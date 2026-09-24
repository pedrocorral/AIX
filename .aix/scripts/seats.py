#!/usr/bin/env python3
"""Leaf: seats for several agents working in one repository. `aix agent claim|release|whoami|list|set|get`.

A seat is a number, agent-001 .. agent-NNN (`agents_total` in .aix/config.yaml, default 1). A seat file
docs/road-map/going-on/agents/agent-001.md (committed, so other machines see it through git) records who sits there:
tool, user, host, process id, start, heartbeat, task. The session that holds the seat is bound to it locally
(.aix/sessions/<session>.json, never committed), so every later `aix` command from that session signs with it.

A seat is free (no file), live, or stale. Stale means: on this host, the process is gone (proof: the session ended
without releasing); on another host, the heartbeat is older than `agents_lease` (default 4h). A dead-process seat is
taken over silently with a notice; a lease-expired seat elsewhere only with --force (a slow session is not a dead one).
Nothing free and nothing stale: refused, with the list of who is working."""
import datetime, json, os, re, socket, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWN_AGENTS = {"claude": "claude", "code": "copilot", "code-insiders": "copilot", "copilot": "copilot", "cursor": "cursor",
                "gemini": "gemini", "antigravity": "gemini", "opencode": "opencode", "codex": "codex"}


# ---- settings ---------------------------------------------------------------------------------------------------------

def setting(project: Path, key: str, default: str) -> str:
    cfg = project / ".aix" / "config.yaml"
    m = re.search(rf"^{key}:\s*([^\s#]+)", cfg.read_text(encoding="utf-8"), re.M) if cfg.exists() else None
    return m.group(1) if m else default


def set_setting(project: Path, key: str, value: str, comment: str):
    cfg = project / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    line = f"{key}: {value}   # {comment}"
    text = re.sub(rf"^{key}:.*$", line, text, count=1, flags=re.M) if re.search(rf"^{key}:", text, re.M) else text.rstrip("\n") + "\n" + line + "\n"
    cfg.write_text(text, encoding="utf-8")


def total(project: Path = ROOT) -> int:
    return max(1, int(setting(project, "agents_total", "1")))


def lease_seconds(project: Path = ROOT) -> int:
    return parse_duration(setting(project, "agents_lease", "4h"))


def parse_duration(s: str) -> int:
    m = re.fullmatch(r"(\d+)\s*([smhd]?)", s.strip())
    if not m:
        raise SystemExit(f"aix agent: bad duration '{s}' (examples: 30m, 4h, 1d)")
    return int(m.group(1)) * {"": 60, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


# ---- the session behind this command ------------------------------------------------------------------------------------

def host() -> str:
    return os.environ.get("AIX_HOST") or socket.gethostname()


def user() -> str:
    return os.environ.get("AIX_USER_NAME") or os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def ancestors():
    """[(pid, name)] from this process's parent upwards (POSIX via ps; Windows: the parent only)."""
    if os.name == "nt":
        return [(os.getppid(), "shell")]
    try:
        out = subprocess.run(["ps", "-eo", "pid=,ppid=,comm="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return [(os.getppid(), "shell")]
    table = {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), Path(parts[2].strip()).name)
    chain, pid = [], os.getppid()
    while pid > 1 and pid in table and len(chain) < 30:
        ppid, name = table[pid]
        chain.append((pid, name))
        pid = ppid
    return chain or [(os.getppid(), "shell")]


def session():
    """(key, pid, tool): the agent process this command runs under. AIX_SESSION / AIX_SESSION_PID / AIX_TOOL override
    (tests, and agents whose process cannot be recognised)."""
    if os.environ.get("AIX_SESSION"):
        return os.environ["AIX_SESSION"], int(os.environ.get("AIX_SESSION_PID") or os.getppid()), os.environ.get("AIX_TOOL", "agent")
    chain = ancestors()
    for pid, name in chain:
        if name in KNOWN_AGENTS:
            return f"{name}-{pid}", pid, KNOWN_AGENTS[name]
    pid, name = chain[min(1, len(chain) - 1)]  # the shell's parent: a terminal, an IDE, an unknown agent
    return f"{name}-{pid}", pid, os.environ.get("AIX_TOOL", "agent")


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return True  # cannot tell cheaply; the lease decides
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


# ---- seat files -------------------------------------------------------------------------------------------------------

def seats_dir(project: Path) -> Path:
    return project / "docs" / "road-map" / "going-on" / "agents"


def sessions_dir(project: Path) -> Path:
    return project / ".aix" / "sessions"


def seat_name(n: int) -> str:
    return f"agent-{n:03d}"


def read_seat(path: Path) -> dict:
    fm = {}
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        for line in text[3:].split("\n---", 1)[0].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    fm["name"] = path.stem
    return fm


def write_seat(project: Path, name: str, info: dict):
    d = seats_dir(project)
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "INDEX.md").exists():
        (d / "INDEX.md").write_text("# road-map/going-on/agents/ — the seats taken by agents working in this repository\nManaged by `aix agent claim | release | list`; one file per seat (agent-001 ...): tool, user, host, process, heartbeat, task. A seat file is not edited by hand.\n\n| Path | What |\n|---|---|\n| `agent-NNN.md` | One taken seat |\n", encoding="utf-8")
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in info.items()) + f"---\n# {name}\nSeat taken by {info.get('tool', '?')} ({info.get('user', '?')}@{info.get('host', '?')}). Released with `aix agent release`; stale seats are reported by `aix agent list` and `aix doctor`.\n"
    (d / f"{name}.md").write_text(body, encoding="utf-8")


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def age_seconds(stamp: str) -> float:
    try:
        t = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return float("inf")
    return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()


def state_of(project: Path, seat: dict) -> str:
    """'live' | 'dead' (same host, process gone) | 'expired' (other host, heartbeat past the lease) | 'remote' (other host, fresh)."""
    if seat.get("host") == host():
        return "live" if pid_alive(int(seat.get("pid") or 0)) else "dead"
    return "expired" if age_seconds(seat.get("heartbeat", "")) > lease_seconds(project) else "remote"


def all_seats(project: Path) -> dict:
    d = seats_dir(project)
    out = {}
    for n in range(1, total(project) + 1):
        name = seat_name(n)
        f = d / f"{name}.md"
        out[name] = {**read_seat(f), "state": None} if f.exists() else None
        if out[name]:
            out[name]["state"] = state_of(project, out[name])
    return out


# ---- binding: which seat is mine ----------------------------------------------------------------------------------------

def binding_file(project: Path) -> Path:
    key, _, _ = session()
    return sessions_dir(project) / (re.sub(r"[^A-Za-z0-9._-]", "_", key) + ".json")


def mine(project: Path = ROOT):
    """The seat bound to this session, when its seat file still names this session; else None."""
    f = binding_file(project)
    if not f.exists():
        return None
    try:
        name = json.loads(f.read_text(encoding="utf-8"))["seat"]
    except (ValueError, KeyError):
        return None
    seat_file = seats_dir(project) / f"{name}.md"
    if not seat_file.exists():
        return None
    seat = read_seat(seat_file)
    key, pid, _ = session()
    if seat.get("host") != host() or seat.get("session") != key:
        return None
    return name


def bind(project: Path, name: str):
    d = sessions_dir(project)
    d.mkdir(parents=True, exist_ok=True)
    binding_file(project).write_text(json.dumps({"seat": name, "since": now()}) + "\n", encoding="utf-8")


def claim(project: Path = ROOT, force: bool = False) -> str:
    """Take a seat for this session (or keep the one it has). Prints what happened; exits when the table is full."""
    have = mine(project)
    if have:
        heartbeat(project)
        print(f"{have}: yours (already)")
        return have
    key, pid, tool = session()
    info = {"tool": tool, "user": user(), "host": host(), "pid": pid, "session": key, "started": now(), "heartbeat": now(), "task": "none"}
    seats = all_seats(project)
    for name, seat in seats.items():
        if seat is None:
            write_seat(project, name, info); bind(project, name)
            print(f"{name}: yours ({tool}, {info['user']}@{info['host']})")
            return name
    for name, seat in seats.items():
        if seat["state"] == "dead" or (seat["state"] == "expired" and force):
            why = "its process is gone (the session ended without releasing)" if seat["state"] == "dead" else f"its heartbeat is older than {setting(project, 'agents_lease', '4h')} (--force)"
            info["took_over"] = f"{seat.get('tool')} {seat.get('user')}@{seat.get('host')} pid {seat.get('pid')}: {why}"
            write_seat(project, name, info); bind(project, name)
            print(f"{name}: yours, taken over: {why}")
            return name
    lines = [f"  {n}: {s.get('tool')} {s.get('user')}@{s.get('host')}, task {s.get('task')}, {s['state']}, heartbeat {int(age_seconds(s.get('heartbeat', '')) // 60)} min ago" for n, s in seats.items() if s]
    expired = [n for n, s in seats.items() if s and s["state"] == "expired"]
    hint = f"; {', '.join(expired)} expired on another machine: `aix agent claim --force` takes it" if expired else "; `aix agent set total N` adds seats"
    sys.exit(f"aix agent: all {total(project)} seats are taken{hint}\n" + "\n".join(lines))


def heartbeat(project: Path = ROOT, task: str = None):
    name = mine(project)
    if not name:
        return None
    f = seats_dir(project) / f"{name}.md"
    seat = read_seat(f)
    seat["heartbeat"] = now()
    if task is not None:
        seat["task"] = task
    seat.pop("name", None)
    write_seat(project, name, seat)
    return name


def release(project: Path = ROOT) -> str:
    name = mine(project)
    if not name:
        sys.exit("aix agent release: this session holds no seat")
    (seats_dir(project) / f"{name}.md").unlink()
    binding_file(project).unlink(missing_ok=True)
    print(f"{name}: released")
    return name


def rows(project: Path = ROOT):
    me = mine(project)
    out = []
    for name, seat in all_seats(project).items():
        if seat is None:
            out.append((name, "free", "", "", "", ""))
        else:
            age = age_seconds(seat.get("heartbeat", ""))
            out.append((name, seat["state"] + (" (you)" if name == me else ""), seat.get("tool", ""), f"{seat.get('user', '')}@{seat.get('host', '')}", seat.get("task", "none"), f"{int(age // 60)} min ago" if age != float('inf') else "?"))
    return out


def report(project: Path = ROOT):
    print(f"{'SEAT':10s} {'STATE':16s} {'TOOL':9s} {'WHO':24s} {'TASK':10s} HEARTBEAT")
    for r in rows(project):
        print(f"{r[0]:10s} {r[1]:16s} {r[2]:9s} {r[3]:24s} {r[4]:10s} {r[5]}")
    print(f"\n{total(project)} seats (aix agent set total N); lease {setting(project, 'agents_lease', '4h')} (aix agent set lease 4h). "
          "dead = process gone on this machine, taken over by the next claim; expired = no heartbeat past the lease on another machine, --force takes it.")


def stale(project: Path = ROOT) -> list:
    return [(n, s) for n, s in all_seats(project).items() if s and s["state"] in ("dead", "expired")]
