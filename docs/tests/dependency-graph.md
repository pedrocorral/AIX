# Dependency graph (generated — do not edit)

```
Dependency graph (modules) — .aix/scripts, tests

  nodes 83, edges 145, components 7; 0 re-export facades collapsed
  stable nodes (instability <= 0.25) 23; edges into them, free reuse, not counted: 97
  complexity        48 edges (into non-stable nodes)
  ideal complexity  36 edges (transitive reduction: every dependency kept; cycles at their acyclic minimum)
  reducible         33.3 %  (12 edges: 12 shortcuts, 0 cycle edges; wiring from roots/tests exempt: 2)
  cycles 0   upward dependencies 0   hubs 2 (fan-in and fan-out both >= 3)
  propagation cost 3.8 %   NCCD 0.76 (1.0 = balanced binary tree, Lakos)   modularity Q by folder depth 1: 0.30 (2 folders)  depth 2: 0.17 (25 folders)  depth 3: 0.00 (75 folders)

  SHORTCUT  .aix/scripts/aix.py -> .aix/scripts/cli_install.py  also reached via .aix/scripts/cli_instructions.py
  SHORTCUT  .aix/scripts/aix.py -> .aix/scripts/roadmap.py  also reached via .aix/scripts/cli_policy.py
  SHORTCUT  .aix/scripts/cli_install.py -> .aix/scripts/codefind.py  also reached via .aix/scripts/agents.py
  SHORTCUT  .aix/scripts/cli_policy.py -> .aix/scripts/install_skills.py  also reached via .aix/scripts/cli_install.py
  SHORTCUT  .aix/scripts/doctor.py -> .aix/scripts/catalog.py  also reached via .aix/scripts/extern.py
  SHORTCUT  .aix/scripts/doctor.py -> .aix/scripts/install_skills.py  also reached via .aix/scripts/extern.py
  SHORTCUT  .aix/scripts/extern.py -> .aix/scripts/catalog.py  also reached via .aix/scripts/install_skills.py
  SHORTCUT  .aix/scripts/graph.py -> .aix/scripts/graphmetrics.py  also reached via .aix/scripts/deadcode.py
  SHORTCUT  .aix/scripts/skills.py -> .aix/scripts/catalog.py  also reached via .aix/scripts/extern.py
  SHORTCUT  .aix/scripts/skills.py -> .aix/scripts/install_skills.py  also reached via .aix/scripts/extern.py
  SHORTCUT  .aix/scripts/stats.py -> .aix/scripts/stylemetrics.py  also reached via .aix/scripts/style.py
  SHORTCUT  .aix/scripts/vulnerabilities.py -> .aix/scripts/codesecurity.py  also reached via .aix/scripts/secrethistory.py
  HUB       .aix/scripts/install_skills.py  (in 7, out 6)  split it: keep the stable part, move the rest up
  HUB       .aix/scripts/cli_install.py  (in 3, out 6)  split it: keep the stable part, move the rest up
  fix with: CYCLE/UPWARD -> skill refactor-cycle; SHORTCUT -> refactor-shortcut; HUB -> refactor-hub (aix skills show NAME)
```
