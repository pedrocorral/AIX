---
name: core-session-handoff
description: Write the hand-off (task log, files changed, verification, next actions, STATE.md) when a task or workflow step completes, the user says stop/save/wrap up, or the runtime shows ~60% context used, whichever comes first.
---
# core-session-handoff

## Procedure
1. Update the active task: **Progress log** entry (done / half-done at file:function / failed / decisions), **Files changed** list, **Verification performed** (exact command → result), **Exact next actions** (numbered, concrete).
2. Update `context_files` if new files became essential; remove ones no longer needed.
3. **Rewrite** `docs/road-map/going-on/STATE.md` from `templates/session-state.md`: `updated`, `active_task`, "where we are" (3 lines), files to load, verified facts (last test run result, migrations, env), immediate next action (imperative, concrete), blockers/questions.
4. Make sure every doc you created/changed is listed in its folder INDEX. Run `aix docs validate` and fix errors.
5. If the task is done: `aix docs coverage` and `aix task done <TASK>` (or equivalent), check DoD.
6. Commit: `<type>(<scope>): <summary> [IDs]`. Tell the user the next action in one sentence.
