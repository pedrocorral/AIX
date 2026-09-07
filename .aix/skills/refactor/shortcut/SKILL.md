---
name: refactor-shortcut
description: Remove a SHORTCUT edge from `aix code graph` (A → C also reached via B): a layer skip or a type that should arrive through the intermediate; use on any SHORTCUT line.
---
# refactor-shortcut
Reading budget: the SHORTCUT line (it names the bypass B), the three files A, B, C.

## When NOT to use
A is a composition root or a test (the tool already exempts them). C is stable (edges into stable nodes are free and not reported).

## Procedure
1. Read how A uses C. Three cases:
   - A only needs something B already exposes → **use B's result** and drop the import of C.
   - A needs a *type* from C → the type is a leaf in disguise: move it to a `models/`/`types` module (stable) or make C stable by removing C's own upward dependencies; re-run, the edge stops being counted.
   - A genuinely orchestrates both B and C → A is doing two jobs: split A, or move the C-call into B.
2. Apply one case; `aix code graph` on the folder: the SHORTCUT line must be gone and no new line appear.
3. Tests for A's domain.

## Outputs
One fewer edge, reducible % down, no new cycle or shortcut.

## Hand-off
Progress entry with the removed edge and the case applied.
