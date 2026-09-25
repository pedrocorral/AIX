aix newie 2   —   the loop, one level deeper            (aix newie for the first screen; aix newie 3 for the next)

A TASK IS THE UNIT OF WORK
  docs/road-map/            pending/  going-on/  blocked/  completed/   one Markdown file per task, moved by `aix task`
  aix task new "..."        creates it in pending/ with a scope (which paths it may touch) and a plan
  aix task start ID         moves it to going-on/, claims a seat for this agent, writes STATE.md
  aix task block ID "why"   parks it with the reason;  aix task done ID  closes it once the checks pass

STATE.md IS WHERE YOU ARE
  docs/road-map/going-on/STATE.md: the active task, the files to load, the last verified facts, the immediate next
  action. An agent that resumes reads it first; an agent that stops writes it last. Never the whole history.

THE CHECKS ARE A POLICY
  aix policy list           anarchy (nothing), minimal (style + docs), standard, hotfix, release
  aix policy use standard   the project's cycle; a task may carry its own `policy:` line for one job
  aix check                 runs the active policy's checks in order and stops at the first required failure
  Each check is a command you can run alone: aix code style --gate, aix docs validate, aix code security --gate ...

SEVERAL AGENTS, ONE REPOSITORY
  aix agent set total 3     three seats; each agent claims one (aix task start does it), each has its own STATE
  aix task list             who holds what, and which scopes overlap

THE DOCS ARE THE GROUND TRUTH
  docs/requirements/  FR-, NFR-, API-, DM-, ADR-   what to build and why;  docs/tests/  TS-  how it is proven
  docs/security/      the vulnerability register, one row per threat, moved by audits with evidence
  aix docs validate   ids, links, indexes, statuses;   aix docs coverage   which FR has a TS and a marker in code
