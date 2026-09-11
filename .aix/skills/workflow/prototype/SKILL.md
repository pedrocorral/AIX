---
name: workflow-prototype
description: Build a throwaway prototype to answer one design question quickly, in isolation from the product code, with the answer and the deletion recorded; use on "can we / sanity-check / spike".
---
# workflow-prototype

Reading budget: the question; nothing in the product code base unless the prototype must call it.

## Procedure
1. Write the question and the observable that answers it (a number, a yes/no, a screenshot).
2. Build in `prototypes/<name>/` (git-ignored or a branch), no requirements, no markers, no tests beyond the observable.
3. Time-box; stop when the observable is measured, not when the code is nice.
4. Record the answer where the decision lives (ADR evidence or the task); then delete the prototype or archive it out of the code roots.
5. Nothing from a prototype is copied into the product without `implement-feature`.

## Outputs
The recorded answer; the prototype gone from the code roots.
