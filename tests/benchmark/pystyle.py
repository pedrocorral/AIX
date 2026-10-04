"""Python cognitive complexity: `aix code style` against complexipy (SonarSource's definition, a value per function) on
the Python projects of the extended cache and the kit's own scripts. Functions are paired by file and qualified name;
the table gives equal / within one / further apart and the functions over 15 on each side; every larger difference is
listed with both values for reading by hand. Not part of the test suite.
Needs BENCH_DIR/venv/bin/complexipy. Usage: python3 tests/benchmark/pystyle.py [--bench DIR] [project ...]"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

PY_PROJECTS = ["flask", "requests", "pygoat", "aix"]
OURS = """import sys, json
sys.path.insert(0, '.aix/scripts')
from codefiles import source_files, default_roots
import stylemetrics as sm
rows = []
for f in sorted(source_files(%s)):
    if f.suffix == '.py':
        rows += [dict(file=fx['file'], line=fx['line'], name=fx['name'], cognitive=fx['cognitive'], cyclomatic=fx['cyclomatic'], test=fx['test']) for fx in sm.functions_in(f)]
print(json.dumps(rows))
"""


def run_ours(tmp: Path, roots_expr: str) -> list:
    r = subprocess.run([sys.executable, "-c", OURS % roots_expr], cwd=tmp, env=engines.env(), capture_output=True, text=True)
    if not r.stdout:
        sys.exit(r.stderr[-2000:])
    return json.loads(r.stdout)


def run_complexipy(tmp: Path, files: list) -> dict:
    """(file, qualified name) -> cognitive complexity, from one complexipy run over the files ours read."""
    out = engines.OUT / "complexipy-last.json"   # never inside the project: the kit itself is one of the projects
    engines.OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(engines.BENCH / "venv" / "bin" / "complexipy"), *files, "--output-format", "json", "--output", str(out), "--max-complexity-allowed", "0", "--quiet"], cwd=tmp, env=engines.env(), capture_output=True, text=True)
    items = json.loads(out.read_text()) if out.exists() else []
    return {(i["path"], i["function_name"].replace("::", ".")): i["complexity"] for i in items}


def compare(ours: list, theirs: dict) -> dict:
    last = {}   # complexipy keys by name: of several definitions (typing overloads), the last one is the implementation
    for r in ours:
        last[(r["file"], r["name"])] = r
    pairs = [(r, theirs[k]) for k, r in last.items() if k in theirs]
    diffs = [(r["cognitive"] - v, r, v) for r, v in pairs]
    apart = [f"{r['file']}:{r['name']} (l.{r['line']}) ours {r['cognitive']} complexipy {v}" for d, r, v in sorted(diffs, key=lambda x: -abs(x[0])) if abs(d) > 1]
    unpaired = [f"{r['file']}:{r['name']}" for r in ours if (r["file"], r["name"]) not in theirs][:10]
    return dict(ours=len(ours), theirs=len(theirs), paired=len(pairs), **_agreement(diffs), apart_list=apart, unpaired_ours=unpaired, **_over(pairs))


def _agreement(diffs: list) -> dict:
    return dict(equal=sum(d == 0 for d, _, _ in diffs), within_one=sum(abs(d) == 1 for d, _, _ in diffs), apart=sum(abs(d) > 1 for d, _, _ in diffs))


def _over(pairs: list) -> dict:
    return dict(ours_over=sum(r["cognitive"] > 15 for r, _ in pairs), theirs_over=sum(v > 15 for _, v in pairs), both_over=sum(r["cognitive"] > 15 and v > 15 for r, v in pairs))


def bench(name: str) -> dict:
    if name == "aix":
        tmp, roots = engines.KIT, "['.aix/scripts', 'tests']"
    else:
        tmp, roots = engines.prepare(next(p for p in engines.PROJECTS if p["name"] == name)), "default_roots()"
    ours = run_ours(tmp, roots)
    files = sorted({r["file"] for r in ours})
    result = dict(project=name, **compare(ours, run_complexipy(tmp, files)))
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"pystyle-{name}.json").write_text(json.dumps(result, indent=1))
    return result


def render(results: list) -> str:
    lines = ["| project | functions ours | complexipy | paired | equal | within 1 | further apart | ours > 15 | complexipy > 15 | both |", "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['project']} | {r['ours']} | {r['theirs']} | {r['paired']} | {r['equal']} | {r['within_one']} | {r['apart']} | {r['ours_over']} | {r['theirs_over']} | {r['both_over']} |" for r in results]
    for r in results:
        lines += ["", f"== {r['project']}: further apart ({len(r['apart_list'])}): {r['apart_list'][:12]}", f"   unpaired ours: {r['unpaired_ours']}"]
    return "\n".join(lines)


def main(argv: list):
    if "--bench" in argv:
        i = argv.index("--bench"); engines.BENCH = Path(argv[i + 1]); del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")] or PY_PROJECTS
    print(render([bench(n) for n in names]))


if __name__ == "__main__":
    main(sys.argv[1:])
