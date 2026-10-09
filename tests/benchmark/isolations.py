"""Section 31 of docs/tests/benchmark-engines.md: `aix code isolations` on real projects and against import-linter.

1. Self-consistency on the cached extended projects: propose (--depth 2), accept, let a person accept the ADR, then
   check. The proposal is the code minus its defects, so the check must report exactly the file edges behind the
   defect pairs it left out (FORBIDDEN or HIDDEN), no UNDECLARED file, no BREAKING change, and no DECLARATION error.
   Any other finding is a bug in the proposal or in the rules.
2. The same rule written both ways on a planted Python project: import-linter's forbidden contract (a deny-list)
   and our declaration (an allow-list); then a package added later that imports the forbidden implementation, and
   a contract edited to make the check pass. Which tool still fails.

Not part of the test suite. Needs the extended cache and BENCH_DIR/venv/bin/lint-imports for part 2.
Run: `python tests/benchmark/isolations.py [PROJECT...]`."""
import os, re, shutil, subprocess, sys, tempfile, textwrap, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines import BENCH, PROJECTS, env, prepare

REAL = ["flask", "requests", "pygoat", "express", "juice-shop", "excalidraw", "ripgrep", "bat", "commons-lang", "spring-petclinic"]
LINT = BENCH / "venv" / "bin" / "lint-imports"


def aix(tmp: Path, *args) -> tuple:
    start = time.time()
    r = subprocess.run([str(tmp / ".aix" / "bin" / "aix"), "code", "isolations", *args], cwd=tmp, env=env(), capture_output=True, text=True, timeout=3600)
    return r.stdout + r.stderr, round(time.time() - start, 1)


def counts(report: str) -> dict:
    m = re.search(r"findings: (.*)", report)
    return {k: int(v) for k, v in re.findall(r"(\w+) (\d+)", m.group(1))} if m else {}


def defect_pairs(decl_text: str) -> set:
    """The (isolation, isolation) pairs the proposal left out, listed at its end."""
    return set(re.findall(r"^#   (\S+) -> (\S+): ", decl_text, re.M))


VERDICTS = ("import sys, json; sys.path.insert(0, '.aix/scripts'); import isodecl, isorules, isopropose; "
            "from codefiles import default_roots; from depedges import module_graph; from graphmetrics import is_test; "
            "d = isodecl.load(); n, e = module_graph(default_roots(), ownership=False); "
            "v = [isorules.judge(d, a, b) for a, b in sorted(e) if not is_test(a) and not is_test(b)]; "
            "print(json.dumps([isopropose._tops(x.owner_a, x.owner_b) for x in v if x]))")


def unexplained(tmp: Path, pairs: set) -> tuple:
    """(edges flagged, flagged edges whose sibling pair is not one the proposal left out)."""
    import json
    out = subprocess.run([sys.executable, "-c", VERDICTS], cwd=tmp, env=env(), capture_output=True, text=True, timeout=3600).stdout
    flagged = [tuple(x) for x in json.loads(out or "[]")]
    return len(flagged), [f for f in flagged if f not in pairs]


def self_consistency(name: str) -> dict:
    tmp = prepare(next(p for p in PROJECTS if p["name"] == name))
    try:
        _out, t_propose = aix(tmp, "--propose", "--depth", "2", "--write")
        decl = (tmp / "docs/requirements/isolations.yaml").read_text(encoding="utf-8")
        aix(tmp, "--accept")
        for adr in (tmp / "docs/requirements/decisions").glob("ADR-*-isolations.md"):
            adr.write_text(adr.read_text(encoding="utf-8").replace("status: proposed", "status: accepted"), encoding="utf-8")
        report, t_check = aix(tmp)
        c, pairs = counts(report), defect_pairs(decl)
        flagged, odd = unexplained(tmp, pairs)
        return dict(project=name, isolations=decl.count("\n    paths:"), defect_pairs=len(pairs), propose_s=t_propose, check_s=t_check,
                    edges_flagged=flagged, unexplained=len(odd), **{k: c.get(k, 0) for k in ("declaration", "governance", "undeclared", "breaking", "data")},
                    sample=[l for l in report.splitlines() if l.strip().startswith(("UNDECLARED", "BREAKING", "DECLARATION"))][:6] + [f"unexplained pair {o}" for o in odd[:6]])
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


# ---- part 2: the same rule, deny-list against allow-list ----------------------------------------------------------

PLANT = {
    "src/app/__init__.py": "",
    "src/app/orders/__init__.py": "",
    "src/app/orders/api.py": "from app.persistence.ports import Repo\n",
    "src/app/persistence/__init__.py": "",
    "src/app/persistence/ports.py": "class Repo: pass\n",
    "src/app/persistence/factory.py": "from app.persistence.postgres.repo import PgRepo\n",
    "src/app/persistence/postgres/__init__.py": "",
    "src/app/persistence/postgres/repo.py": "from app.persistence.ports import Repo\nclass PgRepo(Repo): pass\n",
}
IMPORTLINTER = """[importlinter]
root_package = app

[importlinter:contract:db]
name = Only persistence reaches its implementations
type = forbidden
source_modules =
    app.orders
forbidden_modules =
    app.persistence.postgres
"""
DECLARATION = """tests: exempt
isolations:
  src:                     {paths: [src/**], exposes: []}
  src.orders:              {paths: [src/app/orders/**], exposes: [], may_use: [src.persistence]}
  src.persistence:         {paths: [src/app/persistence/**], exposes: [src/app/persistence/ports.py, src/app/persistence/factory.py], may_use: []}
  src.persistence.postgres: {paths: [src/app/persistence/postgres/**], exposes: [src/app/persistence/postgres/repo.py], may_use: []}
"""


def _write(root: Path, files: dict):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(textwrap.dedent(text), encoding="utf-8")


def _lint(root: Path) -> str:
    if not LINT.exists():
        return "n/a"
    r = subprocess.run([str(LINT)], cwd=root, env=dict(os.environ, PYTHONPATH=str(root / "src")), capture_output=True, text=True)
    return "fails" if r.returncode else "passes"


def _ours(root: Path) -> str:
    r = subprocess.run([str(root / ".aix/bin/aix"), "code", "isolations", "--gate"], cwd=root, env=env(), capture_output=True, text=True)
    return "fails" if r.returncode else "passes"


def deny_against_allow() -> list:
    root = Path(tempfile.mkdtemp(prefix="aix-iso-vs-il-")) / "proj"
    try:
        _write(root, PLANT)
        subprocess.run([str(Path(__file__).resolve().parents[2] / ".aix/bin/aix"), "install", "--into", str(root), "--agents", "claude", "--skip-all"], env=env(), capture_output=True)
        (root / ".importlinter").write_text(IMPORTLINTER, encoding="utf-8")
        _write(root, {"docs/requirements/isolations.yaml": DECLARATION})
        subprocess.run([str(root / ".aix/bin/aix"), "code", "isolations", "--accept"], cwd=root, env=env(), capture_output=True)
        for adr in (root / "docs/requirements/decisions").glob("ADR-*-isolations.md"):
            adr.write_text(adr.read_text(encoding="utf-8").replace("status: proposed", "status: accepted"), encoding="utf-8")
        rows = [("the rule as written, clean code", _lint(root), _ours(root))]
        _write(root, {"src/app/orders/api.py": "from app.persistence.ports import Repo\nfrom app.persistence.postgres.repo import PgRepo\n"})
        rows.append(("orders imports postgres (the case both wrote)", _lint(root), _ours(root)))
        _write(root, {"src/app/orders/api.py": PLANT["src/app/orders/api.py"], "src/app/shipping/__init__.py": "",
                      "src/app/shipping/label.py": "from app.persistence.postgres.repo import PgRepo\n"})
        rows.append(("a new package, shipping, imports postgres", _lint(root), _ours(root)))
        _write(root, {"src/app/shipping/label.py": "", ".importlinter": IMPORTLINTER.replace("    app.persistence.postgres\n", "    app.persistence.mssql\n")})
        decl = root / "docs/requirements/isolations.yaml"
        decl.write_text(DECLARATION.replace("may_use: [src.persistence]}", "may_use: [src.persistence, src.persistence.postgres]}"), encoding="utf-8")
        _write(root, {"src/app/orders/api.py": "from app.persistence.postgres.repo import PgRepo\n"})
        rows.append(("orders imports postgres and the rule file is edited to allow it", _lint(root), _ours(root)))
        return rows
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or REAL
    print("== 1. the proposal judged on its own code (expected: flagged edges come only from the defect pairs)")
    print(f"{'project':<17}{'isolations':>11}{'defect pairs':>14}{'edges flagged':>15}{'unexplained':>13}{'undeclared':>12}{'breaking':>10}{'decl errors':>13}{'propose s':>11}{'check s':>9}")
    for r in (self_consistency(n) for n in names):
        print(f"{r['project']:<17}{r['isolations']:>11}{r['defect_pairs']:>14}{r['edges_flagged']:>15}{r['unexplained']:>13}{r['undeclared']:>12}{r['breaking']:>10}{r['declaration']:>13}{r['propose_s']:>11}{r['check_s']:>9}")
        for line in r["sample"]:
            print("      " + line.strip()[:150])
    print("\n== 2. import-linter (forbidden contract) against `aix code isolations` (allow-list + ADR fingerprint)")
    for case, il, ours in deny_against_allow():
        print(f"  {case:<66} import-linter {il:<7} ours {ours}")


if __name__ == "__main__":
    main(sys.argv[1:])
