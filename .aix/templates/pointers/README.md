# pointers/ — the pointer files agents that do not read AGENTS.md by themselves receive

`CLAUDE.md` (claude), `GEMINI.md` (gemini), `copilot-instructions.md` (`.github/`, copilot), `aix.mdc` (`.cursor/rules/`, cursor). Written by `aix install` for the selected agents when absent. A layer overrides one by placing the same file under its own `templates/pointers/` (`.aix/org/`, `.aix/custom/`); keep the sentence `Read and follow \`AGENTS.md\``, doctor checks for it and it marks the file as AIX's for backups.
