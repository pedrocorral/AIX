---
name: refactor-clone
description: Merge duplicated functions reported by `aix code clones` (EXACT groups, NEAR pairs): extract the shared part as a leaf, parametrise the difference, keep one; use on any clone line whose members share a purpose.
---
# refactor-clone
Reading budget: the clone line, the members side by side.

## When NOT to use
The members share a *shape* but not a *purpose* (two adapters of one port, two route handlers for different resources): record "reviewed, intentional" and move on. Never merge across domains.

## Procedure
1. Diff the members: what is identical, what varies (a value, a type, a call).
2. EXACT (only names/literals differ) → keep one, pass the difference as a parameter or a small object; delete the others; re-point callers.
3. NEAR → extract the identical part into a leaf function both call; the varying parts stay in each; if the extracted part needs state from both, it is not a leaf: stop and record.
4. The extracted leaf gets a name that says what it does, a docstring, and a unit test (`testing-write-unit-tests`).
5. `aix code clones` on the folder: the line is gone; `aix code graph --gate` still passes (a new leaf must not create a cycle); tests green.

## Outputs
One implementation, one leaf, clone line gone.

## Hand-off
Progress entry: members merged, the leaf's name, callers re-pointed.
