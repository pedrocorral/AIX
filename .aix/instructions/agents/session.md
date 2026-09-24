---
id: aix/agents/session
description: "How a session starts, works and hands off: the three core skills and the 60 % rule."
block: true
order: 40
section: "Session"
---
Start: `core-session-resume`. Work: `core-sdd-workflow`. `core-session-handoff` after every completed task or workflow step, on stop/save, or at ~60 % context used, whichever first.
Several agents may share this repository: a task is taken with `aix task start ID`, which signs it with your seat (agent-NNN) and refuses a task another live seat holds; then pick another. Never change files inside another going-on task's `scope:`. Your own state file is `docs/road-map/going-on/STATE-<seat>.md` when the table has more than one seat; `STATE.md` is then the overview. `aix agent release` when you stop.
