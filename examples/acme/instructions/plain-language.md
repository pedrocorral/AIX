---
id: acme/plain-language
name: "Plain Language Requirement"
description: "Require the plain-language skill for every Markdown document in an ACME repository: controlled vocabulary, one idea per sentence, glossary-locked terms."
applyTo: "**/*.md"
---
# Plain language requirement
Before writing or editing any Markdown, run the `spec-plain-language` skill (ACME implementation: glossary-locked). Documents that fail its checks are returned in review.
