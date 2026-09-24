aix policy [list] | show NAME | use NAME | off        aix check [--step ID] [--task TASK-ID]
aix task done TASK-ID [--force]

A policy is the development cycle: an ordered list of steps, each required or advised. Two kinds of step: a check
the tool runs (aix code style --gate, aix docs validate, ...) and a skill the agent performs (spec-write-requirement,
review-code-review, ...). `aix check` runs the checks in order and prints pass / advice / FAIL per step; a failed
required check is the cycle not complete, and `aix task done` refuses to close the task (--force closes anyway,
noted in the task). The active policy's steps are listed in the `## Cycle` section of AGENTS.md, so the agent
and the tool follow one list.
Which policy applies, later wins: anarchy (the kit's default: no cycle, nothing checked) < a layer's defaults.yaml
(`policy: standard` in org/ or custom/) < `policy:` in .aix/config.yaml (aix policy use) < a task's own `policy:`
line (a hotfix in a standard project). `none`, `nothing` and `freedom` are synonyms of anarchy.
The kit ships: minimal (style, docs), standard (spec, tests, threat, implement, tests, style, modularity, security,
docs, coverage, audit, review, drift), hotfix (test, fix, style, security, docs, review), release (adds
vulnerabilities, dead code, clones, the register gate). A layer adds or replaces policies/<name>.yaml; a policy may
define its own checks (`checks: {lint: npm run lint}`) and use them in `order`.
Steps: spec, tests, threat, implement, unit-tests, audit, review, drift (skills); style, modularity, dead, clones,
security, vulnerabilities, docs, coverage, register (checks). `aix policy show NAME` prints a policy's steps.
