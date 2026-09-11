---
name: architecture-deep-modules
class: architecture/deep-modules
id: "@acme/deep-modules-by-callers"
version: 1.0.0
description: Design or improve a module as a deep module: small interface, large hidden implementation, no information leakage; use when designing a module, a public API, or fixing a shallow abstraction.
---
# @acme/deep-modules-by-callers

ACME designs interfaces from the callers' code, not from the module.
1. Write the calling code you wish existed, for the three most common callers.
2. Derive the interface from those snippets; anything a caller never needs is not in it.
3. Hide the rest; document one line: "this module decides X, nobody else does".
4. `aix code graph`: the module must be a leaf or depend only downward.
