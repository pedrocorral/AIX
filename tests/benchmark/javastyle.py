"""Java style benchmark: `aix code style` against Checkstyle and PMD on the same rows, at the same limits, on the
Spring projects of the extended cache (src/main/java only). Not part of the test suite.

Needs BENCH_DIR/checkstyle-all.jar and BENCH_DIR/pmd-bin-*; the rule selections at the kit's limits are
tests/benchmark/style/checkstyle.xml and pmd.xml. Writes ~/.cache/aix/benchmark/style-<project>.json and prints, per row and project,
the three counts, the matches and every mismatch with file:line for reading by hand.
Usage: python3 tests/benchmark/javastyle.py [--bench DIR] [project ...]"""
import csv, io, json, subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

STYLE = Path(__file__).resolve().parent / "style"
JAVA_PROJECTS = ["spring-petclinic", "jhipster-sample-app", "jhipster-sample-app-gradle", "WebGoat"]
MAIN = "src/main/java"
OURS = """import sys, json
sys.path.insert(0, '.aix/scripts')
from pathlib import Path
from codefiles import source_files, rel
import stylemetrics as sm
rows = []
for f in sorted(source_files([Path('src/main/java')])):
    if f.suffix != '.java':
        continue
    for fx in sm.functions_in(f):
        rows.append(dict(kind='function', file=fx['file'], line=fx['line'], name=fx['name'], lines=fx['lines'], params=fx['params'], cyclomatic=fx['cyclomatic'], cognitive=fx['cognitive'], nesting=fx['nesting'], hygiene=fx['hygiene'], test=fx['test']))
    rows.append(dict(kind='file', file=rel(f), lines=sm.file_lines(f), hygiene=sm.file_hygiene(f)))
print(json.dumps(rows))
"""

# row: (name, ours selector, checkstyle check names, pmd rule names)
ROWS = [
    ("lines > 60", "lines", ("MethodLength",), ("NcssCount",)),
    ("cyclomatic > 10", "cyclomatic", ("CyclomaticComplexity",), ("CyclomaticComplexity",)),
    ("cognitive > 15", "cognitive", (), ("CognitiveComplexity",)),
    ("nesting > 4", "nesting", ("NestedIfDepth", "NestedTryDepth", "NestedForDepth"), ("AvoidDeeplyNestedIfStmts",)),
    ("parameters > 5", "params", ("ParameterNumber",), ("ExcessiveParameterList",)),
    ("file lines > 400", "file_lines", ("FileLength",), ()),
    ("unused import", "unused import", ("UnusedImports",), ("UnnecessaryImport",)),
    ("unused variable / parameter / field", "never read", ("UnusedLocalVariable",), ("UnusedLocalVariable", "UnusedFormalParameter", "UnusedPrivateField")),
    ("swallowed exception", "swallowed", ("EmptyCatchBlock",), ("EmptyCatchBlock",)),
    ("== on a String", "compares String", (), ("UseEqualsToCompareStrings", "CompareObjectsWithEquals")),
]
LIMITS = dict(lines=60, cyclomatic=10, cognitive=15, nesting=4, params=5, file_lines=400)


def run_ours(tmp: Path) -> tuple:
    out, secs = engines.timed([sys.executable, "-c", OURS], tmp)
    if not out:
        sys.exit(subprocess.run([sys.executable, "-c", OURS], cwd=tmp, env=engines.env(), capture_output=True, text=True).stderr[-2000:])
    return json.loads(out), secs


def run_checkstyle(tmp: Path) -> tuple:
    out, secs = engines.timed(["java", "-jar", str(engines.BENCH / "checkstyle-all.jar"), "-c", str(STYLE / "checkstyle.xml"), "-f", "xml", MAIN], tmp)
    items = []
    for f in ET.fromstring(out[out.index("<?xml"):]) if "<?xml" in out else []:
        for e in f.findall("error"):
            items.append(dict(file=_rel(f.get("name"), tmp), line=int(e.get("line")), rule=e.get("source").rsplit(".", 1)[-1].removesuffix("Check"), what=e.get("message")))
    return items, secs


def _rel(path: str, tmp: Path) -> str:
    return str(Path(path).relative_to(tmp)) if Path(path).is_absolute() else path


def run_pmd(tmp: Path) -> tuple:
    pmd = next(engines.BENCH.glob("pmd-bin-*/bin/pmd"))
    out, secs = engines.timed([str(pmd), "check", "-R", str(STYLE / "pmd.xml"), "-d", MAIN, "-f", "csv", "--no-fail-on-violation", "--no-progress"], tmp)
    rows = [r for r in csv.DictReader(io.StringIO(out[out.index('"Problem"'):])) ] if '"Problem"' in out else []
    return [dict(file=_rel(r["File"], tmp), line=int(r["Line"]), rule=r["Rule"], what=r["Description"]) for r in rows], secs


def ours_for_row(rows: list, selector: str) -> list:
    """(file, line, name, value) of ours' findings for one row."""
    if selector == "file_lines":
        return [(r["file"], 1, r["file"], r["lines"]) for r in rows if r["kind"] == "file" and r["lines"] > LIMITS[selector]]
    if selector in LIMITS:
        return [(r["file"], r["line"], r["name"], r[selector]) for r in rows if r["kind"] == "function" and r[selector] > LIMITS[selector]]
    return _hygiene_rows(rows, selector)


def _hygiene_rows(rows: list, selector: str) -> list:
    return [(r["file"], line, r.get("name", "-"), msg) for r in rows for line, msg in r["hygiene"] if selector in msg]


def _function_at(rows: list, file: str, line: int):
    """Ours' function whose span holds the line (their line is the method's first token, ours the head's end): name or None."""
    best = None
    for r in rows:
        if r["kind"] == "function" and r["file"] == file and r["line"] - 8 <= line <= r["line"] + r["lines"]:
            if best is None or abs(r["line"] - line) < abs(best["line"] - line):
                best = r
    return best["name"] if best else None


def compare(rows: list, theirs: list, selector: str, by_function: bool) -> dict:
    ours = ours_for_row(rows, selector)
    if by_function:
        ours_keys = {(f, n) for f, _, n, _ in ours}
        their_keys = {(t["file"], _function_at(rows, t["file"], t["line"]) or f"line {t['line']}") for t in theirs}
    else:
        ours_keys = {(f, ln) for f, ln, _, _ in ours}
        their_keys = {(t["file"], t["line"]) for t in theirs}
    return dict(ours=len(ours_keys), theirs=len(their_keys), both=len(ours_keys & their_keys),
                ours_only=sorted(f"{f}:{x}" for f, x in ours_keys - their_keys), theirs_only=sorted(f"{f}:{x}" for f, x in their_keys - ours_keys))


def _compare_rows(rows: list, cs: list, pmd: list) -> dict:
    out = {}
    for title, selector, cs_rules, pmd_rules in ROWS:
        by_function = selector in LIMITS and selector != "file_lines"
        out[title] = dict(checkstyle=compare(rows, [t for t in cs if t["rule"] in cs_rules], selector, by_function) if cs_rules else None,
                          pmd=compare(rows, [t for t in pmd if t["rule"] in pmd_rules], selector, by_function) if pmd_rules else None)
    return out


def bench(name: str) -> dict:
    project = next(p for p in engines.PROJECTS if p["name"] == name)
    tmp = engines.prepare(project)
    rows, ours_secs = run_ours(tmp)
    cs, cs_secs = run_checkstyle(tmp)
    pmd, pmd_secs = run_pmd(tmp)
    result = dict(project=name, secs=dict(ours=ours_secs, checkstyle=cs_secs, pmd=pmd_secs), functions=sum(r["kind"] == "function" for r in rows),
                  files=sum(r["kind"] == "file" for r in rows), checkstyle_all=len(cs), pmd_all=len(pmd), rows=_compare_rows(rows, cs, pmd))
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"style-{name}.json").write_text(json.dumps(result, indent=1))
    return result


def _count_cell(c) -> str:
    return f"{c['theirs']} | {c['both']}" if c else "— | —"


def render(results: list) -> str:
    lines = ["| row | project | ours | Checkstyle | both | PMD | both |", "|---|---|---|---|---|---|---|"]
    for title, *_ in ROWS:
        for r in results:
            cs, pmd = r["rows"][title]["checkstyle"], r["rows"][title]["pmd"]
            lines.append(f"| {title} | {r['project']} | {(cs or pmd)['ours']} | {_count_cell(cs)} | {_count_cell(pmd)} |")
    return "\n".join(lines) + "\n\n" + _timing_table(results)


def _timing_table(results: list) -> str:
    lines = ["| project | functions | files | ours s | Checkstyle s | PMD s |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['project']} | {r['functions']} | {r['files']} | {r['secs']['ours']} | {r['secs']['checkstyle']} | {r['secs']['pmd']} |" for r in results]
    return "\n".join(lines)


def mismatches(results: list) -> str:
    out = []
    for r in results:
        for title, sides in r["rows"].items():
            for engine, c in sides.items():
                if c and (c["ours_only"] or c["theirs_only"]):
                    out.append(f"{r['project']} / {title} / {engine}: ours only {c['ours_only']}; theirs only {c['theirs_only']}")
    return "\n".join(out)


def main(argv: list):
    if "--bench" in argv:
        i = argv.index("--bench"); engines.BENCH = Path(argv[i + 1]); del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")] or JAVA_PROJECTS
    results = [bench(n) for n in names]
    print(render(results)); print(); print(mismatches(results))


if __name__ == "__main__":
    main(sys.argv[1:])
