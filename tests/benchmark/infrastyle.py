"""Infra rules: `aix code security` (the rows on Dockerfiles, compose files, Kubernetes manifests, Helm charts and
GitHub Actions workflows) against Checkov on the same projects. Checkov reads the files as text with its full check
set; pairing is by file and line within three, both ids kept for reading by hand. Prints Checkov's checks by id with
the projects they fire on, ours' findings matched or not, and the Checkov-only checks ranked by projects. Not part of
the test suite. Needs BENCH_DIR/venv/bin/checkov. Usage: python3 tests/benchmark/infrastyle.py [--bench DIR] [project ...]"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

FRAMEWORKS = "dockerfile,kubernetes,helm,github_actions,yaml"
INFRA = re.compile(r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*\.ya?ml|compose\.ya?ml|\.npmrc|dependabot\.ya?ml)$|(^|/)\.github/workflows/[^/]+\.ya?ml$|\.ya?ml$")
OURS = """import sys, json
sys.path.insert(0, '.aix/scripts')
import codesecurity
from codefiles import default_roots
print(json.dumps([(f[3], f[4], f[1], f[2]) for f in codesecurity.scan(default_roots())]))
"""


def run_ours(tmp: Path) -> list:
    out, _ = engines.timed([sys.executable, "-c", OURS], tmp)
    return [(f, ln, cwe, what) for f, ln, cwe, what in engines._json(out) if ln and INFRA.search(f)]


def run_checkov(tmp: Path) -> tuple:
    out, secs = engines.timed([str(engines.BENCH / "venv" / "bin" / "checkov"), "-d", ".", "--framework", FRAMEWORKS, "-o", "json", "--quiet", "--compact", "--skip-path", "node_modules", "--skip-path", ".aix"], tmp, 1800)
    try:
        data = json.loads(out)
    except ValueError:
        return [], secs
    items = []
    for run in (data if isinstance(data, list) else [data]):
        for f in run.get("results", {}).get("failed_checks", []):
            items.append((f["file_path"].lstrip("/"), int(f["file_line_range"][0]), f["check_id"], str(f.get("check_name", ""))[:80], run.get("check_type")))
    return items, secs


def pair(ours: list, theirs: list) -> dict:
    pairs = _pairs(ours, theirs)   # ours index -> theirs index
    return dict(ours=len(ours), checkov=len(theirs), both=len(pairs),
                ours_only=[f"{f}:{ln} {what} ({cwe})" for i, (f, ln, cwe, what) in enumerate(ours) if i not in pairs],
                checkov_only=[(cid, f"{f}:{ln}", name) for j, (f, ln, cid, name, _) in enumerate(theirs) if j not in pairs.values()],
                matched=[f"{f}:{ln} {what} ({cwe}) ~ {theirs[j][2]}" for i, (f, ln, cwe, what) in enumerate(ours) for j in [pairs.get(i)] if j is not None])


def _pairs(ours: list, theirs: list) -> dict:
    """ours index -> the first unmatched Checkov result in the same file within three lines."""
    taken, out = set(), {}
    for i, (f, ln, *_) in enumerate(ours):
        j = next((j for j, (tf, tln, *_) in enumerate(theirs) if j not in taken and tf == f and abs(tln - ln) <= 3), None)
        if j is not None:
            taken.add(j); out[i] = j
    return out


def bench(name: str) -> dict:
    tmp = engines.prepare(next(p for p in engines.PROJECTS if p["name"] == name))
    theirs, secs = run_checkov(tmp)
    result = dict(project=name, secs=secs, checks=Counter(t[2] for t in theirs), names={t[2]: t[3] for t in theirs}, **pair(run_ours(tmp), theirs))
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"infrastyle-{name}.json").write_text(json.dumps(result, indent=1))
    return result


def render(results: list) -> str:
    out = ["| project | ours (infra) | Checkov | both | Checkov s |", "|---|---|---|---|---|"]
    out += [f"| {r['project']} | {r['ours']} | {r['checkov']} | {r['both']} | {r['secs']} |" for r in results]
    by_check, names, only = defaultdict(set), {}, defaultdict(set)
    for r in results:
        names.update(r["names"])
        for cid in r["checks"]:
            by_check[cid].add(r["project"])
        for cid, _, _ in r["checkov_only"]:
            only[cid].add(r["project"])
    out += ["", "| Checkov check | fires on projects | of which unmatched by ours | what it checks |", "|---|---|---|---|"]
    for cid, projects in sorted(by_check.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        out.append(f"| {cid} | {len(projects)} | {len(only.get(cid, ()))} | {names.get(cid, '')} |")
    for r in results:
        out += ["", f"== {r['project']} ours matched ({r['both']}): {r['matched'][:12]}", f"== {r['project']} ours only ({len(r['ours_only'])}): {r['ours_only'][:12]}",
                f"== {r['project']} Checkov only ({len(r['checkov_only'])}): {[(c, w) for c, w, _ in r['checkov_only'][:20]]}"]
    return "\n".join(out)


def main(argv: list):
    if "--bench" in argv:
        i = argv.index("--bench"); engines.BENCH = Path(argv[i + 1]); del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")] or [p["name"] for p in engines.PROJECTS]
    print(render([bench(n) for n in names]))


if __name__ == "__main__":
    main(sys.argv[1:])
