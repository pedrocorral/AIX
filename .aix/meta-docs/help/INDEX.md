# help/ — the pages behind `aix help <command>`, `aix` and `aix about`
Read this when: you need the options of one command. Skip when: you want to learn how to do something (`aix guide`).

One Markdown file per command; a sub-command's page is `<group>-<command>.md` (`aix help code graph` reads `code-graph.md`).
A layer (`.aix/org/meta-docs/help/`, `.aix/custom/meta-docs/help/`) overrides a page by placing a file of the same name.

| Path | What | Read when |
|---|---|---|
| `usage.md` | The one-screen usage printed by a bare `aix` (`{n}` is replaced by the skill count) | Never directly: `aix` |
| `about.md` | The long story: what AIX is, the loop, the layers (`aix about`) | Presenting AIX |
| `install.md`, `upgrade.md`, `doctor.md`, `self-install.md` | Getting the kit into a project and keeping it current | Setting up |
| `agent.md`, `agents.md`, `policy.md`, `profile.md`, `instructions.md`, `skills.md`, `task.md`, `guide.md`, `help.md`, `version.md` | The project commands | Daily use |
| `code.md`, `code-find.md`, `code-graph.md`, `code-style.md`, `code-stats.md`, `code-security.md`, `code-vulnerabilities.md`, `refactor.md` | The code tools and the fix skills | Measuring code |
| `docs.md`, `docs-validate.md`, `docs-coverage.md`, `docs-security.md` | The documentation tools | Closing a task, releasing |
