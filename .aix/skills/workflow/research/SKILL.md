---
name: workflow-research
description: Investigate a question against primary, high-trust sources and record the findings with citations in a Markdown note that a decision can cite; use on "research / find out / what does the spec say".
---
# workflow-research

Reading budget: primary sources first (specification, official docs, the source code of the library); ≤ 3 secondary sources.

## Procedure
1. State the question and what decision depends on the answer.
2. Sources in this order: the standard or RFC, the vendor's documentation for the pinned version, the library source, then reputable secondary. Blog posts are hints, not evidence.
3. For each finding: claim, source (URL or file:line), date/version, confidence.
4. Contradictions between sources are findings too; say which is newer or more authoritative.
5. Write `docs/operations/research/<topic>.md` (or the ADR's evidence section) with the table and a two-line answer at the top.

## Outputs
The note with citations; the answer in ≤ 3 lines for the caller.
