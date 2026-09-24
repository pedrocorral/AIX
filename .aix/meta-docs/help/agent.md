aix agent claim [--force] | release | whoami | list | set total N | get total | set lease 4h | get lease
aix task start ID [--force]

Several agents in one repository, without collisions. A seat is a number, agent-001 up to `agents_total`
(default 1: a single-agent project changes nothing). `aix agent claim` takes the first free seat for this session
and binds it locally (.aix/sessions/), so every later command from the same session signs with it; `aix task start`
claims one by itself. The seat file docs/road-map/going-on/agents/agent-NNN.md (committed) says who sits there:
tool, user, host, process, heartbeat, task; other machines see it through git.
A seat is free, live, or stale. Stale on this machine = the process is gone (the session ended without releasing):
the next claim takes it over and says so. Stale on another machine = no heartbeat for `agents_lease` (default 4h):
only `claim --force` takes it, a slow session is not a dead one. Nothing free, nothing stale: refused, listing who works.
`aix task start ID` signs the task with the seat (owner:, claimed:) and refuses a task another live seat holds
(--force takes it); tasks declare `scope:` (paths/globs) and a start warns when two going-on tasks overlap;
`aix task list` shows owners and overlaps among open tasks. With more than one seat, each seat has its own
STATE-agent-NNN.md and STATE.md becomes the generated overview of every seat. `aix agent release` at the end
of a session; the hand-off skill does it. `aix doctor` reports stale seats and tasks held by no live seat.
Agents whose process is not recognised (claude, code, cursor, gemini, opencode, codex) still get a seat, listed as
`agent`; AIX_TOOL names them, AIX_HOST overrides the host name.
