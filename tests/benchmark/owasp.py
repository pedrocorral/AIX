"""OWASP Benchmark (BenchmarkJava, 2,740 servlet test cases with a ground-truth CSV): the kit's Java taint and security
rules scored per category the way the Benchmark scores a tool (true positive rate, false positive rate), and semgrep
the same way when it is installed. Not part of the suite. Usage: python3 tests/benchmark/owasp.py [--semgrep]"""
import csv, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

CATEGORY_CWE = {"sqli": {"CWE-89"}, "cmdi": {"CWE-78"}, "pathtraver": {"CWE-22"}, "xss": {"CWE-79"}, "ldapi": {"CWE-90"}, "xpathi": {"CWE-643"},
                "trustbound": {"CWE-501"}, "securecookie": {"CWE-614"}, "hash": {"CWE-328", "CWE-327"}, "crypto": {"CWE-327", "CWE-326"}, "weakrand": {"CWE-330", "CWE-338"}}
CASE = re.compile(r"(BenchmarkTest\d{5})\.java")


def ground_truth(copy: Path) -> dict:
    """{test name: (category, real)} from expectedresults-1.2.csv."""
    out = {}
    with open(copy / "expectedresults-1.2.csv", newline="") as f:
        for row in csv.reader(f):
            if row and row[0].startswith("BenchmarkTest"):
                out[row[0]] = (row[1], row[2].strip().lower() == "true")
    return out


def ours(copy: Path, what: str) -> dict:
    """{test name: set of CWEs} the kit reports from the modules: `taint` (javataint, data flow) or `rules`
    (codesecurity, the per-line and assembled rules, no input source needed)."""
    call = "javataint.taint(roots)" if what == "taint" else "codesecurity.scan(roots)"
    code = f"import sys, json; sys.path.insert(0, '.aix/scripts'); import codesecurity, javataint; roots = ['src/main/java/org/owasp/benchmark/testcode']; print(json.dumps([(f[3], f[1]) for f in {call}]))"
    out = subprocess.run([sys.executable, "-c", code], cwd=copy, env=engines.env(), capture_output=True, text=True).stdout
    flagged = {}
    for path, cwe in json.loads(out or "[]"):
        m = CASE.search(path)
        if m:
            flagged.setdefault(m.group(1), set()).add(cwe)
    return flagged


def semgrep(copy: Path) -> dict:
    out, _ = engines.timed(["semgrep", "--config", "p/default", "--json", "--quiet", "--metrics=off", "--timeout", "60", "src/main/java/org/owasp/benchmark/testcode"], copy)
    flagged = {}
    for r in engines._json(out, "results"):
        m = CASE.search(r["path"])
        cwes = r["extra"].get("metadata", {}).get("cwe", [])
        for c in ([cwes] if isinstance(cwes, str) else cwes):
            cm = re.search(r"CWE-\d+", c)
            if m and cm:
                flagged.setdefault(m.group(1), set()).add(cm.group(0))
    return flagged


def _counts(cases: list, hit: set) -> tuple:
    """(TP, FP, FN, TN) of one category: cases = [(name, real)], hit = the names a tool flagged in the category."""
    tally = Counter((real, n in hit) for n, real in cases)
    return tally[(True, True)], tally[(False, True)], tally[(True, False)], tally[(False, False)]


def _rates(tp: int, fp: int, fn: int, tn: int) -> tuple:
    tpr = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return tpr, fpr


def score(truth: dict, flagged: dict) -> list:
    """Per category: cases, TP, FP, FN, TN, TPR, FPR, Benchmark score (TPR - FPR)."""
    rows = []
    for cat, cwes in CATEGORY_CWE.items():
        cases = [(name, real) for name, (c, real) in truth.items() if c == cat]
        hit = {name for name, _ in cases if flagged.get(name, set()) & cwes}
        tp, fp, fn, tn = _counts(cases, hit)
        tpr, fpr = _rates(tp, fp, fn, tn)
        rows.append([cat, len(cases), tp, fp, fn, tn, f"{tpr:.0%}", f"{fpr:.0%}", f"{(tpr - fpr) * 100:.0f}"])
    return rows


def table(rows: list, tool: str) -> str:
    head = ["category", "cases", "TP", "FP", "FN", "TN", "TPR", "FPR", f"score ({tool})"]
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def main(argv: list):
    project = next(p for p in engines.PROJECTS if p["name"] == "BenchmarkJava")
    copy = engines.prepare(project)
    truth = ground_truth(copy)
    print(f"OWASP Benchmark 1.2: {len(truth)} test cases, {sum(1 for _, r in truth.values() if r)} real\n")
    taint, rules = ours(copy, "taint"), ours(copy, "rules")
    both = {n: taint.get(n, set()) | rules.get(n, set()) for n in set(taint) | set(rules)}
    print(table(score(truth, taint), "ours, taint")); print()
    print(table(score(truth, rules), "ours, rules")); print()
    print(table(score(truth, both), "ours, taint + rules"))
    if "--semgrep" in argv and engines.have("semgrep"):
        print(); print(table(score(truth, semgrep(copy)), "semgrep"))


if __name__ == "__main__":
    main(sys.argv[1:])
