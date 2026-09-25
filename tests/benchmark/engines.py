"""Benchmark runner: the kit's own code tools and mature engines on the same extended projects, one finding list each.

Not part of the test suite. Needs the extended cache (tests/extended, ~/.cache/aix/extended) and the engines on disk:
BENCH_DIR/venv/bin (semgrep, bandit, ruff, lizard, vulture), BENCH_DIR/bin (gitleaks, osv-scanner), BENCH_DIR/pmd-bin-*.
An engine that is missing is skipped and the report says so. Writes one JSON per project into ~/.cache/aix/benchmark/
(per-finding lists with file:line, and seconds per engine); report.py turns them into the Markdown tables of
docs/tests/benchmark-engines.md.  Usage: python3 tests/benchmark/engines.py [--bench DIR] [project ...]"""
import csv, io, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
BENCH = Path(os.environ.get("BENCH_DIR", Path.home() / ".cache" / "aix" / "bench"))
OUT = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "benchmark"
CACHE = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "extended"
PROJECTS = json.loads((KIT / "tests" / "extended" / "projects.json").read_text())
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|it)(/|$)|[._-](test|spec)s?\.|Test\w*\.java|test_")
CPD_LANG = {".py": "python", ".js": "ecmascript", ".jsx": "ecmascript", ".ts": "typescript", ".tsx": "typescript", ".java": "java"}
FINDING = r"^{indent}(\S+):(\d+)  (.+?) \(CWE-\d+\)  \[(REVIEW|test)\]"


def env() -> dict:
    return dict(os.environ, CI="1", AIX_NO_USER="1", PATH=os.pathsep.join([str(BENCH / "venv" / "bin"), str(BENCH / "bin"), os.environ["PATH"]]))


def have(tool: str) -> bool:
    return shutil.which(tool, path=env()["PATH"]) is not None


def timed(cmd: list, cwd: Path, timeout=1800, stderr=False) -> tuple:
    """(stdout, seconds); '' when the command is missing, fails to start or times out. `stderr` merges it in."""
    start = time.time()
    try:
        out = subprocess.run(cmd, cwd=cwd, env=env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT if stderr else subprocess.PIPE, text=True, timeout=timeout).stdout
    except (subprocess.TimeoutExpired, OSError):
        out = ""
    return out, round(time.time() - start, 1)


def is_test(path: str) -> bool:
    return bool(TEST_PATH.search(path))


def prepare(project: dict) -> Path:
    """A working copy with the kit installed and code roots found; .git kept (history), node_modules left out."""
    src = next(CACHE.glob(f"{project['name']}-*"))
    tmp = Path(tempfile.mkdtemp(prefix="aix-bench-")) / project["name"]
    shutil.copytree(src, tmp, ignore=shutil.ignore_patterns("node_modules"), symlinks=True)
    subprocess.run([str(KIT / ".aix" / "bin" / "aix"), "install", "--into", str(tmp), "--agents", "claude", "--skip-all"], env=env(), capture_output=True, text=True)
    subprocess.run([str(tmp / ".aix" / "bin" / "aix"), "code", "find", "--yes"], cwd=tmp, env=env(), capture_output=True, text=True)
    return tmp


# ---- ours ---------------------------------------------------------------------------------------------------------

def _findings(out: str, indent: str) -> list:
    return [dict(file=m[1], line=int(m[2]), what=m[3], test=m[4] == "test") for m in re.finditer(FINDING.format(indent=indent), out, re.M)]


def ours_security(tmp: Path) -> dict:
    out, secs = timed([".aix/bin/aix", "code", "security"], tmp)
    return dict(items=_findings(out, "    "), secs=secs)


def ours_vulnerabilities(tmp: Path) -> tuple:
    """Taint findings and history findings, one run each (the history walk is timed on its own)."""
    out, secs = timed([".aix/bin/aix", "code", "vulnerabilities", "--taint"], tmp)
    taint = dict(items=[f for f in _findings(out, "      ") if "in history" not in f["what"]], secs=secs)
    code = "import sys, json; sys.path.insert(0, '.aix/scripts'); import secrethistory; print(json.dumps(secrethistory.history() or []))"
    out, secs = timed([sys.executable, "-c", code], tmp)   # the module, not the report: the report lists at most 20
    history = dict(items=[dict(file=f[3], what=f[2].split(" in history")[0], commit=f[2].rsplit("commit ", 1)[-1].rstrip(")")) for f in _json(out)], secs=secs)
    return taint, history


def ours_style(tmp: Path) -> tuple:
    """Hygiene line findings and the functions over the cyclomatic limit, from one `aix code style --all`."""
    out, secs = timed([".aix/bin/aix", "code", "style", "--all"], tmp)
    hygiene = [dict(file=m[1], line=int(m[2]), kind=m[3], what=m[4]) for m in re.finditer(r"^  LINE  (\S+):(\d+)  (leftover|swallowed|bug): (.+?)  ->", out, re.M)]
    over = [dict(func=m[1], ccn=int(m[2])) for m in re.finditer(r"^  (\S+)\s+\d+\*?\s+\d+\*?\s+(\d+)\*\s", out, re.M)]
    return dict(items=hygiene, secs=secs), dict(items=over, secs=secs)


def ours_dead(tmp: Path) -> dict:
    out, secs = timed([".aix/bin/aix", "code", "dead", "--functions"], tmp)
    block = out.split("DEAD FUNCTIONS")[1].split("\n  Every line")[0] if "DEAD FUNCTIONS" in out else ""
    return dict(items=[dict(file=m[1], name=m[2], line=int(m[3])) for m in re.finditer(r"^    (\S+?):(\S+)  \(line (\d+)\)", block, re.M)], secs=secs)


def ours_clones(tmp: Path) -> dict:
    """The exact groups listed (the report lists at most 20) and the total it counts."""
    out, secs = timed([".aix/bin/aix", "code", "clones"], tmp)
    groups = [dict(n=int(m[1]), lines=int(m[2]), where=re.findall(r"(\S+):\S+ \(l\.(\d+)\)", m[3]), test="[tests]" in m[3]) for m in re.finditer(r"^  EXACT  (\d+) × ~(\d+) lines: (.+)$", out, re.M)]
    total = re.search(r"exact clone groups (\d+)", out)
    return dict(items=groups, total=int(total.group(1)) if total else len(groups), secs=secs)


def ours_cve(tmp: Path) -> dict:
    out, secs = timed([".aix/bin/aix", "code", "vulnerabilities", "--cve"], tmp, stderr=True)
    m = re.search(r"known CVEs \(OSV\): (.+)", out)
    last = out.strip().splitlines()[-1][:120] if out.strip() else "no output"
    return dict(summary=m.group(1) if m else f"crashed: {last}", secs=secs)


# ---- theirs -------------------------------------------------------------------------------------------------------

def _json(out: str, key=None):
    try:
        data = json.loads(out)
    except ValueError:
        return []
    return data.get(key, []) if key else data


def semgrep(tmp: Path) -> dict:
    out, secs = timed(["semgrep", "--config", "p/default", "--json", "--quiet", "--metrics=off", "--timeout", "60", "--exclude", ".aix", "."], tmp)
    return dict(items=[dict(file=r["path"], line=r["start"]["line"], rule=r["check_id"].split(".")[-1], sev=r["extra"]["severity"], test=is_test(r["path"])) for r in _json(out, "results")], secs=secs)


def bandit(tmp: Path) -> dict:
    out, secs = timed(["bandit", "-r", "-q", "-f", "json", "-x", "./.aix,./node_modules,./.venv", "."], tmp)
    return dict(items=[dict(file=r["filename"].removeprefix("./"), line=r["line_number"], rule=r["test_id"], sev=r["issue_severity"], test=is_test(r["filename"])) for r in _json(out, "results")], secs=secs)


def ruff(tmp: Path) -> dict:
    out, secs = timed(["ruff", "check", "--select", "F401,F841,ARG001,ARG002,B006,E722,S110,C901", "--output-format", "json", "--exclude", ".aix", "."], tmp)
    return dict(items=[dict(file=os.path.relpath(r["filename"], tmp), line=r["location"]["row"], rule=r["code"], msg=r["message"], test=is_test(r["filename"])) for r in _json(out)], secs=secs)


def vulture(tmp: Path) -> dict:
    out, secs = timed(["vulture", "--min-confidence", "60", "--exclude", ".aix,node_modules,.venv", "."], tmp)
    return dict(items=[dict(file=m[1], line=int(m[2]), kind=m[3], name=m[4], test=is_test(m[1])) for m in re.finditer(r"^(\S+?):(\d+): unused (\w+) '([^']+)' \((\d+)% confidence\)", out, re.M)], secs=secs)


def lizard(tmp: Path) -> dict:
    out, secs = timed(["lizard", "--csv", "-x", "./.aix/*", "-x", "./node_modules/*", "."], tmp)
    rows = [r for r in csv.reader(io.StringIO(out)) if len(r) > 9 and r[1].isdigit() and int(r[1]) > 10]
    return dict(items=[dict(file=r[6].removeprefix("./"), func=r[7], ccn=int(r[1]), line=int(r[9]), test=is_test(r[6])) for r in rows], secs=secs)


def _cpd_rows(tmp: Path, lang: str) -> tuple:
    pmd = next(BENCH.glob("pmd-bin-*/bin/pmd"), None)
    if pmd is None:
        return [], 0
    out, secs = timed([str(pmd), "cpd", "--minimum-tokens", "60", "--language", lang, "--format", "csv", "--dir", ".", "--exclude", ".aix", "--no-fail-on-violation"], tmp, 900)
    groups = []
    for r in csv.reader(io.StringIO(out)):
        if r and r[0].isdigit():
            where = [(os.path.relpath(r[i + 1], tmp), int(r[i])) for i in range(3, len(r) - 1, 2)]
            groups.append(dict(lines=int(r[0]), tokens=int(r[1]), n=int(r[2]), where=where, lang=lang, test=all(is_test(w[0]) for w in where)))
    return groups, secs


def cpd(tmp: Path) -> dict:
    """PMD CPD once per language present (Rust is not supported by CPD)."""
    langs = sorted({CPD_LANG[f.suffix] for f in tmp.rglob("*") if f.suffix in CPD_LANG and ".aix" not in f.parts and "node_modules" not in f.parts})
    items, secs = [], 0.0
    for lang in langs:
        rows, s = _cpd_rows(tmp, lang)
        items += rows; secs += s
    return dict(items=items, langs=langs, secs=round(secs, 1))


def gitleaks(tmp: Path) -> dict:
    out, secs = timed(["gitleaks", "git", "--no-banner", "--exit-code", "0", "--report-format", "json", "--report-path", "/dev/stdout", "."], tmp)
    return dict(items=[dict(file=x["File"], line=x["StartLine"], rule=x["RuleID"], commit=x["Commit"][:7], test=is_test(x["File"])) for x in _json(out or "[]")], secs=secs)


def osv_scanner(tmp: Path) -> dict:
    out, secs = timed(["osv-scanner", "scan", "source", "-r", "--format", "json", "."], tmp)
    files = [(x["source"]["path"].replace(str(tmp) + "/", ""), len(x["packages"]), sum(len(p.get("vulnerabilities", [])) for p in x["packages"])) for x in _json(out, "results")]
    return dict(files=files, vulns=sum(f[2] for f in files), secs=secs)


# ---- one project --------------------------------------------------------------------------------------------------

THEIRS = [("semgrep", semgrep, None), ("bandit", bandit, "python"), ("ruff", ruff, "python"), ("vulture", vulture, "python"),
          ("lizard", lizard, None), ("cpd", cpd, None), ("gitleaks", gitleaks, None), ("osv-scanner", osv_scanner, None)]


def collect_ours(tmp: Path) -> dict:
    taint, history = ours_vulnerabilities(tmp)
    hygiene, cyclomatic = ours_style(tmp)
    return dict(security=ours_security(tmp), taint=taint, history=history, hygiene=hygiene, cyclomatic=cyclomatic,
                dead=ours_dead(tmp), clones=ours_clones(tmp), cve=ours_cve(tmp))


def collect_theirs(tmp: Path, langs: list) -> dict:
    out = {}
    for name, fn, lang in THEIRS:
        if lang and lang not in langs:
            continue
        tool = "pmd" if name == "cpd" else name
        out[name] = fn(tmp) if (name == "cpd" and next(BENCH.glob("pmd-bin-*/bin/pmd"), None)) or have(tool) else dict(items=[], secs=0, missing=True)
    return out


def bench(project: dict) -> dict:
    tmp = prepare(project)
    try:
        return dict(name=project["name"], langs=project["langs"], kind=project["kind"], ours=collect_ours(tmp), theirs=collect_theirs(tmp, project["langs"]))
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def _summary(result: dict) -> str:
    ours = {k: len(v["items"]) for k, v in result["ours"].items() if "items" in v}
    theirs = {k: len(v.get("items", [])) or v.get("vulns") for k, v in result["theirs"].items()}
    return f"{result['name']} {ours} {theirs}"


def main(argv: list):
    if "--bench" in argv:
        global BENCH; BENCH = Path(argv[argv.index("--bench") + 1]); del argv[argv.index("--bench"):argv.index("--bench") + 2]
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = argv or [p["name"] for p in PROJECTS]
    for project in [p for p in PROJECTS if p["name"] in wanted]:
        result = bench(project)
        (OUT / f"{project['name']}.json").write_text(json.dumps(result, indent=1))
        print(_summary(result), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
