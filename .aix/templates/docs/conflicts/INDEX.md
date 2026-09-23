# conflicts/ — disagreements between specs, code, tests or observed behaviour, awaiting or holding a human decision
Read this when: session start (anything in `open/` blocks its scope), or the moment you notice a mismatch. Skip when: `open/` is empty and you touch nothing disputed.

| Path | What | Read when |
|---|---|---|
| `open/` | Unresolved `CONFLICT-NNNN` records; their scope is frozen | Session start; before touching listed files |
| `resolved/` | Decided conflicts with the ADR/evidence that closed them | "Why was this decided?" |
| `rules.md` | Lifecycle and what a record must contain | Recording a conflict |

Template: `.aix/templates/conflict.md`. Resolution is recorded as an ADR (`spec-write-adr`); the record moves to `resolved/` with the ADR id.
