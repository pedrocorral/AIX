---
id: META-GUIDE-ORGANISATION
title: Organisations, projects and people
---
# 7. Organisations, projects and people

## The four layers
A layer is a folder shaped like `.aix/`: `skills/`, `instructions/`, `profiles/`, `templates/`. A file at the same
path as the kit's replaces it; a new path adds; an empty `DISABLED` file in a skill folder removes that class.
Later wins:

| Layer | Where | Who | Committed |
|---|---|---|---|
| kit | `.aix/` | AIX | ignored (see chapter 3) |
| organisation | `.aix/org/` | your company | arrives from the origin |
| person | `~/.config/aix/` | you | never; terminal sessions only, never CI |
| project | `.aix/custom/` | the project | with the project (unless `.aix/` is ignored) |

## Rolling AIX out to a company
1. Fork the kit repository. Fill `.aix/org/` with your skills (each with `class:` and an `id`), your instructions
   (blocks to replace, standards with `applyTo`), your profiles, and optionally `templates/docs/` (files overlaid on
   the documentation every project receives) and `templates/pointers/` (your text for `CLAUDE.md` and the others).
   `examples/acme/` in the kit is a complete fictional organisation to copy from: 37 skills, 8 instructions, 2 profiles.
2. Projects install from the fork: `aix install --into my-app --from <fork path or git url>`. The fork's `.aix/` is
   the payload and its `org/` and `custom/` are copied. The source is recorded in the project's config.
3. A colleague edits the fork's `.aix/org/`; every project gets it at its next `aix upgrade` run from that fork.
4. Upstream releases reach the fork by a normal git merge: upstream keeps `org/` and `custom/` empty.

The two layers follow one rule: copied at install when the origin has the folder, replaced at upgrade when it has
it, left alone when it does not. `--from-org SRC` and `--from-custom SRC`, on install and on upgrade, take one layer
from somewhere else, a bare folder or another repository, and remember it.

A bare folder with `skills/` and `instructions/` at its top, such as `examples/acme`, works as `--from` too: the
payload then comes from your clone and the folder becomes `org/`.

## A person's overrides
`~/.config/aix/skills/<category>/<name>/` replaces a skill for you alone, only when you run an agent from a terminal.
CI and reproducible checks ignore it (`AIX_NO_USER=1` forces that; `AIX_USER=1` forces it on). `aix skills info`
says when your layer won.

## A project's overrides
`.aix/custom/` is the project's. Same shapes. Every command that shows a choice names the layer it came from:
`aix skills info NAME`, `aix instructions info ID`, `aix doctor`.

## The near-miss check
Names match character by character. A skill folder `coach/grill_me` in your layer does not replace `coach/grill-me`;
it adds a second skill next to it. `aix doctor` and `aix docs validate` therefore report every layer file that
overrides nothing: an error with "did you mean" when the name is one edit away from a kit name, a one-line note
when it is a genuine addition.
