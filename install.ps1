# AIX one-line installer for Windows (PowerShell):
#   irm https://raw.githubusercontent.com/pedrocorral/AIX/main/install.ps1 | iex
# Clones (or updates) the kit into $env:AIX_HOME (default %LOCALAPPDATA%\aix\kit) and runs `aix self-install`, which
# writes %LOCALAPPDATA%\aix\bin\aix.cmd and adds that folder to your user PATH. Needs git and Python 3.9+. Rerunnable.
$ErrorActionPreference = "Stop"
$repo = if ($env:AIX_REPO) { $env:AIX_REPO } else { "https://github.com/pedrocorral/AIX.git" }
$dest = if ($env:AIX_HOME) { $env:AIX_HOME } else { Join-Path $env:LOCALAPPDATA "aix\kit" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "install.ps1: git is required (https://git-scm.com)" }
if (-not ((Get-Command py -ErrorAction SilentlyContinue) -or (Get-Command python -ErrorAction SilentlyContinue))) { throw "install.ps1: Python 3.9+ is required (https://www.python.org/downloads/)" }
if (Test-Path (Join-Path $dest ".git")) {
  Write-Host "updating $dest"
  git -C $dest pull -q --ff-only
} else {
  Write-Host "cloning $repo -> $dest"
  New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
  git clone -q $repo $dest
}
& (Join-Path $dest ".aix\bin\aix.cmd") self-install @args
exit $LASTEXITCODE
