aix install [--copy] [--into DIR] [--replace-all|--skip-all|--merge-all]

Links every enabled skill from skills/ into the folders each agent runtime reads (.opencode/skills, .claude/skills,
.github/skills, .agents/skills, .cursor/skills), writes the pointer files for Copilot, Cursor and Gemini CLI if
missing, creates docs/road-map/going-on/STATE.md if missing, prunes dangling links, and on Linux/macOS links `aix`
into ~/.local/bin when that folder exists. Idempotent: run it after adding, removing or editing skills.
  --copy         copy skill folders instead of symlinking (filesystems or Windows setups without symlinks)
  --into DIR     first copy the kit payload (.aix/, AGENTS.md, CLAUDE.md, GEMINI.md, the docs/ seed) into an
                 existing project, asking per existing item:
                 [r]eplace (yours kept as <item>.bak)  [s]kip  [m]erge (folders: add missing files only)
                 [R]/[S]/[M] same answer for the rest  [a]bort
  --replace-all | --skip-all | --merge-all   answer every collision without a terminal (CI)
  Layers: .aix/org/ (the organisation's) and .aix/custom/ (local overrides) follow one rule: copied when the origin
                 has the folder, replaced by aix upgrade when it has it, left alone when it does not. The origin is
                 this checkout, or the kit checkout named by --from. So a fork of the kit with a filled .aix/org/
                 installs its organisation into every project, and an edit there reaches projects at the next upgrade.
  --from SOURCE  (with --into) a path or git URL. A kit checkout (has .aix/): its .aix/ is the payload and its
                 .aix/org/ and .aix/custom/ the layers. A bare layer folder (skills/, instructions/, profiles/,
                 templates/): payload from this kit, the folder is the org layer. Git URLs are cloned into
                 ~/.cache/aix/sources/ (git pull on upgrade). Recorded as `source:` in config.yaml; aix upgrade follows it.
  --from-org SRC, --from-custom SRC   one layer from another place (a kit checkout's .aix/<layer>/, a bare folder, a
                 URL); recorded as source_org: / source_custom: and followed by aix upgrade, which also accepts them.
Related: aix upgrade (update an already installed project), aix doctor (check the result).
