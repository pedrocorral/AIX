aix code find [--list | --yes]

Finds the folders that hold code and sets `paths.code_roots` in .aix/config.yaml, the default scope of every
`aix code` command. Candidates: each top-level folder with source files below it (hidden, docs/, .aix/, dependency
and build folders skipped) and the project root itself when files sit directly in it; per candidate: files per
language and the project marker (pyproject.toml, package.json, Cargo.toml, pom.xml, ...). A checklist (curses; plain
prompts where curses is missing) keeps or drops each: space toggles, a all, n none, Enter writes, q cancels. Roots
configured but absent on disk are dropped. --list prints and changes nothing; --yes accepts every suggestion (CI).
`aix install --into DIR` runs the same checklist at the end when a terminal is attached, otherwise prints the list.
While code_roots names nothing that exists, the code tools scan the whole project and say so.
