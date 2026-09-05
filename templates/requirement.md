---
id: FR-DOMAIN-000
title: Short imperative title
type: functional            # functional | non-functional
status: draft               # draft | approved | implemented | verified | superseded
priority: must              # must | should | could
domain: DOMAIN
depends_on: []
related: []                 # API-*, DM-*, ADR-*, VUL-*
tests: []                   # TS-* (filled by testing-plan-tests)
---
# FR-DOMAIN-000 — Title

## Statement
The system SHALL … (one sentence, testable, no implementation detail).

## Rationale
Why this exists (business/user value). One paragraph max.

## Acceptance criteria
- AC1: Given … when … then …
- AC2: …

## Actors & permissions
- who may trigger it; what role/ownership is required

## Constraints & edge cases
- …

## Data & privacy
- PII touched? retention? (link DM-*)

## Security & observability notes
- VUL-* categories likely affected; events/metrics to emit

## Out of scope
- …
