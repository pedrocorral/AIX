# decisions/ — Architecture Decision Records of the kit
Accepted ADRs are settled; a change needs a superseding ADR. Read this when: asking "why is it like this?". Skip when: the ADR list does not touch your area.

| Path | What | Status |
|---|---|---|
| `ADR-0001-one-positive-payload-list.md` | One positive list of what travels, shared by install, upgrade, manifest and doctor | accepted |
| `ADR-0002-layers-share-one-rule.md` | `.aix/org/` and `.aix/custom/` follow one rule; the fork fills `org/` | accepted |
| `ADR-0003-agents-not-runtimes.md` | The tools are called agents; a project selects which ones it equips | accepted |
| `ADR-0004-ignore-whole-aix.md` | Projects ignore the whole `.aix/` in `.gitignore` | accepted, under discussion |
| `ADR-0005-kit-docs-and-seed-split.md` | `docs/` is the kit's own; projects are seeded from `.aix/templates/docs/`, overlayable by layers | accepted |
| `ADR-0006-seats-for-several-agents.md` | Seats (agent-001 ...) for several agents in one repository; claims, scopes, one state per seat | accepted |
