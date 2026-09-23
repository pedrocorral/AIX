---
id: META-GUIDE-MAINTAIN
title: Maintaining and troubleshooting
---
# 10. Maintaining and troubleshooting

## `aix doctor`
The health check of an installation. Every problem comes with its fix. It checks: Python and PATH; the pointer
files of the selected agents; every skill linked in every selected agent's folder, and no dangling link; always-on
skills named consistently; downloaded skills with their provenance; STATE.md; kit files edited locally (they are
lost at the next upgrade: make the change in the kit or in a layer); the index of active implementations against
the linked content; the agents and instructions in force; AGENTS.md sections that no block produced; layer files
that override nothing (chapter 7); leftovers of a deselected agent.

## Versions
`aix version` prints the version of the copy that runs. Inside a project that is the project's copy, and the line
also names the kit on your PATH with a hint to upgrade when they differ. This is the usual surprise: the `aix` on
PATH is new, the project still runs its own older copy, until `aix upgrade`.

Versioning: a major only for breaking changes, a minor for functionality (minors count past 9), a patch for fixes.
Every release has a changelog entry and a git tag.

## The kit's own tests
From a clone: `aix self-test` runs the whole suite in temporary folders; `aix self-test agents` one file;
`--network` adds the registry downloads; `-q` hides the per-test lines. Projects carry no tests.

## Common problems
| Symptom | Cause | Fix |
|---|---|---|
| `aix: command not found` | `~/.local/bin` not on PATH | `aix self-install` from the clone, then a new terminal |
| `aix version` says an old version inside a project | the project's own copy runs | `aix upgrade` there |
| `aix upgrade: cannot upgrade itself` | you ran the project's copy | run the `aix` on PATH from inside the project |
| `git: dubious ownership` | the clone belongs to another user | `git config --global --add safe.directory <clone>` |
| the code tools find nothing | none of the configured folders exists | `aix code find` |
| a skill of yours is ignored | class name differs from the kit's by a character | `aix doctor` says "did you mean" |
| a teammate's copy differs from yours | `.aix/` is not committed | `aix upgrade` on both from the same origin |
| Copilot or Cursor do not see a standard | the agent is not selected | `aix agents`, or `aix instructions info ID` |
| `AGENTS.md` lost a hand edit | edited outside `## Project notes` | put it back in that section, or in a block in `custom/` |
| a 1.x project (root `framework.yaml`) | old layout | `aix upgrade` migrates it |
