---
id: META-GUIDE-SKILLS
title: Skills
---
# 5. Skills

## What the kit ships
71 skills in ten categories: core (the session loop, finding documents, tasks), spec, architecture, implement,
testing, security (an orchestrator and ten audits), review, refactor (one per finding of the code tools), workflow,
coach, debug. `aix skills` lists them with their state. `aix skills info NAME` explains one; `aix skills show NAME`
prints it.

A skill's name is its class written flat: the class `coach/grill-me` is the skill `coach-grill-me`, and that is the
folder the agents see and the name you type to invoke it.

## States
| State | Meaning |
|---|---|
| `on-demand` | Installed; the agent loads it when the task matches its description, or when you invoke it |
| `(*) always` | Named in `AGENTS.md`: applied in every session (`aix skills always NAME`, `on-demand NAME` reverts) |
| `manual` | Installed, only when you invoke it by name (the skill says `disable-model-invocation: true`) |
| `disabled` | Unlinked from every agent (`aix skills disable NAME`, `enable NAME` restores) |
| `recommended`, `available` | In the registry, not downloaded (`aix skills add NAME`) |

## Several implementations of one class
An organisation, a project or a download may bring another way of doing the same job. Each is an implementation of
the class, with its own `id`. One is active; `aix skills info NAME` lists the alternatives and the exact line to
switch:
```
aix skills use implement-endpoint @acme/django-endpoint     pin one implementation
aix skills use implement-endpoint default                    back to the normal choice
```
The normal choice, when nothing is pinned: the active profile's `skills:` map if it names the class, otherwise the
highest layer that ships one (project over person over organisation over kit). A pin is the line under `use:` in
`.aix/config.yaml` and survives upgrades.

## Third-party skills: the registry
`aix skills registry` lists known skills from public repositories with an evidence line saying who measured what.
`aix skills add NAME` downloads one (a tarball over HTTPS, no git) into `.aix/skills/extern/NAME/`:
- an entry with a `class` becomes an implementation of that kit class, selected at once, so `aix skills add grill-me`
  replaces the kit's `coach-grill-me` with Matt Pocock's and `aix skills use coach-grill-me default` goes back;
- an entry without one, such as `caveman` or `ponytail`, keeps its own name and is linked next to the others;
  general ones become always-on unless `--on-demand`.
`aix skills update` re-downloads, `aix skills remove NAME` deletes. Downloads are the project's; upgrades leave
them alone.

## Writing your own
Put a folder under `.aix/custom/skills/<category>/<name>/` with a `SKILL.md`:
```
---
name: coach-grill-me            must equal the class written flat
class: coach/grill-me           the job (omit it when the folder path already is the class path)
id: "@myteam/grill-me-timed"    this implementation's name
description: When to use it, in one or two sentences with the trigger words.
---
# Procedure ...
```
Same class path as the kit's: yours replaces it. New path: a new class, linked like any other. An empty file named
`DISABLED` in a class folder removes that class. `aix docs validate` checks the front matter; `aix doctor` warns when
a class name is one edit away from a kit name, which is almost always a typo that would add a second skill instead of
replacing one. The skill `spec-write-skill` helps write a good one.
