---
name: refactor-dead
description: Delete dead code reported by `aix code dead` (DEAD MODULE / DEAD FUNCTION) after proving nothing reaches it by string, reflection or a framework; use on any dead-code candidate.
---
# refactor-dead
Reading budget: the DEAD lines, `grep` results for each name, the entry-module list in the report.

## When NOT to use
The candidate is a public API of a library (exported for others), a plugin/hook looked up by name, a migration, or a fixture registered by a framework: prove it and record it, do not delete.

## Procedure
1. For each candidate: `grep -rn "<simple name>"` across the project **including** config, templates, YAML/JSON, tests and docs. A hit in a string ("handlers": ["cleanup_expired"]) means live.
2. Check framework registration: decorators, `__all__`, entry points in `pyproject`/`package.json`, URL/route tables, DI containers, `getattr`/`import_module` with variables.
3. Truly dead → delete the function or file, its tests, and its INDEX/docs rows; a port method with no caller is unfinished design, ask before deleting.
4. Run the full test suite; `aix code dead` again: the line is gone and no new candidate appeared (deleting a caller can orphan its callee: repeat).
5. If `@implements`/`@tests` markers were deleted, `aix docs validate` must still pass (status drift).

## Outputs
Deleted code, green tests, report clean or with recorded exceptions.

## Hand-off
Progress entry: what was deleted with the grep evidence; exceptions kept and why.
