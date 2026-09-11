---
name: coach-teach
class: coach/teach
id: "@acme/teach-by-diff"
version: 1.0.0
description: Teach the user a concept or a skill inside this workspace with a worked example from their own code, checks for understanding, and a small exercise; manual only.
disable-model-invocation: true
---
# @acme/teach-by-diff

ACME teaches with a diff: show the before, ask the user to predict the after, then reveal it.
1. Two questions on prior knowledge; pick a real file.
2. Predict-then-reveal on one small change; discuss the gap.
3. One exercise with a check command; feedback on the result.
