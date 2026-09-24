aix instructions [list] | info ID | show ID | enable ID | disable ID      (alias: aix rules ...)

Instructions are the second kind of thing a layer ships, next to skills. Two kinds:
  block     `block: true`, `section`, `order` — a section of AGENTS.md itself; `aix install` assembles the file from
            them. The kit's six blocks (aix/agents/*) are the contract; a layer replaces one by id or adds a section.
  scoped    `applyTo` globs (or `always: true`) — a standard rendered natively for Copilot (.github/instructions/)
            and Cursor (.cursor/rules/) and listed in AGENTS.md for every other runtime.
States: active (rendered on the next install), optional (off) (a kit standard such as aix/frameworks/fastapi-backend
that only applies when enabled here or by a profile), disabled (config disabled_instructions), not in profile
(the active profile lists other ids). `enable` / `disable` edit .aix/config.yaml and re-run the install; a profile
(`aix profile use NAME`) switches a whole set at once, and an explicit enable/disable wins over it.
