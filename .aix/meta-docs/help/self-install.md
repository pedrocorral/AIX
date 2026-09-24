aix self-install [--dry-run] [--no-profile]        alias: aix install aix
aix self-update
aix self-test [NAME...] [--network] [--extended [--record]] [-q]

Run once from a clone of AIX (git clone <repo> ~/AIX && ~/AIX/.aix/bin/aix self-install), or by the one-line
installers install.sh / install.ps1 at the repository root, which clone and call it. Refuses to run from a
project's copy of the kit. Steps, each printed:
  python   3.9+ present
  link     ~/.local/bin created if missing; ~/.local/bin/aix -> this clone's launcher. A foreign `aix` there is kept
           as aix.bak; a stale or other-clone link is replaced; a wrapper script where symlinks are impossible.
           Windows: %LOCALAPPDATA%\aix\bin\aix.cmd wrapping this clone's aix.cmd.
  path     when ~/.local/bin is not on PATH: one marked line appended to every shell profile found (~/.bashrc,
           ~/.zshrc, ~/.config/fish/config.fish, plus ~/.bash_profile on macOS, ~/.profile if present). Never twice.
           Windows: the folder added to the user PATH (registry, through PowerShell).
  verify   the aix the new PATH resolves is this clone; another aix earlier on PATH (or a shell alias) is reported.
Then: open a new terminal (or export PATH as printed) and `aix install --into <project>`.
aix self-update pulls the clone (git, fast-forward only) and reminds you to `aix upgrade` each project.
aix self-test runs the kit's own suite (tests/, stdlib unittest, temporary folders only): all files, or the named
ones (agents = tests/test_agents.py); --network adds the two registry downloads; -q hides the per-test lines.
--extended runs every code tool on twelve real projects (Flask, requests, Express, Excalidraw, Spring PetClinic,
commons-lang, ripgrep, bat, and the vulnerable-by-design NodeGoat, PyGoat, WebGoat, Juice Shop), cloned shallow at
a pinned commit into ~/.cache/aix/extended/ on the first run (about 200 MB, network) and never into the repository.
It checks: no crash, each tool under 120 s, every recorded number within 10 % of tests/extended/expected.json, and
every documented vulnerability of tests/extended/known.json found. --record accepts the current numbers after you
reviewed the change. Run it before a release and after touching a code tool; delete the cache to re-clone.
