---
name: debug-merge-conflicts
description: Resolve an in-progress git merge or rebase conflict file by file, keeping both intents and proving the result with the tests; use when git reports conflicts.
---
# debug-merge-conflicts

Reading budget: `git status`, the conflicted files, the two commit messages involved.

## Procedure
1. `git status`; for each conflicted file read both sides' intent from `git log -1 --format=%s <ours> <theirs>`.
2. Resolve hunk by hunk: keep both behaviours when they are compatible; when they are not, stop and ask which wins (`core-conflict-resolution` if a requirement decides it).
3. Never resolve by taking a whole side blindly; never leave markers (`grep -rn "^<<<<<<<"`).
4. Run the tests of the touched domains; `aix docs validate` if docs conflicted.
5. `git add` the files, continue the merge/rebase; write what was decided in the commit message.

## Outputs
A clean tree, green tests, a commit message naming the decisions.
