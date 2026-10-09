---
id: META-ARCH-ISOLATIONS
title: Isolations — the declared parts of the code and their frontiers
read_when: Declaring or changing the parts of a project, adding an import across parts, reading an isolation finding, or deciding where a persistence implementation, a domain or a library may be used from.
---
# Isolations

`modularity.md` says the graph must be acyclic, layered and sparse. Isolations make that concrete for one project:
the code is split into named parts (folders), and each part declares **frontiers**: how deep code outside it may
reach into it. Everything the frontiers do not limit is allowed. The tool is `aix code isolations`
(`aix help code isolations`); the skill is `architecture-isolations`.

## The declaration
`docs/requirements/isolations.yaml`, ground truth like a requirement:

```yaml
isolations:
  app:                      {paths: [src/**], frontiers: {".": accepted}}
  app.orders:               {paths: [src/orders/**], frontiers: {".": accepted}}
  app.persistence:          {paths: [src/persistence/**], frontiers: {".": accepted, ports/sql: accepted}}
  app.persistence.postgres: {paths: [src/persistence/postgres/**], frontiers: {".": accepted}}
  app.persistence.mssql:    {paths: [src/persistence/mssql/**], frontiers: {".": accepted}}
data:
  card: {fields: [card_number, cvv], stays_in: [app.payments]}
owners: {rules: "@architects"}
tests: exempt
```

| Key | Meaning |
|---|---|
| `paths` | Globs of the files the isolation holds (`src/orders/**`, `src/main.py`). A file belongs to the deepest isolation holding it. Frontiers need one folder path. |
| `frontiers` | Folders of the isolation (`"."` its top level) with a status: `accepted`, `proposed`, `rejected`. How deep outsiders may reach. |
| `owner` | Who reviews changes to its files (`--codeowners`). |
| `data` | Fields that carry one kind of data, the isolations allowed to hold them, the sinks they never reach. |

## Frontiers: how deep outsiders reach
A frontier is a limit, declared per isolation and per level of the tree:

- **`"."` accepted** limits the isolation: code outside it calls its top level only.
- **A folder accepted** (`ports/sql`) opens the way down to it: `ports`, `ports/sql`, and nothing deeper or beside.
- **A folder rejected** stays closed. **No accepted frontier** limits nothing (`"."` rejected keeps it open).
- **Proposed** frontiers are not in force; the check reports them as PENDING until a person decides each one.
- The isolation's **own files reach everything inside it**, except where a part (`app.persistence.postgres`)
  declares its own frontiers: inside an established frontier, a part may set a new one, and it limits everyone
  outside that part, its parent included.

Every isolation entered on the way to a file must let the caller through. The files outsiders may reach are the
isolation's contract.

## Everything else is allowed
There is no list of who may use whom: everything the frontiers do not limit is allowed. A dot nests a part
(`app.persistence.postgres` is a part of `app.persistence`); nesting is optional.

1. **Inside a family.** A parent's own files use its parts as deep as the parts' own frontiers allow (the factory in
   `app.persistence` creates the PostgreSQL or the MSSQL repository). A part uses its parent's files freely (the
   repository implements the ports).
2. **From outside.** `app.orders` may import `ports.py`, `factory.py` and `ports/sql/*` from `app.persistence`, never
   `postgres/repo.py`: persistence's frontiers do not reach `postgres`.
3. **Tests are exempt** (they exercise internals) unless `tests: checked`. Rust's `mod x;` declarations and the body
   of a `#[cfg(test)]` module are not uses.

## Starting: `--propose`
AIX recommends the isolations from the code: one per code root, a part per folder (`--depth 2` for one level more).
Frontiers, deterministically: `"."` for every isolation, plus the deepest folders code outside reaches today, each
`proposed` with its evidence (how many imports reach that deep). A person then decides each one with `--review` (a
terminal checklist: checked accepted, unchecked rejected). Accepted as proposed, the frontiers keep every import
of today (benchmark section 31: no finding on ten real projects); a rejected one closes what the code should not
reach, and the imports that reach it become findings to fix. Run `--propose --write` again later: new frontier
suggestions are merged in as proposed; decided frontiers are never touched.

## Governance: who may change the rules
The check fails until an **accepted ADR** carries the fingerprint of the declaration and the recorded contracts
(`isolations: sha256:...` in its front matter). `--accept` records the contracts and writes the ADR with status
`proposed`, the declaration and what changed; **a person sets `status: accepted`, an agent never does.** So widening a
rule to make a check pass is visible and attributed: the gate fails with GOVERNANCE until someone decides.

What makes it unbreakable is outside the repository, because an agent can edit any file in it: the gate in CI,
branch protection with code owners on the declaration, the contracts and `docs/requirements/decisions/`
(`--codeowners --write`), and a runtime rule that denies the agent writes to them.

## Contracts
The files outsiders may reach are a contract. `--accept` records their public names with signatures (Python, JS/TS, Java, Rust,
ABAP). A recorded name removed, or a signature changed so a caller breaks (a new required parameter, a parameter
removed or reordered), is BREAKING. A new optional parameter in Python or JS/TS is compatible; a new name is an
addition, free until the next accept. Breaking a contract on purpose is an ADR, like any rule change.

## Data boundaries
`data:` names the fields that carry one kind of data. A field written in a file of an isolation not in `stays_in`
is DATA; so is a field reaching a logger, `print` or an outbound HTTP call (`never_to`, all three by default),
anywhere. Python follows the value through local assignments; the brace languages read the statement. Name the
fields as the data model does (`field-dictionary.md`); an everyday word (`id`) makes noise.

## For an agent
Before editing: `aix code isolations --context <file>`: the other isolations' frontiers and the only files of them
it may reach (and read), its own frontiers and the contract it keeps. A HIDDEN finding is fixed in the code (skill
`refactor-cycle`: move the code, invert the dependency, go through a file the frontiers let through), never by
opening a frontier or deciding one: a PENDING frontier is a person's decision. A rule that is wrong is a conflict: record it and ask (`core-conflict-resolution`).

## What it does not know
Edges come from the module graph (benchmark section 30 measures it against grimp, dependency-cruiser,
cargo-modules and jdeps): an import built at run time from a string, a plugin or a framework's container is no edge.
A use through a field's inferred type (Rust) or a bytecode-only signature (Java) is not seen.
