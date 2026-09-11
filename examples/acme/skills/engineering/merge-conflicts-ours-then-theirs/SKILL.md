---
name: debug-merge-conflicts
class: debug/merge-conflicts
id: "@acme/merge-conflicts-ours-then-theirs"
version: 1.0.0
description: Resolve an in-progress git merge or rebase conflict file by file, keeping both intents and proving the result with the tests; use when git reports conflicts.
---
# @acme/merge-conflicts-ours-then-theirs

ACME resolves conflicts in two passes.
1. Pass one: apply *ours* everywhere and run the tests; pass two: re-apply *theirs* hunk by hunk, running the affected tests after each.
2. A hunk whose test fails on both sides is a requirement conflict → `core-conflict-resolution`.
3. No markers left (`grep -rn "^<<<<<<<"`); the commit message lists the hunks where theirs won.
