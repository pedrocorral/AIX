"""Shared helpers for the AIX test suite. @tests TS-KIT-001 (docs/tests/suite.md). Every test works in a temporary folder: a temporary HOME (so ~/.local/bin,
~/.cache/aix and the person layer are never touched), CI=1 and AIX_NO_USER=1 (no prompts, no TUI, no person layer),
and the real launcher run as a subprocess. Nothing here writes outside that folder except the tests of the checkout
itself (test_kit.py), which run `aix install` on the checkout the way a developer does."""
import filecmp, os, re, shutil, subprocess, tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LAUNCHER_NAME = "aix.cmd" if os.name == "nt" else "aix"
LAUNCHER = KIT / ".aix" / "bin" / LAUNCHER_NAME
PAYLOAD_IGNORE = shutil.ignore_patterns("index.json", "manifest.json", "org", "custom", "__pycache__", "*.pyc")


def version_of(root: Path) -> str:
    m = re.search(r"^version:\s*([^\s#]+)", (root / ".aix" / "config.yaml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "?"


def vtuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def temp_home(test) -> Path:
    """A fresh temporary folder, removed when the test ends."""
    home = Path(tempfile.mkdtemp(prefix="aix-test-"))
    test.addCleanup(shutil.rmtree, home, True)
    return home


def env(home: Path) -> dict:
    e = dict(os.environ)
    e["PATH"] = os.pathsep.join([str(KIT / ".aix" / "bin"), e.get("PATH", "")])  # `aix` on PATH, as after self-install; CI runners have none
    e.update({"HOME": str(home), "USERPROFILE": str(home), "CI": "1", "AIX_NO_USER": "1", "AIX_CACHE": str(home / "cache"),
              "TERM": "xterm", "PYTHONDONTWRITEBYTECODE": "1",
              "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory", "GIT_CONFIG_VALUE_0": "*"})
    return e


def run(args, cwd: Path, home: Path, check: bool = True, **opts):
    """Run the launcher with args; return CompletedProcess (stdout/stderr as text). check=True fails the call on a non-zero
    exit. opts: launcher (another kit's), stdin (text), extra_env (dict)."""
    e = env(home)
    e.update(opts.get("extra_env") or {})
    launcher = opts.get("launcher") or LAUNCHER
    r = subprocess.run([str(launcher), *map(str, args)], cwd=str(cwd), env=e, capture_output=True, text=True, input=opts.get("stdin"))
    if check and r.returncode != 0:
        raise AssertionError(f"aix {' '.join(map(str, args))} failed ({r.returncode}) in {cwd}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}")
    return r


class Terminal:
    """The launcher in a pseudo terminal, for the checklists and the y/N questions; `out` collects everything read."""
    def __init__(self, cwd: Path, home: Path, args, size: dict = None):
        import pty
        self.pid, self.fd = pty.fork()
        if self.pid == 0:  # child: the real launcher on a real tty
            os.chdir(cwd)
            e = env(home); e.pop("CI", None); e.update(size or {})
            os.execve(str(LAUNCHER), [str(LAUNCHER), *args], e)
        self.out = b""

    def read(self, seconds: float):
        """Collect output for that long, or until the child closes the terminal."""
        import select, time
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.1)
            if ready and not self._chunk():
                return

    def _chunk(self) -> bool:
        try:
            self.out += os.read(self.fd, 65536)
        except OSError:
            return False
        return True

    def send(self, data: bytes, wait: float = 0.5):
        os.write(self.fd, data); self.read(wait)

    def wait(self):
        os.waitpid(self.pid, 0)

    def plain(self) -> str:
        """The output without ANSI escape sequences."""
        return re.sub(rb"\x1b\[[0-9;?]*[A-Za-z]", b"", self.out).decode(errors="replace")


def install(home: Path, into: Path, *flags, kit: Path = KIT):
    """`aix install --into INTO FLAGS...` run from the given kit checkout (its launcher, its cwd)."""
    launcher = kit / ".aix" / "bin" / LAUNCHER_NAME
    return run(["install", "--into", into, *flags], cwd=kit, home=home, launcher=launcher)


def project_cmd(project: Path, home: Path, *args, check=True, **opts):
    """Run a command inside a project (the launcher re-executes the project's own copy of the CLI); opts as for run."""
    return run(args, cwd=project, home=home, check=check, **opts)


def upgrade(project: Path, home: Path, *flags, kit: Path = KIT):
    """`aix upgrade --yes FLAGS...` with the given kit's launcher, from inside the project (how a developer does it)."""
    launcher = kit / ".aix" / "bin" / LAUNCHER_NAME
    return run(["upgrade", "--yes", *flags], cwd=project, home=home, launcher=launcher)


def assert_healthy(test, project: Path, home: Path):
    d = project_cmd(project, home, "doctor")
    test.assertIn("installation healthy", d.stdout, d.stdout + d.stderr)
    v = project_cmd(project, home, "docs", "validate")
    test.assertIn("0 errors", v.stdout, v.stdout + v.stderr)
    return d.stdout


def config(project: Path) -> str:
    return (project / ".aix" / "config.yaml").read_text(encoding="utf-8")


def fixture(name: str, dest: Path) -> Path:
    shutil.copytree(FIXTURES / name, dest, dirs_exist_ok=True)
    return dest


def make_fork(home: Path, org: Path = KIT / "examples" / "acme", custom: Path = None) -> Path:
    """A copy of this checkout (payload + developer doc, no git) with .aix/org/ filled from `org` and optionally .aix/custom/."""
    fork = home / "fork"
    fork.mkdir()
    for rel in (".aix", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "docs", "AIX-DEVELOPMENT.md", "examples"):
        src = KIT / rel
        if src.is_dir():
            shutil.copytree(src, fork / rel, ignore=PAYLOAD_IGNORE)
        elif src.exists():
            shutil.copy2(src, fork / rel)
    if org:
        shutil.copytree(org, fork / ".aix" / "org")
    if custom:
        shutil.copytree(custom, fork / ".aix" / "custom")
    return fork


def previous_kit(test, home: Path) -> Path:
    """The previous tagged release checked out as a git worktree under home (skips the test when git or a tag is missing)."""
    if not shutil.which("git"):
        test.skipTest("git not available")
    r = subprocess.run(["git", "tag", "--sort=-v:refname"], cwd=str(KIT), env=env(home), capture_output=True, text=True)
    if r.returncode != 0:
        test.skipTest("not a git checkout")
    current = vtuple(version_of(KIT))
    prev = next((t for t in r.stdout.split() if t.startswith("v") and vtuple(t[1:]) < current), None)
    if not prev:
        test.skipTest("no previous tag")
    dest = home / "prev-kit"
    subprocess.run(["git", "worktree", "add", "-q", str(dest), prev], cwd=str(KIT), env=env(home), check=True, capture_output=True)
    test.addCleanup(lambda: subprocess.run(["git", "worktree", "remove", "--force", str(dest)], cwd=str(KIT), env=env(home), capture_output=True))
    return dest


def same_tree(a: Path, b: Path) -> list:
    """Files that differ between two folders (ignoring caches); [] when identical."""
    diffs = []
    def walk(x: Path, y: Path):
        c = filecmp.dircmp(str(x), str(y), ignore=["__pycache__"])
        diffs.extend(f"{x / f}" for f in c.diff_files + c.left_only + c.right_only)
        for d in c.common_dirs:
            walk(x / d, y / d)
    walk(a, b)
    return diffs


def has_network() -> bool:
    return os.environ.get("AIX_TEST_NETWORK") == "1"
