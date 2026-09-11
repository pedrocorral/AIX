---
name: architecture-improve
class: architecture/improve
id: "@acme/improve-by-change-frequency"
version: 1.0.0
description: Scan a code base for architecture improvements (cycles, hubs, shallow modules, clones, dead code), rank them by payoff, and turn the accepted ones into tasks; use on "improve the architecture / tech-debt review".
disable-model-invocation: true
---
# @acme/improve-by-change-frequency

ACME ranks architecture improvements by how often the code changes, not only by the graph.
1. `git log --since=6.months --name-only` → change count per file; join with `aix code graph` hubs/cycles and `aix code style` offenders.
2. Score = changes × findings; the top 5 are the proposal, with the refactor skill each needs.
3. Present; accepted items become tasks; nothing is changed here.
