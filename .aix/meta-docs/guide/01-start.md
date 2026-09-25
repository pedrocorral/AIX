---
id: META-GUIDE-START
title: Start here
---
# 1. Start here

## What AIX is
AIX is a spec-driven development kit (SDDK) for building software with coding agents such as Claude Code,
GitHub Copilot, Cursor, Gemini CLI, OpenCode and Codex. In this guide it is simply the kit. It puts into your project the things those agents read: documentation that is the ground truth,
skills (procedures the agent follows on demand), instructions (rules the agent obeys without being asked), and a
command line tool, `aix`, that installs all of it, keeps it up to date and measures your code.

AIX is a folder of files. It needs Python 3.9 or newer and nothing else. It does not run a model and it does not
talk to any service unless you download a third-party skill.

## The three commands
Once, on your machine, from a clone of the kit:

```
git clone https://github.com/pedrocorral/AIX.git ~/AIX
~/AIX/.aix/bin/aix self-install
```

or the one-line form, which clones for you: `curl -fsSL https://raw.githubusercontent.com/pedrocorral/AIX/main/install.sh | sh`.
Open a new terminal. `aix` now works from any folder.

Once, per project:

```
aix install --into my-project
```

This copies the kit into `my-project/.aix/`, seeds `docs/`, asks which agents you use and which folders hold code,
links the skills into the agents' folders, and offers the `.gitignore` lines. Then, at any time:

```
cd my-project
aix doctor
```

tells you whether everything is in place and how to fix what is not.

## The daily loop
1. Open the project in your agent. The agent reads `AGENTS.md` first; it says where everything is.
2. Work as usual. The agent uses the skills when a task matches their description, and obeys the instructions.
3. Before you close a task, run `aix docs validate` (are the documents consistent?) and, when code changed,
   `aix code style` and `aix code graph` (is the code still readable and modular?).
4. When a new version of the kit is out: `aix self-update` on your machine, then `aix upgrade` in each project.

## Where things are
| Path | What |
|---|---|
| `AGENTS.md` | The entry point every agent reads. Assembled by `aix install` from instruction blocks; your own notes go in its `## Project notes` section |
| `docs/` | Your project's documentation: requirements, tests, security, road map. The ground truth |
| `.aix/` | The kit: scripts, skills, instructions, templates, conventions. Do not edit it by hand, `aix upgrade` replaces it |
| `.aix/config.yaml` | Your project's choices: agents, code folders, profile, enabled instructions, chosen skills |
| `.aix/custom/` | Your project's own overrides of anything in the kit |
| `.aix/org/` | Your organisation's overrides, if you installed from an organisation's fork |
| `.claude/`, `.github/`, `.cursor/`, `.agents/`, `.opencode/` | Generated for the selected agents. Links, never edit |

## Getting help
- `aix newie` (or `aix for-dummies`): AIX in one screen, the basics only; `aix newie 2` and `aix newie 3` go one level deeper each.
- `aix` alone or `aix help`: the command overview.
- `aix help <command>`: one command in detail, for example `aix help agents`.
- `aix guide`: this guide; `aix guide <chapter>` opens one chapter, for example `aix guide skills`.
- `aix doctor`: what is wrong and the fix.
