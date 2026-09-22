#!/bin/sh
# AIX one-line installer for Linux and macOS:
#   curl -fsSL https://raw.githubusercontent.com/pedrocorral/AIX/main/install.sh | sh
# Clones (or updates) the kit into $AIX_HOME (default ~/.local/share/aix/kit) and runs `aix self-install`, which
# links ~/.local/bin/aix and adds that folder to your shell profile. Needs git and Python 3.9+. Rerunnable.
set -eu
repo="${AIX_REPO:-https://github.com/pedrocorral/AIX.git}"
dest="${AIX_HOME:-$HOME/.local/share/aix/kit}"
command -v git >/dev/null 2>&1 || { echo "install.sh: git is required (https://git-scm.com)" >&2; exit 1; }
py="$(command -v python3 || command -v python || true)"
[ -n "$py" ] || { echo "install.sh: Python 3.9+ is required (https://www.python.org/downloads/)" >&2; exit 1; }
if [ -d "$dest/.git" ]; then
  echo "updating $dest"
  git -C "$dest" pull -q --ff-only
else
  echo "cloning $repo -> $dest"
  mkdir -p "$(dirname "$dest")"
  git clone -q "$repo" "$dest"
fi
exec "$dest/.aix/bin/aix" self-install "$@"
