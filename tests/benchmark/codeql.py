"""CodeQL as the taint reference: `aix code vulnerabilities --taint` against CodeQL's Java security suite on the Spring
projects of the cache and the OWASP Benchmark. CodeQL reads a built project (`codeql database create` with the
project's Maven build, done beforehand into BENCH_DIR/codeql/db-<project dir>); this runner analyses each database,
pairs CodeQL's results with ours by file, CWE family and sink line (three lines), lists every mismatch with CodeQL's
source for reading by hand, and scores both on the Benchmark's ground truth. Not part of the test suite.
Usage: python3 tests/benchmark/codeql.py [--bench DIR] [project ...]"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines
from owasp import CASE, ground_truth, score, table

PROJECTS = ["WebGoat", "jhipster-sample-app", "spring-petclinic", "BenchmarkJava"]
SUITE = "codeql/java-queries:codeql-suites/java-security-extended.qls"
FAMILIES = {"CWE-89": "sql", "CWE-78": "command", "CWE-22": "path", "CWE-79": "xss", "CWE-90": "ldap", "CWE-643": "xpath", "CWE-601": "redirect",
            "CWE-611": "xxe", "CWE-502": "deserialisation", "CWE-501": "trust boundary", "CWE-918": "ssrf", "CWE-94": "code"}
OURS = """import sys, json
sys.path.insert(0, '.aix/scripts')
import javataint
from codefiles import default_roots
print(json.dumps([(f[3], f[4], f[1], f[2], f[5]) for f in javataint.taint(default_roots())]))
"""


def analyze(db: Path, out: Path) -> float:
    cli = engines.BENCH / "codeql" / "codeql" / "codeql"
    _, secs = engines.timed([str(cli), "database", "analyze", str(db), SUITE, "--format=sarif-latest", f"--output={out}", "--threads=0", "--rerun"], db.parent, 7200, stderr=True)
    return secs


def sarif_total(path: Path) -> dict:
    """rule id -> count over every CodeQL result, the families we have no row for included."""
    data = json.loads(path.read_text())
    out = {}
    for run in data.get("runs", []):
        for r in run.get("results", []):
            out[r["ruleId"]] = out.get(r["ruleId"], 0) + 1
    return out


def sarif_findings(path: Path) -> list:
    """(file, line, CWE, rule, source location, message) per CodeQL result in a family we have a row for."""
    data = json.loads(path.read_text())
    out = []
    for run in data.get("runs", []):
        rules = {r["id"]: r for r in run.get("tool", {}).get("driver", {}).get("rules", [])}
        for r in run.get("results", []):
            cwe = _family(rules.get(r["ruleId"], {}))
            if cwe:
                loc = r["locations"][0]["physicalLocation"]
                out.append((loc["artifactLocation"]["uri"], loc["region"]["startLine"], cwe, r["ruleId"], _source(r), r["message"]["text"][:90]))
    return out


def _family(rule: dict):
    """The first CWE tag of a rule that is one of our families, else None."""
    tags = rule.get("properties", {}).get("tags", [])
    cwes = [f"CWE-{int(t.split('cwe-')[1])}" for t in tags if "external/cwe/cwe-" in t]
    return next((c for c in cwes if c in FAMILIES), None)


def _source(result: dict) -> str:
    flows = result.get("codeFlows") or []
    if not flows:
        return ""
    first = flows[0]["threadFlows"][0]["locations"][0]["location"]["physicalLocation"]
    return f"{first['artifactLocation']['uri']}:{first['region']['startLine']}"


def ours_findings(tmp: Path) -> list:
    r = subprocess.run([sys.executable, "-c", OURS], cwd=tmp, env=engines.env(), capture_output=True, text=True)
    if not r.stdout:
        sys.exit(r.stderr[-1500:])
    return [(f, ln, cwe, what, snippet) for f, ln, cwe, what, snippet in json.loads(r.stdout) if cwe in FAMILIES]


def pair(ours: list, theirs: list) -> dict:
    """Matched when the same file, the same family and the sink lines are within three."""
    matched_theirs, matched_ours = set(), set()
    for i, (f, ln, cwe, *_) in enumerate(ours):
        j = _match(theirs, matched_theirs, f, ln, cwe)
        if j is not None:
            matched_theirs.add(j); matched_ours.add(i)
    return dict(ours=len(ours), codeql=len(theirs), both=len(matched_ours),
                ours_only=[f"{f}:{ln} {FAMILIES[cwe]} ({what}: {snippet[:60]})" for i, (f, ln, cwe, what, snippet) in enumerate(ours) if i not in matched_ours],
                codeql_only=[f"{f}:{ln} {FAMILIES[cwe]} [{rule}] from {src}: {msg}" for j, (f, ln, cwe, rule, src, msg) in enumerate(theirs) if j not in matched_theirs])


def _match(theirs: list, taken: set, f: str, ln: int, cwe: str):
    return next((j for j, (tf, tln, tcwe, *_) in enumerate(theirs) if j not in taken and tf == f and tcwe == cwe and abs(tln - ln) <= 3), None)


def benchmark_table(copy: Path, theirs: list) -> str:
    truth = ground_truth(copy)
    flagged = {}
    for f, _, cwe, *_ in theirs:
        m = CASE.search(f)
        if m:
            flagged.setdefault(m.group(1), set()).add(cwe)
    return table(score(truth, flagged), "CodeQL")


def bench(name: str) -> dict:
    project = next(p for p in engines.PROJECTS if p["name"] == name)
    db = next(engines.BENCH.glob(f"codeql/db-{name}-*"), None)
    if db is None:
        return dict(project=name, missing=True)
    sarif = engines.BENCH / "codeql" / f"{name}.sarif"
    secs = analyze(db, sarif) if not sarif.exists() else 0.0
    tmp = engines.prepare(project)
    theirs = sarif_findings(sarif)
    result = dict(project=name, secs=secs, all_rules=sarif_total(sarif), **pair(ours_findings(tmp), theirs))
    if name == "BenchmarkJava":
        result["table"] = benchmark_table(tmp, theirs)
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"codeql-{name}.json").write_text(json.dumps(result, indent=1))
    return result


def render(results: list) -> str:
    out = ["| project | ours | CodeQL | both | CodeQL analyze s |", "|---|---|---|---|---|"]
    for r in results:
        if r.get("missing"):
            out.append(f"| {r['project']} | — | no database | — | — |"); continue
        out.append(f"| {r['project']} | {r['ours']} | {r['codeql']} | {r['both']} | {r['secs']} |")
    for r in results:
        if r.get("missing"):
            continue
        out += ["", f"== {r['project']} every CodeQL rule that fired: {dict(sorted(r['all_rules'].items(), key=lambda kv: -kv[1]))}"]
        out += [f"== {r['project']} ours only ({len(r['ours_only'])}):"] + [f"   {x}" for x in r["ours_only"][:40]]
        out += [f"== {r['project']} CodeQL only ({len(r['codeql_only'])}):"] + [f"   {x}" for x in r["codeql_only"][:60]]
        if "table" in r:
            out += ["", r["table"]]
    return "\n".join(out)


def main(argv: list):
    if "--bench" in argv:
        i = argv.index("--bench"); engines.BENCH = Path(argv[i + 1]); del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")] or PROJECTS
    print(render([bench(n) for n in names]))


if __name__ == "__main__":
    main(sys.argv[1:])
