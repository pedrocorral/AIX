---
name: architecture-domain-model
class: architecture/domain-model
id: "@acme/domain-model-event-first"
version: 1.0.0
description: Build and sharpen the project's domain model: terms, entities, relationships, invariants and bounded contexts, recorded in the glossary and DM-* docs; use when terminology is fuzzy or a new domain appears.
---
# @acme/domain-model-event-first

ACME models a domain from its events.
1. List the events the business talks about (OrderPlaced, StockReserved); each names the entity it changes.
2. Entities are the things that own events; values are what events carry; invariants are what an event may not violate.
3. Contexts = groups of events one team owns; relationships between contexts are event subscriptions.
4. DM-* docs from the entities; glossary from the event names; ADR for every contested boundary.
