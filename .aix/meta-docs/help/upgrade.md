aix upgrade [PROJECT] [--dry-run] [--yes] [--from-org SRC] [--from-custom SRC]   (experimental)

Brings a project created with `aix install --into` up to the kit version of the `aix` you run. Run the KIT's aix
(the one on PATH) from inside the project; the project's own copy refuses, because the newest logic must come
from the kit. Ownership decides what happens:
  kit-owned, overwritten, removed if gone from the kit:
                 .aix/scripts, .aix/bin, .aix/templates, .aix/meta-docs, .aix/skills/<built-in categories>, CLAUDE.md
  merged:        AGENTS.md and GEMINI.md (kit text + your "## Always-on skills" and "## Project notes"),
                 .aix/config.yaml (your disabled_skills line kept)
  never touched: docs/requirements tests security conflicts operations road-map, .aix/skills/extern/, runtime folders,
                 your code
Prints the full plan, one line per file (line deltas, kept sections, removals), then warns and asks.
  --dry-run      plan only, nothing written        --yes   skip the question (scripts)
Afterwards it relinks skills; run `aix doctor` and `aix docs validate`. Your git history is the backup.
