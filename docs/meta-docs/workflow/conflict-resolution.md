---
id: META-WORKFLOW-CONFLICT
title: Conflict resolution — code vs requirements (and spec vs spec)
---
# Conflict resolution

**Default ruling: requirements win.** Code that deviates is a defect. But the user decides; the agent never does.

## Detection triggers
- A test derived from a requirement fails against existing code that "works".
- Implementing FR-X would break behaviour users rely on but no FR describes.
- Two requirements contradict each other, or a requirement contradicts an ADR.
- Code contains behaviour with no `@implements` marker and no matching requirement.

## Protocol (skill `core-conflict-resolution`)
1. **Freeze & record.** Do not change code or docs. Create `docs/conflicts/open/CONFLICT-NNNN-<title>.md` (template `templates/conflict.md`); its `affects:` scope is frozen for all agents.
2. **Isolate.** Write the conflict as a 3-column diff:

   | Requirement says | Code does | Impact if we follow the requirement |
   |---|---|---|

   Cite IDs and file:line. Keep it under 15 lines.
3. **Options.** Always exactly these three, plus optional others:
   - A. Change code to match requirement (default).
   - B. Change requirement to match code (must justify; produces an ADR).
   - C. Split: new requirement for the new behaviour, keep both.
4. **Ask the user.** Present the table + options. Stop the turn. Do not proceed on assumptions.
5. **Record.** Whatever is chosen → `docs/requirements/decisions/ADR-NNNN-*.md` (template `templates/adr.md`),
   status `accepted`, `affects:` lists the FR/TS/files. Update the affected FR (`status`, text) and TS.
   Fill *Human decision* + *Resolution evidence* in the conflict record, set `status: resolved`, `adr:`, move it to `docs/conflicts/resolved/`, update both INDEX files.
6. **Resume** the task; add a line to its progress log referencing the ADR.

## Spec-vs-spec contradictions
Same protocol; option set becomes: keep A / keep B / merge. The ADR supersedes or amends one of them.

## Anti-patterns
- Quietly adding a `TODO` and moving on.
- Editing the acceptance criteria "to make the test pass".
- Asking the user a vague question ("is this ok?") instead of the 3-column table.
