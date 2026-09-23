#!/usr/bin/env python3
"""aix self-install — make `aix` callable from any terminal, from this kit clone. Idempotent; safe to rerun.

  1. Python 3.9+ present (the launcher needs it).
  2. ~/.local/bin exists (created), and ~/.local/bin/aix is a symlink to this clone's launcher. A foreign file called
     aix there is kept as aix.bak; a stale or other-clone link is replaced; where symlinks are impossible a two-line
     wrapper script is written instead.
  3. ~/.local/bin is on PATH: one marked line appended to the profile of every shell found (~/.bashrc, ~/.zshrc,
     ~/.config/fish/config.fish; ~/.bash_profile or ~/.profile for login shells) unless the folder is already on
     PATH. Never twice (the marker is checked), never edits anything else.
  4. Verification: the `aix` that the new PATH resolves is this clone's launcher; a different one earlier on PATH is
     reported.
Windows: %LOCALAPPDATA%\\aix\\bin\\aix.cmd (a wrapper calling this clone's aix.cmd) and that folder added to the user
PATH through PowerShell. --dry-run prints the plan; --no-profile skips step 3."""
import os, shutil, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
LAUNCHER = KIT / ".aix" / "bin" / ("aix.cmd" if os.name == "nt" else "aix")
MARK = "# added by aix self-install"


def home() -> Path:
    return Path(os.environ.get("HOME") or Path.home()) if os.name != "nt" else Path(os.environ.get("USERPROFILE") or Path.home())


def bin_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or (home() / "AppData" / "Local")) / "aix" / "bin"
    return home() / ".local" / "bin"


def on_path(folder: Path, path_env: str = None) -> bool:
    entries = (path_env if path_env is not None else os.environ.get("PATH", "")).split(os.pathsep)
    return any(e and Path(os.path.expanduser(e)).resolve() == folder.resolve() for e in entries if e)


def is_kit_clone() -> bool:
    return (KIT / "AIX-DEVELOPMENT.md").exists() and LAUNCHER.exists()


# ---- step 2: the link ---------------------------------------------------------------------------------------------

def link_state(link: Path):
    """'ok' | 'missing' | 'stale' (symlink elsewhere or broken) | 'foreign' (a real file) | 'wrapper' (our script)"""
    if link.is_symlink():
        try:
            return "ok" if link.resolve() == LAUNCHER.resolve() else "stale"
        except OSError:
            return "stale"
    if link.exists():
        text = link.read_text(encoding="utf-8", errors="replace") if link.is_file() else ""
        return "wrapper" if MARK in text and str(LAUNCHER) in text else "foreign"
    return "missing"


def write_link(link: Path, dry: bool, actions: list):
    state = link_state(link)
    if state == "ok" or (state == "wrapper" and os.name == "nt"):
        actions.append(f"link    {link} already points to this clone"); return
    if state == "foreign":
        actions.append(f"keep    {link} is not aix's: moved to {link}.bak")
        if not dry:
            shutil.move(str(link), str(link) + ".bak")
    elif state in ("stale", "wrapper"):
        actions.append(f"replace {link} pointed elsewhere")
        if not dry:
            link.unlink()
    if os.name == "nt":
        actions.append(f"write   {link} (wrapper calling {LAUNCHER})")
        if not dry:
            link.write_text(f"@echo off\r\nrem {MARK}\r\n\"{LAUNCHER}\" %*\r\n", encoding="utf-8")
        return
    actions.append(f"link    {link} -> {LAUNCHER}")
    if dry:
        return
    try:
        link.symlink_to(LAUNCHER)
    except OSError:
        link.write_text(f"#!/bin/sh\n{MARK}\nexec \"{LAUNCHER}\" \"$@\"\n", encoding="utf-8")
        link.chmod(0o755)
        actions[-1] = f"write   {link} (wrapper: this filesystem cannot symlink)"


# ---- step 3: PATH ----------------------------------------------------------------------------------------------------

def profile_files() -> list:
    """(file, line to append) for every shell this user has; login profiles on macOS where Terminal opens login shells."""
    h = home()
    shell = Path(os.environ.get("SHELL", "")).name
    posix = f'{MARK}\nexport PATH="$HOME/.local/bin:$PATH"\n'
    out = []
    if shell == "zsh" or (h / ".zshrc").exists():
        out.append((h / ".zshrc", posix))
    if shell == "bash" or (h / ".bashrc").exists() or not out:
        out.append((h / ".bashrc", posix))
        if sys.platform == "darwin":
            out.append((h / ".bash_profile", posix))
    if shell == "fish" or (h / ".config" / "fish" / "config.fish").exists():
        out.append((h / ".config" / "fish" / "config.fish", f"{MARK}\nfish_add_path -g $HOME/.local/bin\n"))
    if (h / ".profile").exists() and not any(f.name == ".profile" for f, _ in out):
        out.append((h / ".profile", posix))
    return out


def extend_path(dry: bool, actions: list) -> bool:
    """Append the PATH line where it is missing. Returns True when a new terminal is needed."""
    folder = bin_dir()
    if on_path(folder):
        actions.append(f"path    {folder} is already on PATH"); return False
    if os.name == "nt":
        return extend_path_windows(folder, dry, actions)
    changed = False
    for f, line in profile_files():
        if f.exists() and MARK in f.read_text(encoding="utf-8", errors="replace"):
            actions.append(f"path    {f} already has the line"); continue
        actions.append(f"path    append to {f}: {line.strip().splitlines()[-1]}")
        changed = True
        if not dry:
            f.parent.mkdir(parents=True, exist_ok=True)
            with f.open("a", encoding="utf-8") as fh:
                fh.write(("\n" if f.exists() and f.stat().st_size and not f.read_text(encoding='utf-8', errors='replace').endswith("\n") else "") + line)
    return changed


def extend_path_windows(folder: Path, dry: bool, actions: list) -> bool:
    ps = f"$p=[Environment]::GetEnvironmentVariable('Path','User'); if(($p -split ';') -notcontains '{folder}'){{[Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';{folder}'), 'User'); 'added'}} else {{'present'}}"
    actions.append(f"path    add {folder} to the user PATH (registry, via PowerShell)")
    if dry:
        return True
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    if r.returncode != 0:
        actions[-1] += f"  FAILED: {r.stderr.strip() or r.stdout.strip()}; add it by hand (System Properties > Environment Variables)"
        return False
    return "added" in r.stdout


# ---- step 4: verification ---------------------------------------------------------------------------------------------

def verify(actions: list) -> bool:
    folder = bin_dir()
    path = os.pathsep.join([str(folder), os.environ.get("PATH", "")])
    found = shutil.which("aix", path=path)
    if not found:
        actions.append("verify  FAILED: no aix found even with the link folder on PATH"); return False
    same = Path(found).resolve() == LAUNCHER.resolve() or (Path(found).is_file() and MARK in Path(found).read_text(encoding="utf-8", errors="replace"))
    if not same:
        actions.append(f"verify  WARNING: another aix comes first on PATH: {found}. Remove it or put {folder} before it. A shell alias named aix hides ours too: `unalias aix`.")
        return False
    r = subprocess.run([found, "version"], capture_output=True, text=True, cwd=str(home()))
    ok = r.returncode == 0 and "AIX" in r.stdout
    actions.append(f"verify  `aix version` -> {r.stdout.strip() or r.stderr.strip()}" if ok else f"verify  FAILED: {r.stdout}{r.stderr}")
    return ok


# ---- command --------------------------------------------------------------------------------------------------------------

def python_ok(actions: list) -> bool:
    if sys.version_info < (3, 9):
        actions.append(f"python  {sys.version.split()[0]} is too old: AIX needs 3.9+"); return False
    actions.append(f"python  {sys.version.split()[0]} at {sys.executable}"); return True


def main(args):
    dry, no_profile = "--dry-run" in args, "--no-profile" in args
    if any(a not in ("--dry-run", "--no-profile") for a in args):
        sys.exit("usage: aix self-install [--dry-run] [--no-profile]   (alias: aix install aix)")
    if not is_kit_clone():
        sys.exit(f"aix self-install: {KIT} is a project's copy of the kit, not a clone of AIX. Run it from the clone: "
                 "git clone <AIX repo> ~/AIX && ~/AIX/.aix/bin/aix self-install")
    actions = []
    print(f"aix self-install — kit clone at {KIT}" + (" (dry run, nothing written)" if dry else ""))
    ok = python_ok(actions)
    folder, link = bin_dir(), bin_dir() / ("aix.cmd" if os.name == "nt" else "aix")
    if not folder.is_dir():
        actions.append(f"mkdir   {folder}")
        if not dry:
            folder.mkdir(parents=True, exist_ok=True)
    write_link(link, dry, actions)
    needs_new_shell = False if no_profile else extend_path(dry, actions)
    if not dry:
        ok = verify(actions) and ok
    for a in actions:
        print("  " + a)
    if dry:
        return
    if needs_new_shell:
        rc = "a new terminal" if os.name == "nt" else "a new terminal, or in this one: export PATH=\"$HOME/.local/bin:$PATH\""
        print(f"\nPATH changed: open {rc}. Then `aix version` from anywhere, `aix install --into <project>` to equip a project.")
    elif ok:
        print("\n`aix` works from any terminal. Next: `aix install --into <project>`; later `aix self-update` refreshes this clone.")
    else:
        print("\nsomething above needs a hand; `aix doctor` inside a project reports the same checks.")
    sys.exit(0 if ok else 1)


# ---- self-update: three small units and the command -------------------------------------------------------------------

def is_git_clone(kit: Path) -> bool:
    return (kit / ".git").exists()


def git_pull(kit: Path):
    """Fast-forward the clone from its origin. Returns (ok, message); never raises."""
    if not shutil.which("git"):
        return False, "git is not installed"
    r = subprocess.run(["git", "-C", str(kit), "pull", "--ff-only", "-q"], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr.strip() or r.stdout.strip())


def update_message(kit: Path, before: str, after: str) -> str:
    """What to tell the user after a pull: the versions, and the reminder to upgrade projects when they changed."""
    line = f"kit clone {kit}: {before} -> {after}"
    if before == after:
        return line + " (already current)"
    return line + "\nrun `aix upgrade` inside each project to bring it to this version (`aix upgrade --dry-run` shows the plan)"


def self_update(args):
    """aix self-update: git pull --ff-only in the kit clone, then remind about aix upgrade."""
    if not is_kit_clone():
        sys.exit("aix self-update: not a kit clone; run it from the clone on PATH (aix self-install sets it up)")
    if not is_git_clone(KIT):
        sys.exit(f"aix self-update: {KIT} is not a git checkout; update it the way it was obtained")
    before = version_of(KIT)
    ok, message = git_pull(KIT)
    if not ok:
        sys.exit(f"aix self-update: git pull failed: {message}")
    print(update_message(KIT, before, version_of(KIT)))


def version_of(root: Path) -> str:
    import re
    m = re.search(r"^version:\s*([^\s#]+)", (root / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "?"


if __name__ == "__main__":
    main(sys.argv[1:])


def self_test(args):
    """aix self-test [NAME...] [--network] [-q]: the kit's own suite (tests/), from the clone. NAME = a file without
    the test_ prefix (agents, layers, ...); --network adds the registry downloads; -q hides the per-test lines."""
    if not is_kit_clone() or not (KIT / "tests").is_dir():
        sys.exit("aix self-test: run it from a clone of AIX (the one `aix self-install` set up); projects carry no tests")
    names = [a for a in args if not a.startswith("-")]
    env = dict(os.environ)
    if "--network" in args:
        env["AIX_TEST_NETWORK"] = "1"
    verbose = [] if "-q" in args else ["-v"]
    patterns = [f"test_{n.removeprefix('test_').removesuffix('.py')}.py" for n in names] or ["test_*.py"]
    failed = 0
    for pat in patterns:
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(KIT / "tests"), "-p", pat, *verbose], cwd=str(KIT), env=env)
        failed += r.returncode != 0
    sys.exit(1 if failed else 0)
