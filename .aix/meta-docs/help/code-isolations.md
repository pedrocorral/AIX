aix code isolations [PATH...] [--gate] [--report]
                   | --propose [--depth N] [--write [--force]] | --review | --accept | --context PATH|NAME
                   | --codeowners [--write] | --requirements

ISOLATIONS: the named parts of the code (a domain, a layer, a library, a persistence and its implementations) and
how deep code outside each part may reach into it: its frontiers. Everything the frontiers do not limit is
allowed. The rules live in docs/requirements/isolations.yaml; an accepted ADR carries their fingerprint, so
changing them is a person's decision, never a side effect of making a check pass. Design: architecture/isolations.md.

  isolations:
    app.orders:               {paths: [src/orders/**], frontiers: {".": accepted}}
    app.persistence:          {paths: [src/persistence/**], frontiers: {".": accepted, ports/sql: accepted, postgres: rejected}}
    app.persistence.postgres: {paths: [src/persistence/postgres/**], frontiers: {".": accepted}}
  data:
    card: {fields: [card_number, cvv], stays_in: [app.payments], never_to: [logs, http, print]}
  owners: {rules: "@architects"}
  tests: exempt

Frontiers (a folder of the isolation, "." its top level; status accepted, proposed or rejected)
  "." accepted        the isolation is limited: code outside calls its top level only
  a folder accepted   opens the way down to it: every folder on the way, that folder, nothing deeper or beside
  a folder rejected   stays closed; a proposed frontier is not in force until a person decides it
  no accepted one     nothing is limited ("." rejected keeps the isolation open)
  A dot nests a part in its parent (app.persistence.postgres). The isolation's own files reach everything inside
  it, except where a part declares its own frontiers: every isolation entered on the way to a file must let the
  caller through. A part uses its parent's files freely. A file belongs to the deepest isolation holding it.

The check (no option) reports, and --gate fails on any of:
  DECLARATION  the file itself: unknown or removed keys, a frontier with a bad status or outside its folder,
               frontiers on an isolation with more than one folder path, a part outside its parent, a file in two
               unrelated isolations
  GOVERNANCE   no accepted ADR carries the fingerprint of the declaration and the recorded contracts
               (or the declaration was deleted and no accepted ADR says `isolations: retired`)
  PENDING      a frontier still proposed: a decision waiting for a person (--review)
  HIDDEN       an import deeper than a frontier allows
  UNDECLARED   a code file in no isolation (tests are exempt unless `tests: checked`)
  BREAKING     a recorded contract name removed, or its signature changed so a caller breaks
  DATA         a declared field written outside its stays_in isolations, or reaching a logger, print or an HTTP call
TIGHTEN lines never fail: an accepted frontier nothing outside reaches that deep, contract names not recorded yet.
Edges come from the module graph (aix code graph); Rust's `mod x;` declarations and the bodies of `#[cfg(test)]`
modules are not uses. With no declaration the gate passes and says so.

  --propose          the isolations AIX recommends: one per code root, one part per folder (--depth 2: one level
                     more); frontiers: "." for every isolation, plus the deepest folders code outside reaches today,
                     all proposed, each with its evidence. --write saves it when there is no declaration (--force
                     replaces one); with a declaration it merges the new frontier suggestions in as proposed and
                     never touches a decided one.
  --review           accept or reject each proposed frontier: a terminal checklist (checked = accepted, unchecked =
                     rejected, q = all stay pending). Without a terminal (CI, an agent) it only lists them.
  --accept           record the contracts (the public names of every file the accepted frontiers let through, per
                     language) in docs/requirements/isolations.contracts.json and write the ADR, status proposed,
                     with the fingerprint, the declaration and what changed. A person sets `status: accepted`.
  --context X        for an agent before it edits: X's isolation, the other isolations' frontiers and the only files
                     of them it may reach (and read), its parts, its own frontiers and contract, the data rules
  --codeowners       the CODEOWNERS lines (each `owner:` on its paths; `owners: {rules: ...}` on the declaration,
                     the contracts and the decisions); --write puts them in a managed block of the CODEOWNERS file
  --requirements     @implements markers by isolation: a requirement spread over 3+ unrelated isolations, an
                     isolation implementing requirements of 3+ domains (advice)
  --report           also write docs/tests/isolations.md

An agent can still edit any file in the repository. What makes a rule unbreakable is outside it: the gate in CI,
branch protection with code owners on the declaration and the decisions, and a runtime rule that denies the agent
writes to them. aix code isolations makes every change to the rules visible and attributes it to a decision.
Fix a HIDDEN finding with the skill refactor-cycle (move the code, invert the dependency, or go through a file the
frontiers let through); declare and evolve the rules with the skill architecture-isolations.
