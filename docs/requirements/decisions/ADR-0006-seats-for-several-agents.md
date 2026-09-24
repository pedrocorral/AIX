---
id: ADR-0006
title: Seats, not names, for several agents in one repository
status: accepted
date: 2026-09-24
supersedes: []
affects: [.aix/scripts/seats.py, roadmap.py, docs/road-map/going-on]
---
# ADR-0006 — Seats, not names, for several agents in one repository
## Context
Two agents on one repository collide on tasks (both take the same one) and on files (two tasks change the same
paths). A name chosen by the agent is not stable across sessions and two sessions of the same tool would share it.
## Decision
Identity is a numbered seat, `agent-001` up to `agents_total`, claimed per session and bound locally, recorded in a
committed seat file with tool, user, host, process, heartbeat and task. Liveness: process id on the same machine
(proof), heartbeat against `agents_lease` elsewhere (`--force` to take over). `aix task start` signs tasks with the
seat and refuses one a live seat holds; tasks declare `scope:` and overlaps are warned, not blocked. One state file
per seat, `STATE.md` as the generated overview, only when the total is above one.
## Consequences
No server, no daemon, no file locks: files and git. Two agents editing outside any declared scope are not stopped.
A single-agent project changes nothing.
