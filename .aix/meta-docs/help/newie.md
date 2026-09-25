aix newie   (also: aix for-dummies)

AIX in one screen. The rest is `aix guide`, when you need it.

WHAT IT IS
  A kit you install into a project so that a coding agent (Claude Code, Copilot, Cursor, Gemini, ...) works from
  written specs, leaves a trail, and passes the same checks every time. The docs are the ground truth; the code
  implements them; `aix` keeps both honest.

SET UP, ONCE
  aix self-install                 makes `aix` callable from any terminal (from a clone of AIX)
  aix install --into ~/my-app      puts the kit into a project: skills, instructions, a docs/ seed, AGENTS.md
  cd ~/my-app && aix doctor        says what is missing, with a fix per line

EVERY DAY
  aix task new "export notes as CSV"     a task file appears; the agent works from it
  aix task start TASK-0001               claims it; STATE.md records where you are
  ... the agent writes the spec, the code and the tests, following the skills ...
  aix check                              the checks of the active policy, in order (style, docs, ...)
  aix task done TASK-0001                closes it, only if the required checks pass

WHEN SOMETHING IS ODD
  aix doctor                       the installation
  aix code style                   which functions are too long or too tangled, with a fix per line
  aix docs validate                which document is inconsistent (ids, links, indexes)
  aix help <command>               the options of one command;  aix guide <chapter>  the longer story

THREE THINGS TO KNOW
  1. Nothing runs outside your machine: no network, no telemetry, no CI. `aix` reads and writes files in the project.
  2. `.aix/` is the kit's; `.aix/custom/` and `docs/` are yours. `aix upgrade` refreshes the first and keeps the rest.
  3. A gate that fails is information, not a wall: `aix check` names the check, the tool names the line, the skill
     names the fix. `aix policy off` if you want no checks at all (the default is exactly that: anarchy).
