---
id: META-CONV-ORG-LAYER
title: "The organisation layer: the contract for an internal AIX repository"
---
# The organisation layer: the contract for an internal AIX repository

**If you are an agent working in a repository that contains AIX and an organisation's own material, read this
page before touching anything.** It says what the repository is, where each kind of organisation content goes,
what you must never edit, and how to prove a change is right. `aix help org` prints a summary.

## 1. What this repository is

An internal AIX repository is the upstream kit (`pedrocorral/AIX`) plus one organisation layer. The kit lives in
`.aix/` and is kit-owned: `aix upgrade` and upstream merges overwrite it. The organisation lives in `.aix/org/`,
a folder shaped like `.aix/`, and upstream keeps that folder empty, so merges never conflict there. Projects
install from this repository (`aix install --into my-app --from <this repo path or git url>`) and receive the kit
and the organisation together; `aix upgrade` run from this repository refreshes both in every project.

There are four layers, later wins, and this page is about the second:

| Layer | Where | Who | Reaches projects |
|---|---|---|---|
| kit | `.aix/` | upstream AIX | install, upgrade |
| organisation | `.aix/org/` | the organisation, in this repository | install (copied), upgrade (replaced) |
| person | `~/.config/aix/` | one developer, terminal sessions only | never committed |
| project | `.aix/custom/` in a project | that project | committed with it |

On upgrade the two layers a source can carry are refreshed differently, by owner (ADR-0008): a project's `.aix/org/`
is replaced whole, because this repository is its only author, so a hand edit there is lost; a project's
`.aix/custom/` is merged, because the project writes it (its lessons included). Never ship lessons in `.aix/org/`:
a lesson the whole organisation needs is a skill or an instruction (section 3).

`examples/acme/` in the kit is a complete fictional organisation layer (37 skills, 8 instructions, 2 profiles): copy
its shapes, not its content.

## 2. The one rule: same path replaces, new path adds, `DISABLED` removes

A file in `.aix/org/` at the same relative path as a kit file replaces it. A new path adds. An empty file named
`DISABLED` inside a skill folder removes that skill class. Names match character by character: `coach/grill_me`
does not replace `coach/grill-me`, it adds a second skill; `aix doctor` and `aix docs validate` report every
layer file that overrides nothing, as an error when it is one edit away from a kit name.

## 3. Where each kind of content goes

| You want to | Put it at | Shape |
|---|---|---|
| Replace how a skill is done | `.aix/org/skills/<category>/<name>/SKILL.md` | front matter `name:` (the class flat name, e.g. `implement-tdd`), `class:` (`implement/tdd`), `id:` (`"@org/…"`), `version:`, `description:` (when it fires; keep the kit's meaning) |
| Add a skill the kit lacks | same, a new `<category>/<name>` | same front matter, a new class |
| Offer a second implementation next to the kit's | `.aix/org/skills/<category>/<name>/@org-variant/SKILL.md` | chosen per project with `use: {class: "@org/id"}` in config or a profile |
| Remove a kit skill for everyone | `.aix/org/skills/<category>/<name>/DISABLED` | empty file |
| Change a block of AGENTS.md | `.aix/org/instructions/<file>.md` with `id: aix/agents/<block>`, `block: true`, `section:`, `order:` | the kit's blocks are `.aix/instructions/agents/*.md`; same id replaces, new id adds a section |
| Add a standard that applies to some files | `.aix/org/instructions/<file>.md` with `id: org/<name>`, `description:`, `applyTo: "glob,glob"` (or `always: true`) | rendered per agent runtime; the description is what makes the agent open it |
| Add text every project's AGENTS.md carries | `.aix/org/AGENTS.md` | a fragment, merged into the managed section |
| Save a set of choices (instructions on, skill implementations) | `.aix/org/profiles/<name>.yaml` | `description:`, `router:`, `instructions: [ids]`, `skills: {class: "@org/id"}`; a project picks it with `aix profile use <name>` |
| Define or replace a development cycle | `.aix/org/policies/<name>.yaml` | `description:`, `order: [steps]`, `required:`, `advised:`; steps are the kit's (`aix help policy`) |
| Make a policy the default for every project | `.aix/org/defaults.yaml` | `policy: <name>` |
| Change a help page (`aix help X`) | `.aix/org/meta-docs/help/<X>.md` | whole page; the layer's copy wins |
| Change a chapter of the guide or a meta-doc | `.aix/org/meta-docs/<same path>` | whole file; the layer's copy wins |
| Seed a document into every new project | `.aix/org/templates/docs/<path under docs/>` | overlaid on the kit's seed at install, file by file; never touched by upgrade |
| Change the pointer files (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) | `.aix/org/templates/pointers/<file>` | whole file; must start with "Read and follow `AGENTS.md`" so AIX still recognises it as its own |

Everything else the kit ships, `.aix/scripts/`, `.aix/bin/`, `.aix/templates/*.md`, `.aix/policies/`,
`.aix/skills/`, `.aix/instructions/`, `.aix/meta-docs/`, is kit-owned. Do not edit it here: the next upstream merge
or `aix upgrade` overwrites it, and `aix doctor` reports the local edit as drift until then. When the kit's behaviour
is wrong for the organisation, override it through the table above; when it is wrong for everyone, change it
upstream in a pull request to `pedrocorral/AIX`.

## 4. Bringing the kit into an existing company repository

Two ways, both keep the rule above:

- **Fork** (simplest): fork `pedrocorral/AIX`, fill `.aix/org/`, commit. Upstream releases arrive with
  `git fetch upstream && git merge upstream/main`; conflicts can only appear in kit-owned files you should not have
  edited, take upstream's side there.
- **Merge into a repository that already exists**: add upstream as a remote and merge it once with
  `git merge --allow-unrelated-histories upstream/main` (or `git subtree add --prefix=aix upstream main` to keep it
  in a sub-folder, then run the kit's `aix` from that folder). The organisation content goes in `.aix/org/` of that
  checkout exactly as in a fork; later releases merge the same way.

After either: `aix doctor`, `aix docs validate`, `aix self-test`; then a test project:
`aix install --into /tmp/probe --from . && cd /tmp/probe && aix doctor && aix skills info <a-class>`, and
`aix skills info` names the layer that won for every class you replaced.

## 5. What the organisation layer must not do

- No secrets, tokens or internal URLs in skills or instructions: every project receives these files and
  `aix code security` scans them.
- No edits to kit-owned files (section 3); no renaming of kit classes (a class name is what the runtimes link).
- No person-specific material: that is `~/.config/aix/`, never committed.
- No project-specific material: that is `.aix/custom/` in the project.
- Keep `.aix/org/` free of generated files (`index.json`, links, caches): `aix install` produces them in projects.

## 6. Checks before a commit to this repository

```bash
aix doctor && aix docs validate && aix self-test
```

`aix doctor` names every override and its layer, and any layer file that overrides nothing. `aix docs validate`
checks the layer's front matter (ids, descriptions, class names) and the near-miss rule. `aix self-test` proves the
kit still works from this checkout. A change to `.aix/org/` reaches every project at its next `aix upgrade` run from
this repository, so those three are the release gate of the organisation.

Related: `guide/07-organisation.md` (the same model told for a person rolling AIX out), `AIX-DEVELOPMENT.md` §11-12
(the design and its precedents), `aix help install`, `aix help upgrade`, `aix help profile`, `aix help policy`.
