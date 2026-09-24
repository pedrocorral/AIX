#!/usr/bin/env python3
"""aix code style — readability of functions and files, with specific, line-numbered feedback.

Per function: lines, cognitive complexity (Campbell / SonarSource 2017), cyclomatic complexity (McCabe 1976),
nesting depth, parameters, naming, docstring, magic numbers. Per file: length. Thresholds live in .aix/config.yaml
(`style:` block) with defaults from the literature (.aix/meta-docs/conventions/readability.md).
Python is measured exactly through the parser; JS/TS, Rust and Java through tokens and braces (approximate).

Targets: a directory, a file (extension optional), or one function: path:func, path/func, path::Class.method."""
import ast, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import ROOT, CODE_ROOTS, default_roots, rel, source_files
from depedges import iter_functions
from stylemetrics import CASE, DEFAULTS, TEST_LINES_FACTOR, analyse_py, file_lines, functions_in, parse_target, thresholds
from modernise import modern_py, modernisations



# ---- findings ---------------------------------------------------------------------------------------------------

def limit(fx, th, key):
    """The limit that applies to THIS function: tests get twice the lines; decorated functions (routes, commands,
    fixtures: the framework maps their parameters) have no parameter limit."""
    if key == "lines" and fx["test"]:
        return th["max_lines"] * TEST_LINES_FACTOR
    if key == "params" and fx["decorated"]:
        return 10 ** 6
    return th["max_" + key]


def _over_findings(fx, th) -> list:
    out = []
    a, b = fx["deepest"]
    if fx.get("passthrough"):
        out.append(("over", fx["line"], f"pass-through: forwards its arguments to `{fx['passthrough']}`",
                    "inline the call at the callers, or give the function a job (validate, convert, decide); a wrapper that only forwards is an envelope inside an envelope"))
    if fx["lines"] > limit(fx, th, "lines"):
        out.append(("over", fx["line"], f"{fx['lines']} lines (limit {limit(fx, th, 'lines')})",
                    f"split: one job per function; the deepest block is lines {a}-{b}, extract it into a named function"))
    if fx["cognitive"] > th["max_cognitive"]:
        where = "; ".join(f"line {l}: {r}" for l, _, r in sorted(fx["cognitive_items"], key=lambda x: -x[1])[:3])
        out.append(("over", fx["line"], f"cognitive complexity {fx['cognitive']} (limit {th['max_cognitive']})",
                    f"flatten: guard clauses and early returns, extract nested loops/conditions. Biggest costs: {where}"))
    if fx["cyclomatic"] > th["max_cyclomatic"]:
        out.append(("over", fx["line"], f"cyclomatic complexity {fx['cyclomatic']} (limit {th['max_cyclomatic']})",
                    "too many paths to test: split by case, or replace branch ladders with a lookup table / polymorphism"))
    if fx["nesting"] > th["max_nesting"]:
        out.append(("over", a, f"nesting depth {fx['nesting']} (limit {th['max_nesting']}) at lines {a}-{b}",
                    "invert the condition and return early, or extract the inner block into a function"))
    if fx["params"] > limit(fx, th, "params"):
        out.append(("over", fx["line"], f"{fx['params']} parameters (limit {th['max_params']})",
                    "group related parameters into one object (dataclass/struct/options), or split the function"))
    return out


def _name_finding(fx):
    case, rx = CASE[fx["lang"]]
    component = fx["lang"] == "js" and fx["jsx"] and re.match(r"^[A-Z][A-Za-z0-9]*$", fx["fname"])  # React: PascalCase is required
    dunder = fx["fname"].startswith("__") and fx["fname"].endswith("__")
    if rx.match(fx["fname"]) or component or dunder:
        return None
    what = f"name `{fx['fname']}` is not {case}_case" if case == "snake" else f"name `{fx['fname']}` is not camelCase"
    return ("name", fx["line"], what, "follow the language convention; a name that looks wrong slows every reader")


def _magic_findings(fx) -> list:
    out = []
    for line, value in ([] if fx["test"] else fx["magic"][:5]):
        shown = int(value) if float(value).is_integer() else value
        out.append(("magic", line, f"magic number {shown}", "name it: a constant tells the reader what the value means"))
    return out


def _advice_findings(fx) -> list:
    out = [f for f in [_name_finding(fx)] if f]
    out += [("name", line, f"single-letter name `{name}`", "say what it holds: `count`, `path`, `user`; one-letter names are for loop counters and maths") for line, name in fx["short_names"]]
    if fx["public"] and not fx["docstring"] and fx["lines"] >= 6 and not fx["test"]:
        out.append(("doc", fx["line"], "public function without a docstring / doc comment", "one line: what it does and when to call it"))
    return out + _magic_findings(fx)


def findings(fx, th):
    """(severity, line, message, advice) — every one specific to this function."""
    return _over_findings(fx, th) + _advice_findings(fx)


def score(fx, th):
    """How far over the limits, summed; 0 = all metrics inside."""
    return sum(max(0.0, fx[k] / limit(fx, th, k) - 1) for k in ("lines", "cognitive", "cyclomatic", "nesting", "params")) + (1.0 if fx.get("passthrough") else 0.0)


# ---- rendering --------------------------------------------------------------------------------------------------

METRIC_LABELS = (("lines", "lines"), ("cognitive", "cognitive complexity"), ("cyclomatic", "cyclomatic complexity"), ("nesting", "nesting depth"), ("params", "parameters"))


def _metric_rows(fx, th) -> list:
    rows = []
    for k, label in METRIC_LABELS:
        v, lim = fx[k], limit(fx, th, k)
        note = "  (test: doubled)" if k == "lines" and fx["test"] else "  (decorated: framework-mapped, no limit)" if k == "params" and fx["decorated"] else ""
        rows.append(f"  {label:22s} {v:>4}   limit {str(lim) if lim < 10 ** 6 else '-':<4}  {'OVER' if v > lim else 'ok'}{note}")
    return rows


def card(fx, th, rt=None):
    lines = [f"{fx['file']}:{fx['name']}  (line {fx['line']}, {fx['lang']})", "", *_metric_rows(fx, th)]
    lines.append(f"  {'docstring':22s} {'yes' if fx['docstring'] else 'no':>4}")
    lines.append(f"  {'pass-through':22s} {'yes' if fx.get('passthrough') else 'no':>4}   limit no    {'OVER' if fx.get('passthrough') else 'ok'}")
    fs = findings(fx, th)
    lines.append("")
    if not fs:
        lines.append("  no findings")
    lines += [f"  line {line:<5} {msg}\n             -> {advice}" for _sev, line, msg, advice in fs]
    lines += [f"  line {line:<5} modernise: {what}\n             -> {advice}" for line, what, advice in (modernisations(fx, rt) if rt else [])]
    return "\n".join(lines)


def runtime_header(rt, langs):
    return "  runtime: " + "; ".join(f"{rt[l][1]} ({rt[l][2]})" for l in ("python", "js", "rust", "java") if l in langs and l in rt)


def _table_row(fx, th) -> str:
    fs = findings(fx, th)
    tag = lambda k: (str(fx[k]) + ("*" if fx[k] > limit(fx, th, k) else " "))
    label = fx['file'] + ':' + fx['name']
    label = label if len(label) <= 60 else "…" + label[-59:]  # keep the function name, cut the path
    return f"  {label:60s} {tag('lines'):>6}{tag('cognitive'):>6}{tag('cyclomatic'):>6}{tag('nesting'):>6}{tag('params'):>5}  " + "; ".join(m for _, _, m, _ in fs[:2])


def _modernise_lines(fxs, rt) -> list:
    mods = [(fx, m) for fx in fxs for m in (modernisations(fx, rt) if rt else [])]
    if not mods:
        return []
    lines = [f"  modernise ({len(mods)}, advice for the detected runtime):"]
    lines += [f"    {fx['file']}:{fx['name']} line {line}: {what} -> {advice}" for fx, (line, what, advice) in mods[:15]]
    if len(mods) > 15:
        lines.append(f"    ... {len(mods) - 15} more")
    return lines


GATED = ("lines", "cognitive", "cyclomatic", "nesting", "params")


def _rows_with_findings(fxs, th) -> list:
    """Every function with a gated excess or an advice finding, worst first."""
    return sorted([fx for fx in fxs if score(fx, th) > 0 or findings(fx, th)], key=lambda fx: (-score(fx, th), -len(findings(fx, th))))


def _table_stats(fxs, th, files) -> dict:
    """What the table header reports: the rows with findings, counts per metric, the long files, the gated count."""
    over = _rows_with_findings(fxs, th)
    counts = {k: sum(1 for fx in fxs if fx[k] > limit(fx, th, k)) for k in GATED}
    counts["pass-through"] = sum(1 for fx in fxs if fx.get("passthrough"))
    long_files = [(rel(f), n) for f, n in files if n > th["max_file_lines"]]
    n_over = sum(1 for fx in fxs if score(fx, th) > 0)
    return dict(over=over, counts=counts, long_files=long_files, n_over=n_over)


def _table_head(n_fxs: int, s: dict, th) -> list:
    counts = ", ".join(f"{k} {v}" for k, v in s["counts"].items())
    lines = [f"  functions analysed {n_fxs}; over a limit {s['n_over']} ({counts}); with any finding {len(s['over'])}; "
             f"files over {th['max_file_lines']} lines: {len(s['long_files'])}", ""]
    if s["over"]:
        lines.append(f"  {'FUNCTION':60s} {'lines':>5} {'cogn':>5} {'cycl':>5} {'nest':>5} {'prm':>4}  findings")
    return lines


def table(fxs, th, files, max_rows=30, rt=None):
    """(text, gated count) for a set of functions and their files."""
    s = _table_stats(fxs, th, files)
    lines = _table_head(len(fxs), s, th)
    lines += [_table_row(fx, th) for fx in s["over"][:max_rows]]
    if len(s["over"]) > max_rows:
        lines.append(f"  ... {len(s['over']) - max_rows} more; narrow the target or use --all")
    lines += [f"  FILE  {f}: {n} lines (limit {th['max_file_lines']})  -> split by responsibility" for f, n in s["long_files"][:10]]
    lines += _modernise_lines(fxs, rt)
    lines.append("  * = over its limit (gated). Names, docstrings and magic numbers are advice.  Details: aix code style FILE:FUNCTION")
    lines.append("  fix with: OVER -> skill refactor-readability (one metric per change); modernise -> refactor-modernise")
    return "\n".join(lines), s["n_over"] + len(s["long_files"])


# ---- self-test --------------------------------------------------------------------------------------------------

SELFTEST_SRC = '''
def simple(a, b):
    return a + b

def sonar_example(x):
    if x > 0:                # +1
        for i in range(x):   # +2 (nesting 1)
            if i % 2:        # +3 (nesting 2)
                pass
    elif x < 0:              # +1
        pass
    else:                    # +1
        pass
    return x and x > 1       # +1 boolean sequence

def ladder(cmd):
    if cmd == "start":
        return 1
    elif cmd == "stop":
        return 2
    elif cmd == "status":
        return 3

def test_many_asserts(client):
    r = client.get("/x")
    assert r.status_code == 200
    assert r.json()["a"] == 1
    assert r.json()["b"] == 2
    assert r.json()["c"] == 3

def deep(a):
    if a:
        if a:
            if a:
                if a:
                    if a:
                        return 86400
'''


def selftest():
    tree = ast.parse(SELFTEST_SRC)
    fxs = {fn.name: analyse_py(Path("selftest.py"), cls, fn) for cls, fn in iter_functions(tree)}
    checks = [("simple cognitive", fxs["simple"]["cognitive"], 0), ("simple cyclomatic", fxs["simple"]["cyclomatic"], 1),
              ("sonar example cognitive", fxs["sonar_example"]["cognitive"], 9), ("sonar example cyclomatic", fxs["sonar_example"]["cyclomatic"], 6),
              ("deep nesting", fxs["deep"]["nesting"], 5), ("deep magic number", len(fxs["deep"]["magic"]), 1),
              ("simple params", fxs["simple"]["params"], 2),
              ("asserts do not add cyclomatic", fxs["test_many_asserts"]["cyclomatic"], 1),
              ("test: 200 is not magic, no magic advice", len([f for f in findings(fxs["test_many_asserts"], DEFAULTS) if f[0] == "magic"]), 0),
              ("ladder -> match under 3.10", len(modern_py(fxs["ladder"], {"python": ((3, 10), "", "")})), 1),
              ("ladder silent under 3.8", len(modern_py(fxs["ladder"], {"python": ((3, 8), "", "")})), 0)]
    failed = 0
    for name, got, want in checks:
        ok = got == want; failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got} (expected {want})")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


# ---- main -------------------------------------------------------------------------------------------------------

USAGE = "usage: aix code style [TARGET...] [--all] [--gate] [--report] [--selftest]   TARGET = dir | file[.ext] | file:func | file::Class.method"


def _target_or_exit(spec: str):
    """The parsed target, None for an absent default code root, or exit with the usage error."""
    t = parse_target(spec)
    if t is None and spec not in CODE_ROOTS:
        sys.exit(f"aix code style: '{spec}' is not a folder, file or file:function in this project")
    return t


def _function_hits(file: Path, name: str) -> list:
    hits = [fx for fx in functions_in(file) if fx["name"] == name or fx["name"].endswith("." + name) or fx["fname"] == name]
    if not hits:
        sys.exit(f"aix code style: no function '{name}' in {rel(file)}")
    return hits


def _collect_one(t, fxs: list, files: list, cards: list):
    if t[0] == "func":
        cards += _function_hits(t[1], t[2])
        return
    for f in (source_files([str(t[1])]) if t[0] == "dir" else [t[1]]):
        fxs += functions_in(f); files.append((f, file_lines(f)))


def _collect(specs):
    """(functions, (file, line count) pairs, single-function cards) for the targets on the command line."""
    fxs, files, cards = [], [], []
    for t in (_target_or_exit(spec) for spec in specs):
        if t is not None:
            _collect_one(t, fxs, files, cards)
    return fxs, files, cards


class _Run:
    """One `aix code style` invocation: thresholds, detected runtime and the flags given."""
    def __init__(self, args, specs):
        import runtime
        self.th, self.rt, self.specs, self.args = thresholds(), runtime.detect(ROOT), specs, args

    def flag(self, name: str) -> bool:
        return name in self.args


def _print_cards(cards, run: _Run) -> int:
    print("\n\n".join(card(fx, run.th, run.rt) for fx in cards))
    print("\n" + runtime_header(run.rt, {fx["lang"] for fx in cards}))
    return sum(1 for fx in cards if score(fx, run.th) > 0)


def _print_table(fxs, files, run: _Run) -> int:
    text, n_over = table(fxs, run.th, files, max_rows=10**6 if run.flag("--all") else 30, rt=run.rt)
    text = runtime_header(run.rt, {fx["lang"] for fx in fxs}) + "\n" + text
    print(f"Code style — {', '.join(run.specs)}\n\n" + text)
    if run.flag("--report"):
        out = ROOT / "docs" / "tests" / "code-style.md"
        out.write_text("# Code style (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    return n_over


def main(args):
    if "--selftest" in args:
        return selftest()
    run = _Run(args, [a for a in args if not a.startswith("--")] or default_roots())
    fxs, files, cards = _collect(run.specs)
    n_over = _print_cards(cards, run) if cards and not fxs else _print_table(fxs + cards, files, run)
    if run.flag("--gate") and n_over:
        sys.exit(f"GATE FAILED: {n_over} function(s)/file(s) over a limit")
    if run.flag("--gate"):
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
