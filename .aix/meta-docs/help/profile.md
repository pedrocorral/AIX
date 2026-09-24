aix profile [list] | show NAME | use NAME | off

A PROFILE is a saved set of customisation choices, shipped by a layer as profiles/<name>.yaml (kit, organisation
`.aix/org/`, or this project's `.aix/custom/`). Choosing one records `profile: NAME` in .aix/config.yaml and re-runs
the install. Keys, all optional:
  description: one line
  router: |               text placed as the "## Organisation" section of AGENTS.md, GEMINI.md and the Copilot pointer
  instructions: [ids]     which scoped instructions apply (others from custom layers are left out; kit ones stay)
  skills:                 class -> implementation id, e.g.  testing/write-unit-tests: "@acme/pytest-tests"
An explicit `use:` entry in config.yaml still wins over the profile for that class.

SKILL CLASSES AND IMPLEMENTATIONS: a skill folder implements a class, named by `class:` in its front matter
(e.g. testing/write-unit-tests) or by its path. `name:` must be the class flat name (runtimes link by it);
`id:` and `version:` name the implementation; `disable-model-invocation: true` makes it manual-only.
Several implementations of one class may coexist across layers; the winner is: config `use:` > profile >
highest layer (project > user > org > kit) > canonical path. `aix skills info CLASS` shows the winner, why, and the
alternatives with the exact `use:` line to switch.

INSTRUCTION BLOCKS: AGENTS.md itself is assembled by `aix install` from instructions marked `block: true` with
`section:` and `order:`; the kit's contract is .aix/instructions/agents/ (header, authority, rules, navigation,
session, output). A layer replaces a block with the same id or adds a section with a new one. Managed sections
(Organisation, Scoped instructions, Always-on skills, Project notes) are kept; write by hand only in Project notes.
Kit instructions with `optional: true` (the FastAPI, React and Kedro stack standards) apply only when a profile or
config `instructions:` names them: kit profiles fastapi-react and kedro do.

SCOPED INSTRUCTIONS: instructions/**/*.md in a layer, front matter `id`, `description`, `applyTo` (comma or list
of globs), `always: true`. Rendered by `aix install` as .github/instructions/aix-<id>.instructions.md (Copilot
native, applyTo), .cursor/rules/aix-<id>.mdc (globs / alwaysApply), and a "## Scoped instructions" section in
AGENTS.md and GEMINI.md that tells every other runtime which file to read when touching matching paths. Generated
files are git-ignored and regenerated; the sources in custom/ are what you commit. The user layer cannot carry
instructions (they would end up in committed files).
