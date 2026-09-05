---
name: spec-write-requirement
description: Write or update FR/NFR/API/DM docs (ground truth) when a behaviour has no requirement, the user describes a need, vibe-coding needs a draft, or an ADR changes behaviour.
---
# spec-write-requirement

Inputs: user intent; `docs/requirements/product/glossary.md` (domain codes); `docs/requirements/how-to-write-requirements.md`; existing IDs in the domain folder INDEX. Templates in `templates/`.

## Procedure
1. Identify domain code (create it in the glossary if new; create `functional/<domain>/` + INDEX).
2. Next ID: `grep -rho "FR-<DOMAIN>-[0-9]\{3\}" docs/requirements | sort | tail -1` + 1.
3. Draft from `templates/requirement.md`: one SHALL statement, ACs in Given/When/Then, constraints, out-of-scope; `status: draft`.
4. Field names: every field in an `API-*`/`DM-*` must exist in `docs/requirements/data-model/field-dictionary.md`; add rows first, never invent synonyms.
5. If the requirement implies a boundary or data: draft `API-*` (`templates/api-contract.md`) and/or `DM-*` (`templates/data-model.md`) stubs and link them in `related:`.
6. Add rows to the folder INDEX files. Run `aix validate`.
7. Show the user the statement + ACs only (not the whole file) and ask for approval → set `status: approved`.

## Vibe mode
Statement + 2 ACs, `status: draft`, done in ≤ 10 lines. Upgrade before task close.

## Never
Put implementation details in FRs; change an `approved` FR without `core-conflict-resolution` / ADR.
