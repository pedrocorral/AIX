---
name: architecture-deep-modules
description: Design or improve a module as a deep module: small interface, large hidden implementation, no information leakage; use when designing a module, a public API, or fixing a shallow abstraction.
---
# architecture-deep-modules

Reading budget: `references/DEEP-MODULES.md`, `.aix/meta-docs/architecture/modularity.md`.

## Procedure
1. State the module's one job in one sentence; list its callers.
2. Interface: the fewest operations that let callers do their job; defaults over parameters; errors defined out of existence where possible.
3. Implementation hides everything else: formats, ordering, retries, caches. A change inside must not change callers.
4. Design it twice: write two interface sketches, compare on caller code length and on what leaks; keep the better one.
5. Check with `aix code graph`: the module is a leaf or depends only downward; fan-in may be high, fan-out small.
6. Record the interface as the DM/API doc it belongs to.

## Outputs
The interface (types/signatures) and a note on what it hides; callers rewritten if the interface shrank.
