---
id: PRODUCT-GLOSSARY
title: Glossary
status: accepted
---
# Glossary
| Term | Meaning |
|---|---|
| agent | The tool that reads the files, whatever model it runs: claude, copilot, cursor, gemini, opencode, codex |
| skill | A `SKILL.md` folder (agentskills.io) a runtime loads on demand; a `class` names the job, an implementation (`id`) does it |
| instruction | A markdown file agents obey passively: a block of AGENTS.md, or a standard scoped by `applyTo` globs |
| profile | A saved set of choices: router text, instructions, one implementation per class |
| layer | A folder shaped like `.aix/`: kit < organisation (`.aix/org/`) < person (`~/.config/aix/`) < project (`.aix/custom/`) |
| payload | What `aix install` copies into a project (`.aix/scripts/payload.py`): owned, merged, seeded, layer items |
| origin | The kit checkout a project installs or upgrades from (`--from SRC` or the clone on PATH) |
