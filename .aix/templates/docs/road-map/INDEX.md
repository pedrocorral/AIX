# road-map/ — what is pending, going on, and done
Read this when: session start/end; choosing work. Skip when: never at session start.

| Path | What | Read when |
|---|---|---|
| `going-on/STATE.md` | **Resume point.** Snapshot: active task, files to load, next action | Every session start |
| `going-on/` | Active `TASK-*.md` files (one per agent) | Resuming |
| `pending/next/` | Prioritised, ready to start (has requirements + tests planned) | Picking work |
| `pending/backlog/` | Agreed but not ready (missing spec/tests) | Grooming |
| `pending/ideas/` | Unvetted ideas; no ID promises | Brainstorming |
| `blocked/` | Tasks waiting on a user decision or external dependency (reason in file) | Session start; unblocking |
| `completed/YYYY-MM/` | Done tasks, immutable | History; "was X done?" (`grep -rl "FR-…" completed`) |
| `rules.md` | Task lifecycle and file rules | Creating/moving tasks |

Helper: `aix task new "title" | start TASK-… | block TASK-… "reason" | done TASK-… | list`.
