# conventions/ — formats and habits that make the kit cheap to navigate
Read this when: writing any document or looking for something. Skip when: purely coding inside a known file.

| Path | What | Read when |
|---|---|---|
| `ids-and-traceability.md` | ID scheme (FR/NFR/API/DM/ADR/TS/VUL/TASK), code markers, coverage matrix | Creating any ID; adding markers |
| `document-format.md` | Front-matter, INDEX tables, size limits, naming | Writing or reviewing any doc |
| `token-economy.md` | How to locate information with minimal reads; grep recipes | Whenever you are about to "look around" |
| `readability.md` | Function limits with their evidence (cognitive/cyclomatic complexity, nesting, parameters, lines), naming rules, structure rules; `aix code style` | Writing or reviewing any function |
| `cli.md` | The `aix` CLI: which project it acts on, every command, skill states (recommended/available/always/on-demand/disabled), always-on wiring per runtime, third-party registry | Running any kit command; choosing or activating a skill |
| `org-layer.md` | The organisation layer as a contract for an internal AIX repository: what the repo is, where every kind of organisation content goes, what is kit-owned and never edited, forking or merging the kit into a company repo, the checks before a commit | Working in a repository that holds AIX plus an organisation's own material; `aix help org` |
| `git-and-commits.md` | Branch, commit and PR conventions carrying IDs | Committing |
