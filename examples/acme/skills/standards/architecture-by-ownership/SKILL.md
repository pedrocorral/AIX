---
name: architecture-trace
class: architecture/trace
id: "@acme/architecture-by-ownership"
version: 1.0.0
description: Trace a repository's live architecture to find who owns a behaviour, what depends on what, the runtime flow and the entry points, with the fewest reads; use on "how does X work", "where is Y decided", onboarding.
---
# @acme/architecture-by-ownership

ACME traces architecture by ownership tables rather than call paths.
1. `aix code graph --report`; list the top fan-out modules: those are the owners.
2. For the behaviour asked: which owner decides it, which adapter executes it, which model records it. One line each.
3. Confirm with one grep per line; no more than three files opened.
4. Answer as a three-row table; record it in `docs/operations/ownership.md` when it will be asked again.
