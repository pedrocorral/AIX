---
name: workflow-wayfinder
class: workflow/wayfinder
id: "@acme/wayfinder-decision-log"
version: 1.0.0
description: Plan a piece of work too large for one session as a shared map of decision tickets that several agents or people can work through in any order; use on "big project / roadmap / multi-session plan".
disable-model-invocation: true
---
# @acme/wayfinder-decision-log

ACME maps big work as a decision log first.
1. Every decision as a row: question, options, deadline, owner, unblocks.
2. Rows ordered by deadline; each becomes an ADR draft when decided.
3. Work tickets only for decided rows; undecided rows are the visible frontier in `docs/road-map/pending/backlog/README.md`.
