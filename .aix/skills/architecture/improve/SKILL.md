---
name: architecture-improve
description: Scan a code base for architecture improvements (cycles, hubs, shallow modules, clones, dead code), rank them by payoff, and turn the accepted ones into tasks; use on "improve the architecture / tech-debt review".
disable-model-invocation: true
---
# architecture-improve

Reading budget: `aix code graph --report`, `aix code clones`, `aix code dead --functions`, `aix code stats`; open no source file before step 3.

## Procedure
1. Run the four reports; collect candidates: CYCLE/UPWARD (always), HUBs not roots, SHORTCUTs, EXACT clones, DEAD functions, the stats offenders.
2. Rank by payoff ÷ risk: a cycle in a hot module first; a clone in tests last.
3. For the top 5, open the files and write one paragraph each: what is wrong, the refactor skill that fixes it, the blast radius (callers).
4. Present the ranked list; the user accepts or drops each.
5. Accepted items → `core-roadmap-task` (one task per item, `context_files` set); nothing is changed in this skill.

## Outputs
A ranked report (≤ 40 lines) and the tasks created.
