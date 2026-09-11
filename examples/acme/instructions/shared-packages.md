---
id: acme/shared-packages
name: "Shared Package Boundaries"
description: "Use when creating, changing, extracting or integrating a shared package under packages/ or a Git submodule in an ACME repository."
applyTo: "packages/**,**/*.gitmodules,.gitmodules"
---
# Shared package boundaries
- A package has one public module (`__init__` / `index.ts`) and a `CHANGELOG.md`; internals are private by convention and by lint.
- Dependencies point from applications to packages, never back; `aix code graph --gate` fails on the reverse.
- A package has its own tests and quality gates and passes them in isolation before the monorepo pipeline runs.
- Submodules are pinned by commit; updates are a merge request that names the changelog entries pulled in.
