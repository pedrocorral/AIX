---
id: META-CONV-DOCFORMAT
title: Document format
---
# Document format

## Front-matter (YAML, first thing in the file)
Required keys by type are in `.aix/templates/`. Common: `id`, `title`, `status`. Optional: `depends_on`, `related`,
`read_when` (one sentence — used by agents to decide whether to open the file).

## INDEX.md (one per folder, mandatory)
- First line: `# <folder> — one-line purpose`.
- Second line: `Read this when: … Skip when: …`.
- Table `| Path | What | Read when |`. ≤ 40 rows. More → create sub-folders.
- Lists files **and** sub-folders. Nothing unlisted (validator warns).

## Size and shape
- ≤ 300 lines per file; ≤ 12 files per folder. Split by domain, not by date.
- Headings are stable anchors; agents may `grep -n "^## "` to jump. Keep H2 names from the template.
- Prefer tables over prose for enumerations; prose for rationale.
- No duplication: link to the canonical doc by relative path.

## Naming
- Folders: `kebab-case`. Docs: `<ID>-<kebab-title>.md` when an ID exists, else `<kebab-title>.md`.
- Language: English, imperative mood for requirements ("The system SHALL").
