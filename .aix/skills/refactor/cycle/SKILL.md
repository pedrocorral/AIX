---
name: refactor-cycle
description: Break a dependency cycle or an upward dependency reported by `aix code graph` (CYCLE / UPWARD lines); use on any cycle, any import into a composition root, or any lower-layer → higher-layer import.
---
# refactor-cycle
Reading budget: the CYCLE/UPWARD lines, the two files at each end, `.aix/meta-docs/architecture/modularity.md` (rules only).

## When NOT to use
The report shows 0 cycles and 0 upward dependencies. Never "fix" a cycle by a lazy/inline import: that hides it from the tool and keeps the coupling.

## Procedure
1. Name the edge that points the wrong way. In a cycle A ⇄ B, it is the one from the more stable node to the less stable (higher fan-in, lower fan-out). For UPWARD it is the reported edge.
2. Ask what the wrong-way edge actually needs from its target: a type, a function, a value, or behaviour.
   - a type / pure function / value → **extract it into a leaf** module both sides import (`shared/` or the domain's `models/`); nothing else moves.
   - behaviour → **invert the dependency**: define a port (protocol / interface) next to the caller, implement it on the other side, wire it in the composition root.
   - into the composition root (a controller importing `composition.py` for a factory) → move the factory into a `dependencies` module of the caller's layer, or inject it; the composition root is imported only by `main`.
3. Move exactly that; run `aix code graph --gate` on the touched roots. If a new cycle appears you moved too much or in the wrong direction: revert and repeat step 2.
4. Run the tests of both files' domains.

## Outputs
The edge gone, one new leaf or port at most, gate passing, before/after lines of the report.

## Hand-off
Task progress entry: the edge, what was extracted or inverted, the two report lines. `@implements` markers unchanged.
