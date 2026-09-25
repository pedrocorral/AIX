# Dependency graph (generated — do not edit)

```
Dependency graph (modules) — .aix/scripts, tests

  A (the code): nodes 99, edges 177, components 7; 0 re-export facades collapsed
  B (ideal: leaves and composers, arcs downward, no cycle, no hub): nodes 100, arcs 178, depth 6; in A: leaves 21, composers 38, roots 39, hubs 1
  distance A -> B: 1 edits  (cuts: 0 cycle, 0 upward; splits: 1)

  stable nodes (instability <= 0.25) 30; edges into them, free reuse: 130; edges into nodes that change: 47
  cycles 0   upward dependencies 0   hubs 1 (fan-in and fan-out both >= 3)
  propagation cost 3.0 %   NCCD 0.69 (1.0 = balanced binary tree, Lakos)   modularity Q by folder depth 1: 0.30 (2 folders)  depth 2: 0.16 (31 folders)  depth 3: -0.00 (91 folders)

  EDITS (do these and A is B; cuts are defects, splits are design):
  SPLIT  .aix/scripts/clones.py  (in 3, out 3): keep the work as a leaf, move the calls to a composer above it
  fix with: CUT -> skill refactor-cycle; SPLIT -> refactor-hub (aix skills show NAME)
  B does not know: calls A could not resolve (absent from both graphs), and meaning: a SPLIT says where the shape breaks, you decide the cut.
```
