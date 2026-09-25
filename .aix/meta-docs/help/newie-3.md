aix newie 3   —   making it yours                       (aix newie 2 for the loop; aix guide for everything)

SKILLS ARE WHAT THE AGENT KNOWS HOW TO DO
  aix skills                the catalogue: always-on (named in AGENTS.md), on-demand, disabled
  aix skills show NAME      the skill's text;  aix skills enable|disable NAME  remembered in .aix/config.yaml
  aix skills registry       third-party skills with evidence;  aix skills add NAME  downloads one into .aix/skills/extern/

INSTRUCTIONS ARE THE STANDARDS
  aix instructions          blocks assembled into AGENTS.md and scoped standards (per file pattern) rendered per agent
  aix instructions enable ID   optional ones, per language or framework (python, typescript, fastapi, react ...)
  aix profile use NAME      a saved set of choices from a layer (which instructions, which skills)

FOUR LAYERS, LATER WINS
  .aix/            the kit: refreshed by aix upgrade, never edited
  .aix/org/        your organisation's fork: skills, instructions, profiles, policies (aix install --from <url>)
  ~/.config/aix/   you, skills only, terminal sessions
  .aix/custom/     this project, committed with it: the same shapes, overriding by name
  A file in a higher layer with the same class or id replaces the lower one; a DISABLED file removes it.

AGENTS AND UPGRADES
  aix agents claude cursor  which tools this project equips: their folders and pointer files, nothing else
  aix upgrade --dry-run     the plan;  aix upgrade  applies it: kit files refreshed, your choices and docs kept
  aix doctor                after either, and whenever something looks wrong

MEASURE BEFORE YOU REASON
  aix code graph            A, the code's dependency graph; B, its ideal shape; the edits between them
  aix code style|dead|clones|security|vulnerabilities|stats     each with --gate, each naming the skill that fixes it
