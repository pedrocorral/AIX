aix skills [list|general|specific [category]] | info NAME | show NAME | enable|disable NAME...
           | registry [general|specific] | add NAME... [--on-demand|--always] [--extra a,b] | remove NAME... | update [NAME...]
           | always NAME | on-demand NAME | use NAME ID | use NAME default

Catalogue: SKILL, STATE, DESCRIPTION (cut at the terminal width). States:
  recommended / available   known in .aix/skills/extern/registry.json, not downloaded (listed first)
  (*) always                named in AGENTS.md: applied in every session
  on-demand                 installed; invoked by name, by an orchestrator, or when its description matches
  disabled                  listed in .aix/config.yaml disabled_skills; linked into no runtime
Groups (filters): general = behaviour that applies to every session (style, method); specific = one job.
  info      group, level (always/orchestrator/on-demand), category, runtimes it is linked into, source
  add       download a registry skill (GitHub tarball, no git) into .aix/skills/extern/NAME. An entry with a
            `class` (aix skills registry shows it) becomes that kit class's implementation, selected at once
            (`use:` in config; `aix skills use CLASS default` returns to the kit's); one without keeps its bare
            name and is linked everywhere; general skills become always-on unless --on-demand; --extra adds
            siblings from the repo
  always    write the "## Always-on skills" section into AGENTS.md, .github/copilot-instructions.md,
            .cursor/rules/aix.mdc and GEMINI.md (no runtime has an always-apply switch; the instruction files are
            the only mechanism every tool honours); on-demand removes it
  registry  the known third-party skills with their evidence line (only entries with evidence belong there)

Overrides (layers, AIX-DEVELOPMENT.md §11-12): a skill folder at the same class path in .aix/custom/skills/
(this project, committed) or ~/.config/aix/skills/ (you; applied only in a terminal session, never in CI, off with
AIX_NO_USER=1, forced with AIX_USER=1, relocated with AIX_USER_DIR) replaces the kit's implementation; a new path
adds a class; an empty DISABLED file in a class folder removes it. The runtime always sees one folder per class.
`aix install` links the winner and writes .aix/index.json (layer, id, version, content hash per class);
`aix skills info NAME` shows layer, id, hash and the copies it shadows; `aix doctor` lists overrides and reports
linked content that changed since the install.
Choosing between implementations of one class: `aix skills use NAME ID` writes  use: {NAME: ID}  into
.aix/config.yaml and relinks (an explicit choice wins over the profile and over layer precedence);
`aix skills use NAME default` removes it. `info` lists the ids on offer.
