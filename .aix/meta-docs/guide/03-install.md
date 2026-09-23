---
id: META-GUIDE-INSTALL
title: Installing and upgrading
---
# 3. Installing and upgrading

## Your machine: `aix self-install`
Run once from a clone of the kit. It makes `aix` callable from any terminal:
1. checks Python 3.9 or newer;
2. creates `~/.local/bin` if missing and links `~/.local/bin/aix` to the clone. A file called `aix` that is not
   AIX's is kept as `aix.bak`; a link to another clone is replaced; where symlinks are impossible a small wrapper
   script is written;
3. adds one line to the profile of every shell it finds (`~/.bashrc`, `~/.zshrc`, fish, the macOS login profile)
   unless `~/.local/bin` is already on your PATH. Never twice;
4. checks that the `aix` your PATH resolves is this clone, and tells you if another one comes first.

`--dry-run` shows the plan and writes nothing. `--no-profile` skips step 3. `aix install aix` is the same command.
On Windows it writes `%LOCALAPPDATA%\aix\bin\aix.cmd` and adds that folder to your user PATH.

The one-line installers `install.sh` (Linux, macOS) and `install.ps1` (Windows) clone the kit into a standard place
(`~/.local/share/aix/kit`, `%LOCALAPPDATA%\aix\kit`) and run `self-install`. Rerunning them updates the clone.

`aix self-update` pulls the clone (git, fast-forward only) and reminds you to upgrade your projects.

## A project: `aix install --into DIR`
Copies the payload into `DIR` and sets it up. In order:
1. the kit files (`.aix/`, `AGENTS.md`); an existing item asks `[r]eplace [s]kip [m]erge`, or `--replace-all`,
   `--skip-all`, `--merge-all` answer for you;
2. the layers `org/` and `custom/`, when the origin has them;
3. `docs/`, seeded from `.aix/templates/docs/` when the project has none;
4. the agents: `--agents claude,copilot`, or a checklist in a terminal, or all of them without one;
5. links every skill into the selected agents' folders, writes their pointer files, renders the instructions;
6. `.gitignore`: shows the lines AIX needs and adds them on a y/N;
7. the code folders: `aix code find`'s checklist, or the table without a terminal.

Where AIX is about to write and a file of yours already exists (`CLAUDE.md`, `.github/skills/`), it is kept as
`<name>-bak` first, never a parent folder.

`--copy` copies the skill folders instead of linking them, for filesystems without symlinks.
`--from SRC` installs from an organisation's fork instead of your clone. Chapter 7.

Inside a project, a plain `aix install` relinks everything. Run it after adding or removing a skill by hand.

## Keeping a project current: `aix upgrade`
Run inside the project, it brings the project's kit to the version of the `aix` on your PATH:
- owned items are overwritten, and removed when the kit dropped them;
- `AGENTS.md`, `GEMINI.md`, `CLAUDE.md` and `.aix/config.yaml` are rebuilt from the kit's text plus your parts:
  the managed sections, `## Project notes`, and your config keys (agents, profile, enabled instructions, chosen
  skills, code folders, sources, style limits, disabled skills);
- `docs/` is never touched;
- `org/` and `custom/` are refreshed when their source has them;
- a kit file you edited locally is flagged before it is overwritten;
- a 1.x layout (a root `framework.yaml`) is migrated into `.aix/` first.

`aix upgrade --dry-run` prints the plan and writes nothing. `--yes` skips the questions, including the
`.gitignore` one. `aix version` inside a project names both the project's copy and the kit on PATH, with a hint when
they differ.

## What travels and what stays
The payload list, `.aix/scripts/payload.py`, is the only definition. Owned: `.aix/bin`, `scripts`, `templates`,
`meta-docs`, `instructions`, `profiles`, the skill categories, `skills/INDEX.md`, the registry. Merged: `AGENTS.md`,
`CLAUDE.md`, `GEMINI.md`, `config.yaml`. Seeded: `docs/`. Layer: `org/`, `custom/`. Not on the list, therefore
never copied and never touched: the kit's own `tests/`, `examples/`, developer documentation, changelog, downloaded
skills, your code.

## `.gitignore`
AIX generates per-machine files. `aix install`, `aix upgrade` and `aix agents` show the lines your `.gitignore`
lacks and add them when you say yes: `.aix/`, the selected agents' skills folders, the rendered `aix-*` instruction
files, the reports the code tools write. Lines are appended once under a marker; your lines are never edited.

Note: the whole `.aix/` is ignored, by decision. Every teammate and every CI job therefore runs
`aix install --into .` before the tools work, and `.aix/custom/` and `.aix/org/` are not committed either. The
alternative, ignoring only `.aix/index.json` and `.aix/manifest.json`, is one edit to `gitignore.py`.
