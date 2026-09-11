---
name: implement-feature
class: implement/feature
id: "@acme/implement-from-tickets"
version: 1.0.0
description: Implement an approved requirement across layers (model → repository → service → controller/UI) with @implements markers; entry point for any implement/build/add/code request after spec and tests are planned.
disable-model-invocation: true
---
# @acme/implement-from-tickets

ACME implements strictly from an accepted ticket; manual because it changes code.
1. Read the ticket's FR/TS ids and acceptance check; refuse to start without them (`workflow-to-tickets` first).
2. Write the failing test for the acceptance check; commit it (`test(scope): …`).
3. Implement the thinnest slice that passes; `@implements` markers; `aix code style` on each touched file.
4. `aix code graph --gate` on the domain; `aix code security` on the diff.
5. Move the ticket with `aix task done` only when the check passes in CI.
