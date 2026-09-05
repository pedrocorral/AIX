---
id: META-CONV-IDS
title: IDs and traceability
---
# IDs and traceability

## ID scheme (stable, never reused, uppercase)
| Prefix | Pattern | Example | Lives in |
|---|---|---|---|
| FR | `FR-<DOMAIN>-NNN` | `FR-AUTH-003` | `docs/requirements/functional/<domain>/` |
| NFR | `NFR-<CAT>-NNN` (PERF, SEC, A11Y, OBS, OPS, DATA, UX) | `NFR-PERF-001` | `docs/requirements/non-functional/` |
| API | `API-<DOMAIN>-NNN` | `API-AUTH-002` | `docs/requirements/api/<domain>/` |
| DM | `DM-<Entity>` | `DM-User` | `docs/requirements/data-model/` |
| ADR | `ADR-NNNN` | `ADR-0007` | `docs/requirements/decisions/` |
| TS | `TS-<DOMAIN>-NNN` | `TS-AUTH-011` | `docs/tests/<level>/<domain>/` |
| VUL | `VUL-<CAT>-NNN` (INJ, AUTHN, AUTHZ, INPUT, SECRET, DEP, WEB, DATA, LOG, AI, INFRA) | `VUL-INJ-002` | `docs/security/vulnerability-register.md` |
| TASK | `TASK-NNNN` | `TASK-0042` | `docs/road-map/**` |
| CONFLICT | `CONFLICT-NNNN` | `CONFLICT-0003` | `docs/conflicts/{open,resolved}/` |

`<DOMAIN>` = bounded context of the app (AUTH, BILLING, CATALOG…); defined in `docs/requirements/product/glossary.md`.
File name = `<ID>-<kebab-title>.md`. The ID also appears in front-matter `id:` (validator relies on it).

## Code markers (grep-able, language-agnostic comments)
```
# @implements FR-AUTH-003, API-AUTH-002        (top of module/class/function that realises it)
# @tests TS-AUTH-011                           (top of the test function)
# @mitigates VUL-INJ-002                       (at the control that mitigates it)
```
Rules: markers go on the *narrowest* symbol that fully realises the ID; one marker line may list several IDs;
never mark generic helpers. `aix coverage` scans them (no LLM, no full read), and `aix validate` fails any doc whose status claims `implemented` / `automated` / `mitigated` without the marker in code.

## Traceability chain
`FR/NFR` ─covers─► `TS` ─@tests─► test code; `FR` ─@implements─► code; `VUL` ─@mitigates─► code; `ADR.affects` ─► anything.

## Finding by ID (cheapest possible)
`grep -rln "FR-AUTH-003" docs backend frontend`
