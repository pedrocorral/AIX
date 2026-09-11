---
name: workflow-to-tickets
description: Break a plan, a spec or the current conversation into tracer-bullet tickets that each deliver a thin end-to-end slice with its acceptance check; use on "make tickets / split this".
disable-model-invocation: true
---
# workflow-to-tickets

Reading budget: the plan or spec; `docs/road-map/pending/next/INDEX.md`.

## Procedure
1. Identify the end-to-end path (UI → API → service → storage); the first ticket walks it with the simplest data ("tracer bullet").
2. Each following ticket adds one behaviour along that path; none is "backend only" or "tests later".
3. Ticket = title (verb + object), FR/TS ids, acceptance check (a command or a test name), dependencies, size ≤ one session.
4. Create them with `aix task new` in `pending/next`, ordered; note blocked ones with `aix task block`.
5. Read the list back: can the first three be started today with no further question? If not, fix the tickets.

## Outputs
TASK-* files in the road-map, each with a check; the INDEX rows.
