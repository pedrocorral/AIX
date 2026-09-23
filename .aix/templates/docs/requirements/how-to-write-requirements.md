---
id: REQ-GUIDE
title: How to write requirements
---
# How to write requirements
- One requirement = one testable statement ("The system SHALL …"). If you need "and", split.
- Acceptance criteria in Given/When/Then; each AC becomes at least one TS.
- No implementation detail (no table names, no framework names). Those go to ADRs or DM/API docs.
- Priority `must/should/could`; status `draft → approved → implemented → verified` (`verified` = all its TS automated and green) `→ superseded`. Only the user approves.
- Fill *Actors & permissions*, *Data & privacy* and *Security & observability* even with "none" — they seed VUL rows and NFR checks.
- Reference DM/API/NFR IDs in `related:` instead of repeating their content.
- Keep domain vocabulary consistent with `product/glossary.md`; add terms there first.
- Template: `.aix/templates/requirement.md`. Reviewer: skill `spec-review`.
- Field names in DM/API docs come from `data-model/field-dictionary.md` only; add the row first.
