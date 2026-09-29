aix help org          the organisation layer: an internal AIX repository and what goes where

An internal AIX repository = the upstream kit in .aix/ (kit-owned, overwritten by upgrades and upstream merges)
plus the organisation's layer in .aix/org/, a folder shaped like .aix/ that upstream keeps empty. Same path
replaces a kit file, a new path adds, an empty DISABLED file in a skill folder removes; names match character by
character (aix doctor reports near-misses). Projects install from the repository with
`aix install --into my-app --from <path or git url>` and get both; `aix upgrade` from it refreshes both.

Where things go (details, shapes and the full table: .aix/meta-docs/conventions/org-layer.md)
  skills/<category>/<name>/SKILL.md      replace or add a skill: name (class flat name), class, id "@org/...", version, description
  skills/.../<name>/DISABLED             remove a kit skill for every project
  instructions/<file>.md                 a block of AGENTS.md (id aix/agents/<block>, block: true) or a scoped standard (applyTo globs)
  AGENTS.md                              a fragment every project's AGENTS.md carries
  profiles/<name>.yaml, policies/<name>.yaml, defaults.yaml (policy: <name>)
  meta-docs/help/<page>.md, meta-docs/...   a help page or any meta-doc, the layer's copy wins
  templates/docs/..., templates/pointers/... documents seeded into new projects; the pointer files' text

Never: edit kit-owned files (.aix/scripts, bin, skills, instructions, meta-docs, policies, templates/*.md); put
secrets, person-specific or project-specific material in the layer. Fix the kit upstream, override it here.

Before committing to the repository:  aix doctor && aix docs validate && aix self-test
