"""22. Extended tests: every code tool on real projects (tests/extended/projects.json), cloned shallow at a pinned
commit into ~/.cache/aix/extended/ on the first run (network), never into the repository. Skipped unless
`aix self-test --extended`. Per project: no traceback, each tool under the time limit, every recorded number within
the band of tests/extended/expected.json (`--record` rewrites it), and for the vulnerable-by-design apps every
documented vulnerability of tests/extended/known.json present in the report."""
import json, os, re, shutil, subprocess, tempfile, time, unittest
from pathlib import Path
from helpers import KIT, env, install

DATA = KIT / "tests" / "extended"
PROJECTS = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
EXPECTED_FILE, KNOWN_FILE = DATA / "expected.json", DATA / "known.json"
CACHE = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "extended"
ENABLED = os.environ.get("AIX_TEST_EXTENDED") == "1"
RECORD = os.environ.get("AIX_TEST_RECORD") == "1"
TIME_LIMIT = 120.0   # seconds per tool per project
BAND = 0.10          # a recorded number may move this much before the test fails
TOOLS = {  # tool -> (arguments, the number to record: regex with one group)
    "style": (["code", "style"], r"functions analysed (\d+)"),
    "graph": (["code", "graph"], r"nodes \d+, edges (\d+)"),
    "dead": (["code", "dead"], r"DEAD MODULES (\d+)"),
    "clones": (["code", "clones"], r"exact clone groups (\d+)"),
    "security": (["code", "security"], r"findings to review (\d+)"),
    "vulnerabilities": (["code", "vulnerabilities", "--taint"], r"taint paths[^:]*: (\d+) finding"),
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def fetch(project: dict):
    """The cached clone at the pinned commit; cloned on the first run. None when the network is not there."""
    dest = CACHE / f"{project['name']}-{project['commit'][:7]}"
    if not (dest / ".git").exists():
        shutil.rmtree(dest, ignore_errors=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", project["ref"], project["url"], str(dest)],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            return None
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != project["commit"]:
        raise AssertionError(f"{project['name']}: cache holds {head[:7]}, projects.json pins {project['commit'][:7]}; delete {dest} to re-clone")
    return dest


def working_copy(clone: Path, home: Path) -> Path:
    """A throwaway copy (no .git, no node_modules) with the kit installed and the code roots chosen."""
    copy = home / clone.name
    shutil.copytree(clone, copy, ignore=shutil.ignore_patterns(".git", "node_modules", "dist", "build"), symlinks=True)
    install(home, copy, "--agents", "claude", "--skip-all")
    subprocess.run([str(copy / ".aix" / "bin" / "aix"), "code", "find", "--yes"], cwd=copy, env=env(home), capture_output=True, text=True)
    return copy


def run_tool(copy: Path, home: Path, args: list) -> dict:
    """{'seconds', 'exit', 'out', 'traceback'} for one tool; a timeout is a traceback-level failure."""
    start = time.time()
    try:
        r = subprocess.run([str(copy / ".aix" / "bin" / "aix"), *args], cwd=copy, env=env(home), capture_output=True, text=True, timeout=TIME_LIMIT * 3)
        out, err, code = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        out, err, code = "", "TIMEOUT", -1
    tb = err.strip().splitlines()[-1] if "Traceback" in err or err == "TIMEOUT" else ""
    return {"seconds": round(time.time() - start, 1), "exit": code, "out": out, "traceback": tb}


def _number(out: str, rx: str):
    m = re.search(rx, out)
    return int(m.group(1)) if m else None


def _compare(name: str, got: dict, want: dict) -> list:
    """Problems: numbers outside the band, or nothing recorded yet."""
    if not want:
        return [f"{name}: nothing recorded in expected.json; run `aix self-test --extended --record` after reviewing: {got}"]
    problems = []
    for tool, value in got.items():
        old = want.get(tool)
        if old is None or value is None:
            continue
        if abs(value - old) > max(1, BAND * old):
            problems.append(f"{name} {tool}: {old} recorded, {value} now (band {BAND:.0%}); review, then --record")
    return problems


def _missing_known(name: str, report_for) -> list:
    """Documented vulnerabilities (known.json) absent from the tool's report on their own file."""
    missing = []
    for entry in _load(KNOWN_FILE).get(name, []):
        if f"{entry['file']}:{entry['line']}" not in report_for(entry["tool"], entry["file"]):
            missing.append(f"{name}: {entry['file']}:{entry['line']} ({entry['what']}) not found by aix code {entry['tool']}")
    return missing


@unittest.skipUnless(ENABLED, "extended: run `aix self-test --extended` (clones real projects into ~/.cache/aix/extended)")
class Extended(unittest.TestCase):
    """One test per project; see the module docstring."""
    recorded = {}

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="aix-ext-"))
        self.addCleanup(shutil.rmtree, self.home, True)

    @classmethod
    def tearDownClass(cls):
        if RECORD and cls.recorded:
            current = _load(EXPECTED_FILE)
            current.update(cls.recorded)
            EXPECTED_FILE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"\nrecorded {len(cls.recorded)} project(s) into {EXPECTED_FILE.relative_to(KIT)}")

    def run_project(self, project: dict):
        clone = fetch(project)
        if clone is None:
            self.skipTest(f"{project['name']}: not cached and the clone failed (network?)")
        copy = working_copy(clone, self.home)
        got, problems = {}, []
        for tool, (args, rx) in TOOLS.items():
            r = run_tool(copy, self.home, args)
            got[tool] = _number(r["out"], rx)
            if r["traceback"]:
                problems.append(f"{project['name']} {tool}: {r['traceback']}")
            elif r["seconds"] > TIME_LIMIT:
                problems.append(f"{project['name']} {tool}: {r['seconds']} s (limit {TIME_LIMIT:.0f} s)")
            elif got[tool] is None:
                problems.append(f"{project['name']} {tool}: no summary line in the output")
        Extended.recorded[project["name"]] = got
        if not RECORD:
            problems += _compare(project["name"], got, _load(EXPECTED_FILE).get(project["name"], {}))
        if project["kind"] == "vulnerable":
            problems += _missing_known(project["name"], lambda tool, file: run_tool(copy, self.home, TOOLS[tool][0] + [file])["out"])
        self.assertEqual(problems, [], "\n" + "\n".join(problems))


for _project in PROJECTS:
    setattr(Extended, f"test_{_project['name'].replace('-', '_')}", (lambda p: lambda self: self.run_project(p))(_project))


if __name__ == "__main__":
    unittest.main()
