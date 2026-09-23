---
id: ADR-0003
title: The tools are called agents and a project selects which ones it equips
status: accepted
date: 2026-09-22
supersedes: []
affects: [.aix/scripts/agents.py, install_skills.py]
---
# ADR-0003 — The tools are called agents and a project selects which ones it equips
## Context
The kit called the tools 'runtimes', a word nobody else uses; it also wrote every tool's folders and pointer files into every project, which teams using one tool found noisy.
## Decision
The word is agent (agentskills.io, AGENTS.md, Copilot, Codex say so; 'client' is the formal synonym). `aix agents` selects from a fixed list (claude, copilot, cursor, gemini, opencode, codex); `agents:` in config, no line = all; install writes only the selected agents' folders and pointer files.
## Consequences
Existing projects change nothing until they choose. A deselected agent's AIX files are removed; a person's files never are.
