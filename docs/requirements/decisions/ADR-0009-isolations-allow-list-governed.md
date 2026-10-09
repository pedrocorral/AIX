---
id: ADR-0009
title: Isolations as governed frontiers, checked on the kit's own graph
status: proposed   # designed with the user on 2026-10-09; the user accepts it
date: 2026-10-09
supersedes: []
affects: [.aix/scripts/isolations.py, .aix/scripts/isodecl.py, .aix/scripts/isorules.py, .aix/scripts/isogov.py, .aix/scripts/depedges.py, .aix/meta-docs/architecture/isolations.md, AGENTS.md]
---
# ADR-0009 — Isolations as governed frontiers, checked on the kit's own graph
## Context
`modularity.md` asks for an acyclic, layered, sparse graph, and `aix code graph` guesses the layers from folder
names; nothing let a project say which of its parts may use which. Mature tools do (import-linter, ArchUnit,
dependency-cruiser, Nx boundaries, Rust's visibility, SAP package interfaces), one per language, each with its
rules in a file the agent being checked can edit. Most are deny-lists: a package added later is unrestricted.
## Options considered
1. Recommend the per-language tools and ship their configuration (backlog item 6).
2. Generate an import-linter file from one declaration for Python, our engine for the rest.
3. One declaration, checked by the kit's own module graph in all five languages, governed by an ADR.
## Decision
Option 3. The declaration (`docs/requirements/isolations.yaml`) names the parts of the code (folders; a dot nests a
part in its parent) and their **frontiers** (decided with the user on 2026-10-09): `"."` accepted limits an
isolation to its top level, an accepted folder opens the way down to it, a rejected one stays closed, and a part may
set its own frontiers inside its parent's. **Everything the frontiers do not limit is allowed**: there is no list of
who may use whom (the first draft's allow-list and `may_use` were removed with point 2). AIX proposes the frontiers
from the deepest folders code reaches today and a person accepts or rejects each one. The rules are **governed**: the gate fails until an accepted ADR carries the fingerprint of the declaration
and the recorded contracts; `--accept` writes that ADR as proposed and a person accepts it, never an agent.
Before building on the graph, its edges were measured against grimp, dependency-cruiser, cargo-modules and jdeps
(benchmark section 30) and the gaps fixed. Option 2 was dropped: import-linter has no frontier contract, and its
forbidden lists would have to be regenerated with every new package.
## Consequences
- One declaration for Python, JS/TS, Rust, Java and ABAP; no new dependency.
- AIX proposes the frontiers from the code, so adopting it starts from a review, not from a blank file (benchmark
  section 31: accepted as proposed, no finding on ten real projects).
- Contracts (the public names the frontiers let through), data boundaries, agent guidance (`--context`), CODEOWNERS and the
  requirements map hang off the same declaration; `aix code affected` reuses the graph for test selection.
- The check is only as good as the graph: an import built from a string at run time is no edge. Unbreakable
  enforcement needs CI, branch protection and a runtime rule outside the repository; the tool makes every change
  to the rules visible and attributed.
## Review by the user (2026-10-09)
| Point | Decision | Answer |
|---|---|---|
| 1 | AIX checks the rules itself (one declaration, five languages, no extra tool) | accepted |
| 2 | The rules list what is allowed, not what is forbidden | rejected: everything the frontiers do not limit is allowed; no matrix for now |
| 3 | Every change to the rules needs a person's approval (ADR fingerprint) | pending |
| 4 | AIX drafts the first rules from the current code (`--propose`) | accepted |

The status stays `proposed` until every point is answered.
