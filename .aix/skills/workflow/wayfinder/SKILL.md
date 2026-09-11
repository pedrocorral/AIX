---
name: workflow-wayfinder
description: Plan a piece of work too large for one session as a shared map of decision tickets that several agents or people can work through in any order; use on "big project / roadmap / multi-session plan".
disable-model-invocation: true
---
# workflow-wayfinder

Reading budget: the vision/product docs, `docs/road-map/INDEX.md`; no code.

## Procedure
1. Name the destination in one sentence and the three constraints that bound it (time, compatibility, risk).
2. List the decisions that must be made before code, each as a ticket: question, options, who decides, what unblocks.
3. Order by dependency, not by preference; mark the critical path.
4. Each decision ticket ends in an ADR (`spec-write-adr`); each work ticket follows `workflow-to-tickets`.
5. Write the map to `docs/road-map/pending/backlog/` with a README that shows the graph as a list of "A before B".
6. Session-safe: any agent can pick the next unblocked ticket from `aix task list` without reading the map twice.

## Outputs
The map README, the decision tickets, the first work tickets.
