---
name: core-which-skill
class: core/which-skill
id: "@acme/which-skill-by-outcome"
version: 1.0.0
description: Ask which skill or flow fits the situation: a router over every installed skill, answering "what should I use for X" or "is there a skill for this".
disable-model-invocation: true
---
# @acme/which-skill-by-outcome

ACME routes by the outcome the user wants, not by the activity.
1. Ask (or infer) the artefact expected: a decision, a document, code, a test, a number.
2. Map: decision → coach/spec skills; document → spec; code → implement; test → testing; number → aix code tools.
3. Offer the two closest with one line each; wait.
