"""Section 22 of docs/tests/benchmark-engines.md: ABAP style, ours vs abaplint on the same methods. abaplint's
`method_length` (statements), `cyclomatic_complexity` (its own list: IF, ELSEIF, WHILE, CASE, LOOP, CATCH, CHECK,
ASSERT, CLEANUP, ENDAT, SELECT loop, no base) and `nesting` are run at our limits on every method; ours reads the
same files through stylemetrics. Reported: units, how many are over each of our limits, and on the methods abaplint
flags whether our statement count and our count by abaplint's definition equal its numbers, next to our McCabe.
Needs BENCH_DIR/node/bin and BENCH_DIR/node_modules/.bin/abaplint (`npm install @abaplint/cli` in BENCH_DIR)."""
import json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import abapstyle   # noqa: E402
import stylemetrics   # noqa: E402

ABAPLINT_LIST = ("IF", "ELSEIF", "WHILE", "CASE", "LOOP", "CATCH", "CHECK", "ASSERT", "CLEANUP", "ENDAT", "ENDSELECT")
LIMITS = dict(max_lines=60, max_cognitive=15, max_cyclomatic=10, max_nesting=4, max_params=5)
ISSUE = re.compile(r"(\S+)\[(\d+), \d+\]\s+- (.*) \((\w+)\)")


def abaplint(project: Path) -> dict:
    """{(file, line): {rule: number}} from abaplint's metric rules at our limits, with its seconds."""
    base = json.loads(subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), "--default"], capture_output=True, text=True, env=_env()).stdout)
    rules = {k: v for k, v in base["rules"].items() if k in ("cyclomatic_complexity", "method_length", "nesting")}
    rules["cyclomatic_complexity"]["max"] = LIMITS["max_cyclomatic"]; rules["method_length"]["statements"] = LIMITS["max_lines"]
    rules["method_length"]["ignoreTestClasses"] = True; rules["nesting"]["depth"] = LIMITS["max_nesting"]
    cfg = project / "abaplint-metrics.json"
    cfg.write_text(json.dumps({"global": base["global"], "syntax": base.get("syntax", {}), "rules": rules}))
    t0 = time.time()
    out = subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), str(cfg)], cwd=project, capture_output=True, text=True, env=_env()).stdout
    cfg.unlink()
    found = {}
    for m in ISSUE.finditer(out):
        n = re.search(r"reached, (\d+)|currently (\d+)", m.group(3))
        found.setdefault((m.group(1), int(m.group(2))), {})[m.group(4)] = int(n.group(1) or n.group(2)) if n else None
    return {"items": found, "secs": round(time.time() - t0, 1)}


def _env() -> dict:
    return dict(os.environ, PATH=os.pathsep.join([str(engines.BENCH / "node" / "bin"), os.environ["PATH"]]))


def _body_of(stmts: list, head_line: int) -> list:
    """The statements between a unit's head (by its line) and its END word."""
    i = next((k for k, (word, _t, line) in enumerate(stmts) if word in abapstyle.UNITS and line == head_line), None)
    if i is None:
        return []
    j = next((k for k in range(i + 1, len(stmts)) if stmts[k][0] == abapstyle.UNITS[stmts[i][0]]), len(stmts) - 1)
    return stmts[i + 1:j]


def _file_units(f: Path, project: Path) -> dict:
    stmts = abapstyle.statements(f.read_text(encoding="utf-8", errors="replace").splitlines())
    out = {}
    for fx in stylemetrics.functions_in(f):
        body = _body_of(stmts, fx["line"])
        fx["statements"] = len(body)
        fx["abaplint_cyc"] = sum(1 for w, _t, _l in body if w in ABAPLINT_LIST)
        out[(str(f.relative_to(project)), fx["line"])] = fx
    return out


def ours(project: Path) -> dict:
    """Every unit by (file, head line) with our metrics, abaplint's statement count and its cyclomatic definition."""
    units, t0 = {}, time.time()
    for f in sorted(project.rglob("*.abap")):
        if ".testclasses." not in f.name and ".aix" not in f.parts:
            units.update(_file_units(f, project))
    return {"units": units, "secs": round(time.time() - t0, 1)}


def _mismatch(rule: str, key: tuple, value: int, fx) -> str:
    got = (fx["statements"] if rule == "method_length" else fx["abaplint_cyc"]) if fx else None
    if got == value:
        return ""
    mccabe = f" (McCabe {fx['cyclomatic']})" if fx and rule != "method_length" else ""
    return f"    {rule} {key[0]}:{key[1]} {fx['name'] if fx else '?'}: abaplint {value}, ours {got}{mccabe}"


def compare(ab: dict, us: dict) -> dict:
    rows, agree = [], {"method_length": [0, 0], "cyclomatic_complexity": [0, 0]}
    for key, rules in ab["items"].items():
        for rule, value in rules.items():
            if rule in agree and value is not None:
                row = _mismatch(rule, key, value, us["units"].get(key))
                agree[rule][1] += 1; agree[rule][0] += not row
                rows += [row] if row else []
    return {"agree": agree, "mismatches": rows}


def report(project: dict) -> str:
    tmp = engines.prepare(project)
    ab, us = abaplint(tmp), ours(tmp)
    cmp = compare(ab, us)
    over = {k: sum(1 for fx in us["units"].values() if fx[k[4:]] > v) for k, v in LIMITS.items()}
    flagged = {rule: sum(1 for r in ab["items"].values() if rule in r) for rule in ("method_length", "cyclomatic_complexity", "nesting")}
    lines = [f"== {project['name']}: units {len(us['units'])} (ours {us['secs']} s, abaplint {ab['secs']} s)",
             f"   ours over the limits: " + ", ".join(f"{k[4:]} {v}" for k, v in over.items()),
             f"   abaplint at the same limits: statements>{LIMITS['max_lines']} {flagged['method_length']}, its cyclomatic>{LIMITS['max_cyclomatic']} {flagged['cyclomatic_complexity']}, nesting>{LIMITS['max_nesting']} {flagged['nesting']} (one per file)",
             f"   same numbers on the methods it flags: statements {cmp['agree']['method_length'][0]}/{cmp['agree']['method_length'][1]}, cyclomatic by its definition {cmp['agree']['cyclomatic_complexity'][0]}/{cmp['agree']['cyclomatic_complexity'][1]}"]
    return "\n".join(lines + cmp["mismatches"][:12])


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name]))


if __name__ == "__main__":
    main(sys.argv[1:])
