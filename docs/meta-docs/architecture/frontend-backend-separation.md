---
id: META-ARCH-FEBE
title: Frontend / backend separation
---
# Frontend / backend separation

Two deployable units, one contract. The contract is `docs/requirements/api/` (`API-*`) plus the shared schemas
in `shared/`. Nothing else crosses the line.

## Ownership matrix
| Concern | Backend | Frontend | Notes |
|---|---|---|---|
| Business rules & invariants | **owns** | mirrors for UX only | Frontend checks are hints; backend re-validates everything |
| Input validation | **authoritative** | early feedback | Same schema definition in `shared/` where the stack allows |
| Authentication | issues/verifies tokens & sessions | stores token securely, attaches it | Never trust client-side role claims |
| Authorisation | **owns** (every endpoint) | hides/disables UI | Hidden ≠ protected |
| State | source of truth (persisted) | ephemeral UI state, cache | Cache invalidation follows API semantics (ETags / versions) |
| Rendering | templates only if server-rendered | components | No HTML generation in JSON APIs |
| Secrets | **only here** | none, ever | Public keys/config only |
| Error messages | machine-readable envelope | human text | Map error `code` → i18n string in frontend |

## Contract rules
- One vocabulary: field names on both sides come from `docs/requirements/data-model/field-dictionary.md`; a name not in the dictionary does not exist.
- Every endpoint used by the frontend has an `API-*` doc **before** either side is coded.
- Backward-compatible evolution: add fields, never rename/remove within a major version; breaking → `/v2` (see `api-design.md`).
- The frontend consumes the API through **one** client module (`frontend/src/api/`) generated or hand-written from `API-*`; components never call `fetch` directly.
- Backend never knows frontend routes; frontend never knows table names.

## Server-rendered apps (single deployable)
Still separate *logically*: `backend/app/<domain>/views/` (templates + view-models) vs controllers/services.
Templates receive view-models (plain dicts/DTOs), not ORM entities.

## Data-science / AI apps
Dashboards (Streamlit/Dash/Gradio) count as **frontend** even when in Python; they call services through the same
API or an in-process facade in `backend/app/<domain>/facade.py` — never repositories or the DB directly.
