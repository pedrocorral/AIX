---
name: spec-review
description: Review FR/API/DM/TS docs for testability, completeness, contradictions and duplication before approval, or on "does this spec make sense".
---
# spec-review
Checklist (report as a table: item / pass·fail / fix):
- Single SHALL statement, no "and/or" bundling; no implementation detail.
- Every AC is Given/When/Then and objectively checkable; error cases and limits present.
- IDs valid and referenced docs exist (`grep -rl "^id: <ID>" docs`).
- No contradiction with other FRs in the domain (grep key nouns in the domain folder) or with ADRs.
- API/DM consistency: fields named identically; error codes in the shared enum.
- NFR impact considered (perf, security, privacy, a11y) — at least a note.
- Glossary terms used consistently.
Output: approved / changes-requested with concrete edits. Never silently edit approved docs.
