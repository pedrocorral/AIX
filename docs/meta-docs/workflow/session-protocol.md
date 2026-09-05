---
id: META-WORKFLOW-SESSION
title: Session resume and hand-off protocol
---
# Session protocol

Agent context windows end; the project must not lose state. `docs/road-map/going-on/STATE.md` is the
hand-off note; the active `TASK-*.md` is the detailed log.

## Resume (skill `core-session-resume`) — budget: < 3 000 tokens of reading
1. Read `STATE.md`. If `active_task: none`, read `docs/road-map/pending/next/INDEX.md` and pick the top task (ask if unclear).
2. Read the active task file. Load **only** the paths in `context_files:`.
3. Verify "last verified facts" cheaply (run the test subset named in the task, `git status`).
4. Announce in one paragraph: task, next action, anything stale. Then work.

## Hand-off (skill `core-session-handoff`) — triggers, whichever comes first
- **Event:** a task or a workflow step (spec, tests, implement, audit, review) is completed; the user says stop / save / wrap up.
- **Threshold:** the runtime shows ~60 % of the context window used (Claude Code and opencode display it; Copilot does not, so rely on the event trigger there).
- Why 60 %: quality of long-context recall degrades gradually with input length (no cliff), Claude Code auto-compacts around 80 % with a lossy summary the agent does not control, and the hand-off itself costs 5-10 % of the window. 60 % leaves the notes written from the real work, not from a summary.

1. Append to the task's progress log: what was done, what is half-done (file:function), what failed.
2. Rewrite `STATE.md` fully (it is a snapshot, not a log): where we are, files to load, verified facts,
   immediate next action, blockers.
3. Ensure every changed doc is listed in its INDEX and `aix validate` passes.
4. Commit with IDs in the message.

## Multi-agent / parallel work
One task per agent. `STATE.md` may list several `active_task` lines suffixed by owner
(`active_task: TASK-0012 (agent:opencode-A)`). Never edit another task's file.
