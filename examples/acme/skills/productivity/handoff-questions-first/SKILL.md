---
name: core-session-handoff
class: core/session-handoff
id: "@acme/handoff-questions-first"
version: 1.0.0
description: Write the hand-off (task log, files changed, verification, next actions, STATE.md) when a task or workflow step completes, the user says stop/save/wrap up, or the runtime shows ~60% context used, whichever comes first.
---
# @acme/handoff-questions-first

ACME hand-offs start with the questions the next agent will ask, then answer them.
1. Write the five questions: what was the goal, what is done and proven, what is half-done (file:function), what failed and why, what is the next command.
2. Answer each in ≤ 2 lines; commands verbatim; ids for everything.
3. STATE.md gets the same five answers (it is a snapshot, never a log); the task file gets the log entry.
4. `aix docs validate`; commit with ids. Nothing else in this skill.
