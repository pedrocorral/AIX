---
id: META-ARCH-ISOLATIONS
title: Isolations — the declared parts of the code and who may use whom
read_when: Declaring or changing the parts of a project, adding an import across parts, reading an isolation finding, or deciding where a persistence implementation, a domain or a library may be used from.
---
# Isolations

`modularity.md` says the graph must be acyclic, layered and sparse. Isolations make that concrete for one project:
the code is split into named parts, and the project declares which part may use which, and which files each part
offers to the others. **An allow-list: anything not declared is forbidden.** The tool is `aix code isolations`
(`aix help code isolations`); the skill is `architecture-isolations`.

## The declaration
`docs/requirements/isolations.yaml`, ground truth like a requirement:

```yaml
isolations:
  app:                      {paths: [src/**], exposes: []}
  app.orders:               {paths: [src/orders/**], exposes: [src/orders/api.py], may_use: [app.persistence]}
  app.persistence:          {paths: [src/persistence/**], exposes: [src/persistence/ports.py, src/persistence/factory.py], may_use: []}
  app.persistence.postgres: {paths: [src/persistence/postgres/**], may_use: []}
  app.persistence.mssql:    {paths: [src/persistence/mssql/**], may_use: []}
data:
  card: {fields: [card_number, cvv], stays_in: [app.payments]}
owners: {rules: "@architects"}
tests: exempt
```

| Key | Meaning |
|---|---|
| `paths` | Globs of the files the isolation holds (`src/orders/**`, `src/main.py`). A file belongs to the deepest isolation holding it. |
| `exposes` | The files other isolations may use: its contract. Absent: every file is visible. `[]`: nothing. |
| `may_use` | The isolations it may use. Absent: its parent's list; a top isolation without one may use nothing. |
| `owner` | Who reviews changes to its files (`--codeowners`). |
| `data` | Fields that carry one kind of data, the isolations allowed to hold them, the sinks they never reach. |

## The rules
A dot nests: `app.persistence.postgres` is a part of `app.persistence`. Nesting is optional; a flat declaration is
the same rules without families.

1. **Inside a family.** A parent's own files use its parts (the factory in `app.persistence` creates the PostgreSQL
   or the MSSQL repository). A part uses its parent's files (the repository implements the ports). Siblings use
   each other freely until one of them declares `may_use`.
2. **Across families.** The nearest isolation, from the user up to the part that meets the other family, that
   declares `may_use` decides; it must name the other part (or a part inside it). A part's list names everything it
   may use outside itself and may only narrow its parent's list, never widen it.
3. **Entering.** Every isolation entered on the way to a file must expose it. `app.orders` may use
   `app.persistence`, so it may import `ports.py` and `factory.py`, never `postgres/repo.py`: persistence does not
   expose it. Naming a part (`may_use: [app.persistence.postgres]`) enters it directly: that is how a composition root
   outside the family would be allowed in, and a person decides it in the declaration.
4. **Tests are exempt** (they exercise internals) unless `tests: checked`. Rust's `mod x;` declarations and the body
   of a `#[cfg(test)]` module are not uses.

## Starting: `--propose`
AIX recommends the isolations from the code: one per code root, a part per folder (`--depth 2` for one level more),
`may_use` = what each part uses today and `exposes` = what outside code uses today, **minus the defects**: an edge
that closes a cycle between parts or points up the layers is left out and listed at the end of the file, so it
fails the check until it is fixed. The draft is the code's own shape with its defects removed, never blessed.
Prune it: every entry removed is a rule the code must then keep.

## Governance: who may change the rules
The check fails until an **accepted ADR** carries the fingerprint of the declaration and the recorded contracts
(`isolations: sha256:...` in its front matter). `--accept` records the contracts and writes the ADR with status
`proposed`, the declaration and what changed; **a person sets `status: accepted`, an agent never does.** So widening a
rule to make a check pass is visible and attributed: the gate fails with GOVERNANCE until someone decides.

What makes it unbreakable is outside the repository, because an agent can edit any file in it: the gate in CI,
branch protection with code owners on the declaration, the contracts and `docs/requirements/decisions/`
(`--codeowners --write`), and a runtime rule that denies the agent writes to them.

## Contracts
The exposed files are a contract. `--accept` records their public names with signatures (Python, JS/TS, Java, Rust,
ABAP). A recorded name removed, or a signature changed so a caller breaks (a new required parameter, a parameter
removed or reordered), is BREAKING. A new optional parameter in Python or JS/TS is compatible; a new name is an
addition, free until the next accept. Breaking a contract on purpose is an ADR, like any rule change.

## Data boundaries
`data:` names the fields that carry one kind of data. A field written in a file of an isolation not in `stays_in`
is DATA; so is a field reaching a logger, `print` or an outbound HTTP call (`never_to`, all three by default),
anywhere. Python follows the value through local assignments; the brace languages read the statement. Name the
fields as the data model does (`field-dictionary.md`); an everyday word (`id`) makes noise.

## For an agent
Before editing: `aix code isolations --context <file>`: what the code there may use, the only files of those parts
to read, what it must not use, the contract it keeps. A FORBIDDEN or HIDDEN finding is fixed in the code (skill
`refactor-cycle`: move the code, invert the dependency, go through an exposed file), never by widening the
declaration. A rule that is wrong is a conflict: record it and ask (`core-conflict-resolution`).

## What it does not know
Edges come from the module graph (benchmark section 30 measures it against grimp, dependency-cruiser,
cargo-modules and jdeps): an import built at run time from a string, a plugin or a framework's container is no edge.
A use through a field's inferred type (Rust) or a bytecode-only signature (Java) is not seen.
