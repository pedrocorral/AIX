---
id: PRODUCT-VISION
title: Vision
status: accepted
---
# Vision
AIX is a spec-driven development kit for coding agents: one `aix` CLI that equips a project with documentation as
ground truth, skills, instructions and measurement tools that Claude Code, Copilot, Cursor, Gemini CLI, OpenCode and
Codex read as files. The kit is a folder of files with no dependency beyond Python; a project vendors it under
`.aix/`, an organisation forks it and fills `.aix/org/`, a person overrides it under `~/.config/aix/`.
Principles: modularity measured against the transitive reduction; navigate, never scan; one positive list of what
travels; everything installable lives inside `.aix/` so a layer can override it.
