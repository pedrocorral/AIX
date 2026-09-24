---
id: META-GUIDE-TEAM
title: Several agents in one repository
---
# 12. Several agents in one repository

Two agents on the same repository collide in two ways: both take the same task, or two tasks change the same files.
AIX prevents the first with seats and warns about the second with scopes. Files only, no server, git carries it
between machines.

## Seats
A seat is a number: `agent-001`, `agent-002`, up to the total the project allows.
```
aix agent set total 5        how many agents may work at once (default 1: nothing changes for a single agent)
aix agent get total
aix agent claim              take the first free seat for this session
aix agent whoami             which seat this session holds
aix agent list               every seat: free, live, or stale, who sits there, since when
aix agent release            give it back when the session ends
```
The seat file, `docs/road-map/going-on/agents/agent-002.md`, records the tool, the user, the machine, the process,
the start, the last heartbeat and the task. It is committed, so a colleague's machine sees it after a pull. The
session that holds the seat is bound to it on its own machine, so every later `aix` command from that session
signs with it and nobody types a name. `aix task start` claims a seat by itself if the session has none.

## How a stale seat is recognised
A session that ends without releasing leaves its seat file behind. Three signals tell it apart from a working one:
- **On the same machine**, the process id in the seat file. Gone means dead, no doubt: the next claim takes the seat
  over and says so.
- **On another machine**, the heartbeat. Every `aix task` and `aix agent` command from the owner refreshes it. Older
  than the lease, `aix agent set lease 4h`, the seat counts as expired and `aix agent claim --force` takes it. Without
  `--force` it is left alone, because a slow session on another laptop is not a dead one.
- **The release**, which a well-behaved session does. The hand-off skill does it.
When every seat is live the claim is refused with the list of who is working and their tasks: raise the total or wait.

## Tasks are signed
`aix task start TASK-0042` writes `owner: agent-002`, `claimed:` and `claimed_by: opencode ana@laptop` into the task, so a completed task still says who did it long after the seat was released. Another live seat starting the
same task is refused with the holder's name; `--force` takes it over, for a seat that is stale. `aix task list`
shows the owner of every task.

## Scopes
A task says which paths it will change:
```
scope: [backend/app/orders/**, docs/requirements/functional/orders/**]
```
`aix task start` warns when the scope overlaps a task already going on, and `aix task list` shows overlaps among
open tasks so whoever orders the backlog serialises them, `after: TASK-0041`, or merges them. The rule the agents
are given: never change a file inside another going-on task's scope.

## One state per seat
With more than one seat, each session writes its own `STATE-agent-002.md` and `STATE.md` becomes a generated
overview: every seat, its state, its task, its next action, its heartbeat. Resume reads the overview, then your own
file. With one seat nothing changes: `STATE.md` is yours, as before.

## What doctor says
`aix doctor` reports stale seats, and going-on tasks whose owner is not a live seat. Both mean a session ended badly.

## Limits, stated plainly
Two agents editing the same file outside any declared scope are not stopped; only the scope discipline and git
catch it. Seats do not lock files. On Windows the process check is not available, so the lease decides there too.
