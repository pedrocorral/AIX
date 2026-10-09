---
name: architecture-isolations
description: Declare, evolve and respect the project's isolations (frontiers: how deep code may reach into each part; contracts, data boundaries) with `aix code isolations`; use before an import across parts, on any PENDING/HIDDEN/BREAKING/DATA/GOVERNANCE line, or on "how deep may I reach into this".
---
# architecture-isolations
Reading budget: `aix code isolations --context <file>` output; `.aix/meta-docs/architecture/isolations.md` only when declaring or changing rules.

## When NOT to use
Inside one isolation, between files of the same part: the rules do not apply. A cycle or an upward edge with no isolation finding: `refactor-cycle`.

## Inputs
The file or isolation you will change; the task's `scope:`; the check's report lines.

## Procedure
1. **Before editing**: `aix code isolations --context <file>`. From a part with frontiers, read only the files it lists (what the frontiers let through); never open another part's internals to copy from them. Everything the frontiers do not limit is allowed.
2. **Writing code**: import only as deep as step 1 allows. Need something deeper than a frontier? Do not open the frontier yourself. Either use what the frontiers let through, ask the person to open a frontier (a change to the owning part's contract), or stop and record a conflict (`core-conflict-resolution`): the rule may be wrong, a person decides.
3. **After editing**: `aix code isolations --gate` on the touched roots, then `aix code affected --plain` and run those tests.
4. **A finding**:
   - HIDDEN: fix the code with `refactor-cycle` (move the code to the part that owns it, invert the dependency through a port, or go through a file the frontiers let through).
   - BREAKING: restore the old name or signature (add a new one beside it); a deliberate break is a person's decision through `--accept`.
   - DATA: keep the field inside its `stays_in` parts; log or send an id or a masked value instead.
   - UNDECLARED: a new folder needs a place in the declaration: propose it to the person (step 5), do not guess.
   - GOVERNANCE: the rules changed without an accepted ADR. Never set `status: accepted` yourself.
   - PENDING: a proposed frontier waits for a person (`--review`). Never accept or reject a frontier yourself.
5. **Declaring or changing the rules** (only when the user asks): `--propose [--depth 2]` on a project without a declaration, then the user decides each frontier with `--review` (accepting `"."` limits a part to its top level; a rejected folder stays closed). Later, `--propose --write` merges new frontier suggestions in as proposed. `--accept` records the contracts and writes the ADR; the user accepts it. `--codeowners --write` when the isolations name owners.

## Outputs
Code that keeps to the declaration; the gate passing; or a recorded conflict / a proposed ADR waiting for the user.

## Hand-off
Task progress entry: the isolations touched, findings fixed and how, any ADR waiting for acceptance. `refactor-cycle` for the code moves, `core-conflict-resolution` when a rule is wrong.
