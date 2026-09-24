---
id: META-GUIDE-CYCLE
title: The development cycle as a policy
---
# 13. The development cycle as a policy

## The problem it solves
The workflow skill tells the agent to write the spec, plan the tests, implement, audit and review. Nothing checked
that any of it happened, and what is not checked gets skipped. A policy turns that list into steps the tool runs,
in order, with a verdict per step, and a task cannot close while a required one fails.

## Anarchy, the default
A fresh project has no cycle. `aix policy list` shows it as `anarchy`, and `none`, `nothing` and `freedom` mean the
same thing. `aix check` prints "nothing is checked, nobody is stopped" and `aix task done` closes any task. Nothing
is imposed until someone opts in.

## The policies the kit ships
```
aix policy list                 what is on offer and which one is active, with where it came from
aix policy show standard        the file and its steps with their levels
aix policy use standard         opt in (policy: standard in .aix/config.yaml; AGENTS.md gets a ## Cycle section)
aix policy off                  back to anarchy
```

| Policy | For | Required | Advised |
|---|---|---|---|
| `minimal` | a small team starting out | style gate, docs valid | implement |
| `standard` | a feature | implement, style, security scan, docs valid | spec, tests, threat model, unit tests, modularity, coverage, audit, review, drift |
| `hotfix` | a bug under pressure | implement, style, security scan, docs valid | the reproducing test, review |
| `release` | closing a version | style, modularity, security, vulnerabilities, docs, the register gate | dead code, clones, coverage, drift, review |

## Two kinds of step
- A **check** is a command the tool runs: `aix code style --gate`, `aix docs validate`, `aix code security --gate`.
  It passes or fails, and a failed required check is the cycle not complete.
- A **skill** is what the agent performs: `spec-write-requirement`, `review-code-review`. The tool lists it in
  order and cannot verify it; it stays the agent's word.

## `aix check`
Runs the checks of the active policy in order and prints one line per step: `pass`, `advice` (an advised check
failed), or `FAIL` (a required one did). `aix check --step security` runs one step. `aix task done TASK-0042` runs
the whole cycle first and refuses to close while a required check fails; `--force` closes anyway and writes that
into the task.

## Which policy applies
Later wins:
1. `anarchy`, the kit's default;
2. a layer's `defaults.yaml`, `policy: standard` in `.aix/org/` or `.aix/custom/`, so an organisation sets its default once;
3. the project's own `policy:` line, `aix policy use`;
4. a task's own `policy:` line in its front matter, `policy: hotfix` for a fix in a project on `standard`,
   `policy: release` for the release task.

## Your own policy
A file `policies/<name>.yaml` in `.aix/custom/` or in the organisation's `org/`:
```
description: Our cycle
order: [spec, implement, lint, style, security, docs, review]
required: [implement, lint, style, docs]
advised: [spec, security, review]
checks:
  lint: npm run lint          # a step of your own, any command; exit code 0 is a pass
```
The known steps are the ones `aix help policy` lists; a check under `checks:` adds any command. The same file name
as a kit policy replaces it.

## What the agent sees
The active policy's steps are the `## Cycle` section of `AGENTS.md`, in order, with their level and what each one
means. The workflow skill follows that section when it exists, so the agent and the tool work from one list.
