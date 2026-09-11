---
name: workflow-to-tickets
class: workflow/to-tickets
id: "@acme/tickets-vertical-slices"
version: 1.0.0
description: Break a plan, a spec or the current conversation into tracer-bullet tickets that each deliver a thin end-to-end slice with its acceptance check; use on "make tickets / split this".
disable-model-invocation: true
---
# @acme/tickets-vertical-slices

ACME tickets are vertical slices with a demo.
1. Ticket one: the smallest demo a user could see end to end (a fixed value on screen through the whole stack).
2. Each next ticket: one more user-visible behaviour; a ticket without a demo is split or dropped.
3. Ticket = FR/TS ids, demo script (steps a person follows), size ≤ one day; `aix task new` in order.
