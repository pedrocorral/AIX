# Dependency graph (generated — do not edit)

```
Dependency graph (modules) — .aix/scripts, tests

  A (the code): nodes 90, edges 156, components 7; 0 re-export facades collapsed
  B (ideal: leaves and composers, arcs downward, no cycle, no hub): nodes 92, arcs 158, depth 5; in A: leaves 20, composers 32, roots 36, hubs 2
  distance A -> B: 2 edits  (cuts: 0 cycle, 0 upward; splits: 2)

  stable nodes (instability <= 0.25) 27; edges into them, free reuse: 108; edges into nodes that change: 48
  cycles 0   upward dependencies 0   hubs 2 (fan-in and fan-out both >= 3)
  propagation cost 3.5 %   NCCD 0.74 (1.0 = balanced binary tree, Lakos)   modularity Q by folder depth 1: 0.31 (2 folders)  depth 2: 0.17 (29 folders)  depth 3: -0.00 (82 folders)

  EDITS (do these and A is B; cuts are defects, splits are design):
  SPLIT  .aix/scripts/cli_install.py  (in 3, out 6): keep the work as a leaf, move the calls to a composer above it
  SPLIT  .aix/scripts/install_skills.py  (in 7, out 6): keep the work as a leaf, move the calls to a composer above it
  fix with: CUT -> skill refactor-cycle; SPLIT -> refactor-hub (aix skills show NAME)
  B does not know: calls A could not resolve (absent from both graphs), and meaning: a SPLIT says where the shape breaks, you decide the cut.
```
