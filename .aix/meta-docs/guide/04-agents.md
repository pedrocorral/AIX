---
id: META-GUIDE-AGENTS
title: Agents
---
# 4. Agents

## The list
AIX knows six agents. Each reads a skills folder and, when it does not read `AGENTS.md` by itself, a pointer file
that sends it there.

| Name | Covers | Skills folder | Pointer file |
|---|---|---|---|
| `claude` | Claude Code, Claude desktop | `.claude/skills/` | `CLAUDE.md` |
| `copilot` | GitHub Copilot in VS Code, Copilot CLI, the cloud agent (alias `vscode`) | `.github/skills/` | `.github/copilot-instructions.md`, plus `.github/instructions/` for scoped standards |
| `cursor` | Cursor | `.cursor/skills/` | `.cursor/rules/aix.mdc`, plus `.cursor/rules/` for scoped standards |
| `gemini` | Gemini CLI, Antigravity (alias `antigravity`) | `.agents/skills/` | `GEMINI.md` |
| `opencode` | OpenCode | `.opencode/skills/` | none, it reads `AGENTS.md` |
| `codex` | Codex | none | none, it reads `AGENTS.md` |

`AGENTS.md` is always present; every agent reads it.

## Choosing: `aix agents`
```
aix agents                      a checklist; agents found on your machine are preselected
aix agents claude copilot       set without a screen
aix agents all                  every agent
aix agents --list               show the table, change nothing
aix install --into DIR --agents claude,copilot
```
In the checklist: space toggles, `a` selects all, `n` none, arrows or `j`/`k` move, Enter applies, `q` cancels.

The choice is the line `agents: [claude, copilot]` in `.aix/config.yaml`. No line means all six, which is what a
project has until it chooses. `aix upgrade` keeps the line.

## What changes with the choice
- `aix install` links skills and writes pointer files only for the selected agents, and renders scoped standards
  only for the agents that read them (Copilot files, Cursor rules).
- Choosing fewer agents removes what AIX created for the others: its links, its own pointer files, its rendered
  files. A file a person wrote is never removed; a pointer file you edited is kept.
- `aix doctor` prints the selection and warns when AIX files of a deselected agent remain.
- The `.gitignore` lines follow the selection.

## Detection
The checklist preselects agents whose command is on your PATH (`claude`, `code`, `cursor`, `gemini`, `opencode`,
`codex`) or whose folder already exists in the project. Nothing detected means all preselected.
