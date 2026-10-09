aix code isolations [PATH...] [--gate] [--report]
                   | --propose [--depth N] [--write [--force]] | --accept | --context PATH|NAME
                   | --codeowners [--write] | --requirements

ISOLATIONS: the named parts of the code (a domain, a layer, a library, a persistence and its implementations), who
may use whom, and what each one exposes. An allow-list: anything not declared is forbidden. The rules live in
docs/requirements/isolations.yaml; an accepted ADR carries their fingerprint, so changing who may use whom is a
person's decision, never a side effect of making a check pass. Design and rules: architecture/isolations.md.

  isolations:
    app:                     {paths: [src/**], exposes: []}
    app.orders:              {paths: [src/orders/**], exposes: [src/orders/api.py], may_use: [app.persistence]}
    app.persistence:         {paths: [src/persistence/**], exposes: [src/persistence/ports.py, src/persistence/factory.py]}
    app.persistence.postgres: {paths: [src/persistence/postgres/**], may_use: []}
  data:
    card: {fields: [card_number, cvv], stays_in: [app.payments], never_to: [logs, http, print]}
  owners: {rules: "@architects"}
  tests: exempt

The rules (a dot nests: app.orders is a part of app)
  a file belongs to the deepest isolation whose paths match it
  a parent's own files use its parts; a part uses its parent's files; siblings are free until one declares may_use
  may_use absent: the parent's list; a top isolation without one may use nothing. A part's list may only narrow
  its parent's, and names everything the part uses outside itself. Naming a part (app.persistence.postgres) enters
  it directly; naming its parent does not reach inside it.
  every isolation entered on the way to a file must expose it (`exposes` absent: everything is visible)

The check (no option) reports, and --gate fails on any of:
  DECLARATION  the file itself: unknown keys, a part outside its parent, a part widening its parent, a file in two
               unrelated isolations, an exposed file that is not the isolation's own or that a part hides
  GOVERNANCE   no accepted ADR carries the fingerprint of the declaration and the recorded contracts
  FORBIDDEN    an import edge no may_use allows
  HIDDEN       an import of a file an isolation it enters does not expose
  UNDECLARED   a code file in no isolation (tests are exempt unless `tests: checked`)
  BREAKING     a recorded contract name removed, or its signature changed so a caller breaks
  DATA         a declared field written outside its stays_in isolations, or reaching a logger, print or an HTTP call
TIGHTEN lines never fail: a may_use entry nothing uses, an exposed file nothing outside uses, contract names not
recorded yet. Edges come from the module graph (aix code graph); Rust's `mod x;` declarations and the bodies of
`#[cfg(test)]` modules are not uses. With no declaration the gate passes and says so.

  --propose          the isolations AIX recommends: one per code root, one part per folder (--depth 2: one level
                     more), may_use = what each part uses today minus the defects (an edge that closes a cycle
                     between parts or points up the layers is left out and listed to fix), exposes = what outside
                     code uses today. --write saves it when there is no declaration (--force replaces one).
  --accept           record the contracts (the public names of every exposed file, per language) in
                     docs/requirements/isolations.contracts.json and write the ADR, status proposed, with the
                     fingerprint, the declaration and what changed. A person sets `status: accepted`; an agent never.
  --context X        for an agent before it edits: X's isolation, what it may use and the only files of them to
                     read, its parts and parent, what it must not use, the contract it keeps, the data rules
  --codeowners       the CODEOWNERS lines (each `owner:` on its paths; `owners: {rules: ...}` on the declaration,
                     the contracts and the decisions); --write puts them in a managed block of the CODEOWNERS file
  --requirements     @implements markers by isolation: a requirement spread over 3+ unrelated isolations, an
                     isolation implementing requirements of 3+ domains (advice)
  --report           also write docs/tests/isolations.md

An agent can still edit any file in the repository. What makes a rule unbreakable is outside it: the gate in CI,
branch protection with code owners on the declaration and the decisions, and a runtime rule that denies the agent
writes to them. aix code isolations makes every change to the rules visible and attributes it to a decision.
Fix a finding with the skill refactor-cycle (move the code, invert the dependency, or go through an exposed file);
declare and evolve the rules with the skill architecture-isolations.
