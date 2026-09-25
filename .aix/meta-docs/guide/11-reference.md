---
id: META-GUIDE-REFERENCE
title: Command reference
---
# 11. Command reference

Words are commands, dashes are modifiers. `aix help <command>` prints the details of one.

## The kit
| Command | Does |
|---|---|
| `aix self-install [--dry-run] [--no-profile]` | Make `aix` callable from any terminal (link in `~/.local/bin`, PATH line in your shell profiles, verification). Alias `aix install aix` |
| `aix self-update` | Pull the clone; then `aix upgrade` each project |
| `aix self-test [NAME...] [--network] [-q]` | The kit's own test suite, from the clone |
| `aix install [--copy]` | Inside a project: relink skills, pointer files, rendered instructions, `.gitignore` check |
| `aix install --into DIR [--from SRC] [--from-org SRC] [--from-custom SRC] [--agents a,b] [--copy] [--replace-all\|--skip-all\|--merge-all]` | Copy the kit into a project and set it up |
| `aix upgrade [PROJECT] [--dry-run] [--yes] [--from-org SRC] [--from-custom SRC]` | Bring a project to the version of the `aix` on PATH |
| `aix doctor` | Health check with a fix per problem |
| `aix newie` (alias `aix for-dummies`) | AIX in one screen: the basics only |
| `aix version`, `aix about`, `aix help [CMD]`, `aix guide [CHAPTER] [--all]` | Versions, the introduction, the help, this guide |

## Choices of a project
| Command | Does |
|---|---|
| `aix agents [NAME...\|all] [--list]` | Which agents the project equips (checklist without names) |
| `aix code find [--list\|--yes]` | Which folders hold code (checklist) |
| `aix agent claim [--force]\|release\|whoami\|list`, `set total N`, `get total`, `set lease 4h`, `get lease` | Seats for several agents in one repository (chapter 12) |
| `aix profile [list\|show NAME\|use NAME\|off]` | Saved sets of instructions and skill choices |
| `aix policy [list\|show NAME\|use NAME\|off]`, `aix check [--step ID] [--task ID]` | The development cycle (chapter 13); `anarchy` = none |
| `aix instructions [list\|info ID\|show ID\|enable ID\|disable ID]` | The instruction files of every layer; alias `aix rules` |
| `aix skills [list\|general\|specific [CATEGORY]]` | The catalogue with states |
| `aix skills info NAME`, `show NAME` | One skill: state, layer, id, alternatives; its text |
| `aix skills use NAME ID`, `use NAME default` | Pin an implementation of a class, or unpin |
| `aix skills enable\|disable NAME...` | Link or unlink everywhere |
| `aix skills always NAME`, `on-demand NAME` | Name it in every session, or not |
| `aix skills registry`, `add NAME... [--always\|--on-demand] [--extra a,b]`, `update [NAME...]`, `remove NAME...` | Third-party skills with evidence |

## The documentation
| Command | Does |
|---|---|
| `aix docs validate` | IDs, links, indexes, front matter, status claims, layers, near-miss names; exit 1 on errors |
| `aix docs coverage` | Regenerate `docs/tests/coverage-matrix.md` |
| `aix docs security [open\|validated] [--gate]` | The vulnerability register's state; the release gate |
| `aix task new "title" \| start ID [--force] \| block ID "reason" \| done ID [--force] \| list` | Move tasks through the road map; `start` signs the task with your seat, `done` runs the cycle's checks first |

## The code
| Command | Does |
|---|---|
| `aix code graph [PATH...] [--functions] [--roles] [--gate] [--max-distance N] [--report] [--selftest]` | The modularity metric; alias `complexity` |
| `aix code dead [PATH...] [--functions] [--gate]` | Unreachable modules and functions |
| `aix code clones [PATH...] [--similarity PCT] [--gate]` | Duplicated functions |
| `aix code style [TARGET...] [--gate] [--all] [--report] [--selftest]` | Readability per function; `FILE:FUNCTION` for one card |
| `aix code stats [PATH...] [--metric lines\|cognitive\|cyclomatic\|nesting\|params] [--report]` | The histogram |
| `aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]` | Static security checks mapped to VUL rows |
| `aix code vulnerabilities [PATH...] [--taint] [--cve] [--history] [--commits N] [--strict] [--gate] [--audit]` | Taint paths, CVEs, secrets in history |

## Files a project owns in `.aix/config.yaml`
`agents`, `paths.code_roots`, `profile`, `instructions`, `disabled_instructions`, `use` (skill pins),
`disabled_skills`, `source`, `source_org`, `source_custom`, `agents_total`, `agents_lease`, `policy`, `style` limits. `aix upgrade` keeps all of them.

## Environment variables
| Variable | Effect |
|---|---|
| `AIX_NO_USER=1` / `AIX_USER=1` | Never / always apply the person layer (`~/.config/aix`) |
| `AIX_USER_DIR` | Another folder for the person layer |
| `AIX_CACHE` | Where git sources are cloned (default `~/.cache/aix/sources`) |
| `CI` | Set by CI systems: no prompts, no checklists, no person layer |
| `AIX_TEST_NETWORK=1` | Lets `aix self-test` run the download tests |
| `AIX_HOST`, `AIX_TOOL` | Override the host name and the tool name a seat records |
