aix task new "Title" [--bucket next|backlog|ideas] | start ID | block ID "reason" | done ID | list

Moves TASK-* files through the road-map and keeps docs/road-map/going-on/STATE.md in sync:
  pending/{ideas,backlog,next}  ->  going-on  <->  blocked  ->  completed/YYYY-MM/
  new     create pending/<bucket>/TASK-nnnn-title.md from .aix/templates/task.md
  start   move to going-on/, status going-on, STATE.md active_task = ID
  block   move to blocked/, note the reason, clear active_task
  done    move to completed/YYYY-MM/ (creating the month INDEX), stamp the date, clear active_task
  list    one line per task with status
Never move task files by hand; agents use this through the core-roadmap-task skill.
