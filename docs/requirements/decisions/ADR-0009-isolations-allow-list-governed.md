---
id: ADR-0009
title: Isolations as a governed allow-list, checked on the kit's own graph
status: proposed   # designed with the user on 2026-10-09; the user accepts it
date: 2026-10-09
supersedes: []
affects: [.aix/scripts/isolations.py, .aix/scripts/isodecl.py, .aix/scripts/isorules.py, .aix/scripts/isogov.py, .aix/scripts/depedges.py, .aix/meta-docs/architecture/isolations.md, AGENTS.md]
---
# ADR-0009 — Isolations as a governed allow-list, checked on the kit's own graph
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
Option 3. The declaration (`docs/requirements/isolations.yaml`) is an **allow-list**: anything not declared is
forbidden. A dot nests a part in its parent; nesting is optional. Inside a family the parent's files use its
parts, a part uses its parent's files, siblings are free until one declares `may_use`; across families the nearest
declared `may_use` decides, a part may only narrow its parent's list, and every isolation entered must expose the
file. The rules are **governed**: the gate fails until an accepted ADR carries the fingerprint of the declaration
and the recorded contracts; `--accept` writes that ADR as proposed and a person accepts it, never an agent.
Before building on the graph, its edges were measured against grimp, dependency-cruiser, cargo-modules and jdeps
(benchmark section 30) and the gaps fixed. Option 2 was dropped: translating an allow-list into import-linter's
forbidden contracts means generating every pair not allowed, regenerated with every new package.
## Consequences
- One declaration for Python, JS/TS, Rust, Java and ABAP; no new dependency.
- AIX proposes the isolations from the code with its defects (cycles, upward edges) left out, so adopting it starts
  from a review, not from a blank file (benchmark section 31: self-consistent on ten real projects).
- Contracts (the exposed files' public names), data boundaries, agent guidance (`--context`), CODEOWNERS and the
  requirements map hang off the same declaration; `aix code affected` reuses the graph for test selection.
- The check is only as good as the graph: an import built from a string at run time is no edge. Unbreakable
  enforcement needs CI, branch protection and a runtime rule outside the repository; the tool makes every change
  to the rules visible and attributed.
