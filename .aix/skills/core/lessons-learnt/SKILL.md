---
name: core-lessons-learnt
description: Record, merge and prune the agents' lessons the moment a user corrects how you work ("don't do X", "I told you", "stop", "never", "always", a wrong assumption or an unrequested action), confirms a non-obvious approach, or says "compact the lessons".
---
# core-lessons-learnt

Reading budget: the index `.aix/custom/skills/core/lessons-learnt-notes/SKILL.md` (always read already), then only the lesson files you change.
The method is here; the content is the project's notes skill `core-lessons-learnt-notes`, one file per lesson under its `lessons/`.

## When NOT to use
- The correction is about what the application must do: a requirement (`spec-write-requirement`) or a conflict (`core-conflict-resolution`).
- It holds for the current task only ("skip the tests this time"): follow it, record nothing.
- You are in the kit checkout (`AIX-DEVELOPMENT.md` at the root): it holds no notes; a wrong kit skill is fixed in the skill.

## Procedure
1. **Recognise.** The user corrected your behaviour (an assumption, an action nobody asked for, a habit, a format) in a way that should hold in later sessions, or confirmed an approach you would not have chosen by default.
2. **Propose, then write.** Say the lesson in one line, `Lesson: <rule>. Record it?`, and write only on yes. Recording without asking is itself an unrequested action.
3. **Look for the same lesson.** Read the index. A lesson about the same behaviour: update that file (sharpen the rule, add the new case to *Why*) instead of a new one. A lesson that contradicts it: ask the user which holds; never keep both.
4. **Write** `lessons/<kebab-slug>.md` in the notes folder:
   ```
   ---
   rule: "One imperative sentence, at most 25 words, double-quoted."
   author: <git config user.email, or the name the user gave>
   scope: project            # project: everyone working here; person: this author's preference
   updated: YYYY-MM-DD
   ---
   **Why:** what happened, with the absolute date (two lines at most).
   **How to apply:** when it triggers, what to do instead, the edge where it stops applying.
   ```
5. **Index and apply.** `aix lessons index`, then `aix lessons check` (0 problems). Apply the lesson from this answer on.

## Maintenance: merge, prune, compact
Run it when the index passes 15 lines, when `aix lessons check` reports the cap (20), or on "compact the lessons". Show the user the plan (which files merge, which go) and wait for yes.
6. **Merge** lessons that are one behaviour seen twice into one file with the more general rule; keep both cases in *Why*, condensed; delete the other file.
7. **Prune** a lesson the user withdrew, one the tools or the workflow made obsolete, and one now written in a document (step 9).
8. **Compact** every kept file: rule one sentence, *Why* two lines, *How to apply* three. Then step 5.

## Promotion: when a lesson is bigger than a lesson
9. A lesson that recurs, applies to all the work of the project, or needs more than three lines is a missing rule, not a habit. Recommend writing it where it belongs, one line, and ask:
   - how the code or the architecture must be: a requirement or NFR (`spec-write-requirement`), an ADR (`spec-write-adr`);
   - how to operate or release: `docs/operations/`;
   - a standard for some files: a project instruction in `.aix/custom/instructions/` (`.aix/meta-docs/conventions/org-layer.md`, same shapes);
   - a kit skill that told you to do the corrected thing: say so, and propose the fix upstream to the kit.
   After the document exists, delete the lesson (step 7): the document is the source now.

## Outputs
Lesson files added, merged or deleted; the regenerated index; `aix lessons check` clean.

## Hand-off
Name the lessons touched in the task report (`lessons: +1 <slug>`); `core-session-handoff` as usual.
