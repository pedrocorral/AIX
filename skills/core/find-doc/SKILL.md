---
name: core-find-doc
description: Locate a doc, requirement, test spec, VUL row, task or code file with the fewest reads; use before listing directories or reading several files for context, or on "where is / do we have a spec for".
---
# core-find-doc

Reference: `docs/meta-docs/conventions/token-economy.md`.

## Procedure (stop at the first hit)
1. Known ID → `grep -rl "^id: <ID>" docs` (docs) or `grep -rn "@implements <ID>\|@tests <ID>" backend frontend shared` (code).
2. Known area → open only that folder's `INDEX.md` (`docs/<area>/INDEX.md`), pick the row, open the file.
3. Keywords → `grep -rli "<kw1>\|<kw2>" docs/requirements docs/tests --include=INDEX.md` first; then non-INDEX files only in the matching folder.
4. Code → guess the path from `docs/meta-docs/architecture/project-layout.md` (`backend/app/<domain>/<layer>/`), `ls` that single folder.
5. Still nothing → tell the user what does not exist yet and propose the skill that creates it (`spec-write-requirement`, `testing-plan-tests`, …).

## Never
`ls -R`, `find .` without a path filter, reading whole `coverage-matrix.md` or `vulnerability-register.md` (grep the ID/category row instead).
