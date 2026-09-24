aix agents [NAME... | all] [--list]          aix install --into DIR --agents claude,copilot

An agent is the tool that reads the files, whatever model it runs: claude (Claude Code, Claude desktop), copilot
(GitHub Copilot in VS Code, the CLI, the cloud agent; alias vscode), cursor, gemini (Gemini CLI, Antigravity),
opencode, codex (reads AGENTS.md only). Each has a skills folder and, for those that do not read AGENTS.md by
themselves, a pointer file:
  claude   .claude/skills/   CLAUDE.md            copilot  .github/skills/  .github/copilot-instructions.md, .github/instructions/
  cursor   .cursor/skills/   .cursor/rules/       gemini   .agents/skills/  GEMINI.md
  opencode .opencode/skills/                      codex    AGENTS.md (always present)
`aix agents` with no names opens the checklist (space toggles, a all, n none, Enter writes, q cancels): agents
detected on PATH or already equipped are preselected; nothing detected = all. Names on the command line set it
without a screen; `all` removes the line. The choice is `agents:` in .aix/config.yaml, kept by aix upgrade.
Install, upgrade and `aix skills` then link folders and write pointer files only for the selected agents; choosing
fewer removes what AIX created for the others (links, its own pointer files, rendered aix-* files), never a file a
person wrote. `aix doctor` reports the selection and leftovers. `aix install --into DIR` asks in a terminal unless
--agents names them; without a terminal all agents are equipped.
Where AIX writes and a person's file or folder already sits (CLAUDE.md, GEMINI.md, .github/skills, ...), it is kept
as `<name>-bak` first. After the selection, the .gitignore lines AIX needs (.aix/, the selected agents' skills
folders, rendered aix-* files, reports) are shown and added on a y/N (`aix install`, `aix upgrade --yes` too).
