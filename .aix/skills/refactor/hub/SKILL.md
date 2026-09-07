---
name: refactor-hub
description: Split a HUB reported by `aix code graph` (fan-in ≥ 3 and fan-out ≥ 3, not a composition root): keep the stable part as a leaf, move the rest up; use on any HUB line not labelled "by design".
---
# refactor-hub
Reading budget: the HUB line, the hub file, `aix skills show refactor-cycle` if a cycle is involved.

## When NOT to use
The hub is labelled "composition root: a hub by design", or it is `main`/`app`/`index`.

## Procedure
1. List the hub's exports and who imports each (`grep -rn "from .*<hub> import\|import <hub>"`).
2. Partition the exports: **stable** (pure functions, types, constants: no upward dependency) vs **behaviour** (touches state, I/O, other domains).
3. Move the stable set into a leaf module (`<name>_types.py` / `<name>/core.ts`), keep the name of every symbol; update the imports of the callers that only needed the stable set.
4. The behaviour set stays, or moves up into its single real caller when there is one. Never split by size: split by stability.
5. `aix code graph`: the HUB line is gone or now has fan-out < 3; no new cycle/shortcut. Tests of the callers' domains.

## Outputs
A leaf module with the stable part, the hub shrunk, report lines before/after.

## Hand-off
Progress entry: the partition (what went to the leaf), callers re-pointed.
