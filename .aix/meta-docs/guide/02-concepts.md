---
id: META-GUIDE-CONCEPTS
title: The concepts
---
# 2. The concepts

Eight words explain everything AIX does. Each has one meaning.

## Agent
The tool that reads the files: Claude Code, GitHub Copilot, Cursor, Gemini CLI, OpenCode, Codex. Whatever model it
runs, the agent is the software with the loop, the tools and the file access. Each agent reads its own folder of
skills and, for those that do not read `AGENTS.md` by themselves, a pointer file. A project says which agents it
equips with `aix agents`. Chapter 4.

## Skill
A folder with a `SKILL.md` file, in the open Agent Skills format that every agent understands. A skill is a
procedure the agent loads on demand: when your request matches its description, or when you invoke it by name.
Two words matter inside a skill:
- **class**: the job, for example `coach/grill-me` or `implement/endpoint`. The kit has one skill per class.
- **implementation**: one way of doing that job, with an `id` such as `@acme/django-endpoint`. Several implementations
  of one class can exist side by side, one is active. Chapter 5.

## Instruction
A markdown file the agent obeys passively, without being asked. Two shapes:
- **block**: a section of `AGENTS.md` itself. `aix install` assembles `AGENTS.md` from the blocks.
- **scoped**: a standard that applies always, or when the agent touches files matching its globs, for example the
  FastAPI standard applies to `backend/**/*.py`. Rendered in the format each agent expects. Chapter 6.

Other tools call instructions "rules". `aix rules` is the same command as `aix instructions`.

## Profile
A saved set of choices, in one file: which instructions to enable, which implementation of each skill class, and a
paragraph of routing text for `AGENTS.md`. `aix profile use fastapi-react` switches the whole set. Chapter 6.

## Layer
A folder shaped like `.aix/` whose files replace the kit's at the same path. Four layers, later wins:
kit (`.aix/`) < organisation (`.aix/org/`) < person (`~/.config/aix/`, terminal sessions only) < project
(`.aix/custom/`). A file at the same path replaces, a new path adds, an empty `DISABLED` file in a skill folder
removes. Skills, instructions, profiles, the documentation seed and the pointer texts can all be overlaid. Chapter 7.

## Payload
What `aix install` copies into a project and `aix upgrade` may change later. One list, in
`.aix/scripts/payload.py`, with four modes: owned (the kit's, overwritten on upgrade), merged (`AGENTS.md`,
`config.yaml`: kit text plus your parts), seeded (`docs/`: copied once, never touched again), layer (`org/`,
`custom/`: copied and replaced when the origin has them). Anything not on the list never leaves the kit. Chapter 3.

## Origin
Where a project's kit comes from: the clone of AIX on your machine, or an organisation's fork named with
`--from`. Upgrade follows the origin. `--from-org` and `--from-custom` can point one layer elsewhere. Chapter 7.

## Ground truth
The `docs/` folder. Requirements (`FR-*`, `NFR-*`, `API-*`, `DM-*`), decisions (`ADR-*`), test specifications
(`TS-*`), the vulnerability register (`VUL-*`) and the road map (`TASK-*`). Code carries markers such as
`@implements FR-001`, and `aix docs validate` and `aix docs coverage` check that documents and code agree. Chapter 8.
