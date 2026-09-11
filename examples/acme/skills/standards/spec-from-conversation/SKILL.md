---
name: spec-write-requirement
class: spec/write-requirement
id: "@acme/spec-from-conversation"
version: 1.0.0
description: Write or update FR/NFR/API/DM docs (ground truth) when a behaviour has no requirement, the user describes a need, vibe-coding needs a draft, or an ADR changes behaviour.
disable-model-invocation: true
---
# @acme/spec-from-conversation

ACME turns a conversation into a requirement without inventing anything; manual because it writes ground truth.
1. Extract every sentence that states a behaviour; each becomes an acceptance criterion in the user's words.
2. Anything the conversation did not decide becomes a question, not a default.
3. Fill `.aix/templates/requirement.md`; actors, data, security rows from the questions answered; status draft.
4. Read it back to the user in ≤ 10 lines; only then `status: approved`.
