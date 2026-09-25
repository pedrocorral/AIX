---
name: architecture-trace
description: Trace a repository's live architecture to find who owns a behaviour, what depends on what, the runtime flow and the entry points, with the fewest reads; use on "how does X work", "where is Y decided", onboarding.
---
# architecture-trace

Reading budget: `aix code graph`, `aix code dead`, INDEX files; open at most 5 source files.

## Procedure
1. `aix code graph --report`: entry points, hubs, the folder Q; read the top fan-out list: those are the coordinators.
2. Locate the behaviour: `grep -rn "<keyword>"` limited to `backend frontend shared`; then `core-find-doc` for its FR/API/DM ids.
3. Follow the dependency direction from the entry point to the model: name each layer crossed (controller → service → port → adapter).
4. Write the flow as a numbered list with file:function at each step; mark anything that goes the wrong way (a CUT edit in the report).
5. Record the answer in `docs/operations/` or the ADR that asked for it when it will be asked again.

## Outputs
A ≤ 15-line trace with file:function per step and the ids involved; findings for `refactor-*` if the graph is wrong.
