"""JS/TS style benchmark: `aix code style` against ESLint on the same functions and the same rows at the kit's limits,
on the JS/TS projects of the extended cache. Both sides read the same file list: the kit's code roots after
`aix code find`, vendored files and node_modules left out. ESLint runs with every threshold at 0, so it reports
every function with its value (lines, cyclomatic, cognitive, parameters, block depth); the runner pairs its functions
with ours by file, line and name, then applies the kit's limits to both. Not part of the test suite.

Needs BENCH_DIR/node/bin and BENCH_DIR/eslint/node_modules (eslint, @typescript-eslint/parser, eslint-plugin-sonarjs);
the rule selection is tests/benchmark/style/eslint.config.mjs, copied beside those node_modules at run time.
Writes ~/.cache/aix/benchmark/jsstyle-<project>.json and prints the tables and every mismatch for reading by hand.
Usage: python3 tests/benchmark/jsstyle.py [--bench DIR] [project ...]"""
import json, os, re, shutil, subprocess, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines
from javastyle import LIMITS, STYLE

JS_PROJECTS = ["express", "NodeGoat", "juice-shop", "excalidraw", "jhipster-sample-app", "jhipster-sample-app-gradle"]
JS_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".mjs")
METRICS = ("lines", "cyclomatic", "cognitive", "nesting", "params")
OURS = """import sys, json
sys.path.insert(0, '.aix/scripts')
from codefiles import source_files, rel, default_roots
import stylemetrics as sm
rows = []
for f in sorted(source_files(default_roots())):
    if f.suffix not in %r or f.name.endswith('.d.ts'):
        continue
    for fx in sm.functions_in(f):
        rows.append(dict(kind='function', file=fx['file'], line=fx['line'], name=fx['name'], lines=fx['lines'], params=fx['params'], cyclomatic=fx['cyclomatic'], cognitive=fx['cognitive'], nesting=fx['nesting'], hygiene=fx['hygiene'], test=fx['test']))
    rows.append(dict(kind='file', file=rel(f), lines=sm.file_lines(f), hygiene=sm.file_hygiene(f)))
print(json.dumps(rows))
""" % (JS_SUFFIXES,)
LINE_ROWS = [("unused import / variable / parameter", "leftover", "no-unused-vars"), ("swallowed exception", "swallowed", "no-empty"),
             ("assignment inside a condition", "assignment inside", "no-cond-assign")]
NAMED = re.compile(r"^(?:Async |Static |Generator )*(?:[Ff]unction|[Mm]ethod|[Gg]etter|[Ss]etter|[Aa]rrow function|[Cc]onstructor)(?: '([^']+)')?")


# ---- the two sides ------------------------------------------------------------------------------------------------

def run_ours(tmp: Path) -> tuple:
    out, secs = engines.timed([sys.executable, "-c", OURS], tmp)
    if not out:
        sys.exit(subprocess.run([sys.executable, "-c", OURS], cwd=tmp, env=engines.env(), capture_output=True, text=True).stderr[-2000:])
    return json.loads(out), secs


def run_eslint(tmp: Path, files: list) -> tuple:
    """ESLint on exactly the files ours read: (messages, seconds). A parse error is kept as rule 'fatal'."""
    home = engines.BENCH / "eslint"
    shutil.copy(STYLE / "eslint.config.mjs", home / "eslint.config.mjs")
    env = dict(engines.env(), PATH=os.pathsep.join([str(engines.BENCH / "node" / "bin"), engines.env()["PATH"]]))
    start = time.time()
    r = subprocess.run([str(home / "node_modules" / ".bin" / "eslint"), "--config", str(home / "eslint.config.mjs"), "--no-config-lookup", "--no-ignore", "--format", "json", *files],
                       cwd=tmp, env=env, capture_output=True, text=True, timeout=1800)
    items = []
    for f in json.loads(r.stdout or "[]"):
        rel = str(Path(f["filePath"]).relative_to(tmp))
        items += [dict(file=rel, line=m.get("line") or 1, end=m.get("endLine") or m.get("line") or 1, rule="fatal" if m.get("fatal") else m["ruleId"], what=m["message"]) for m in f["messages"]]
    return items, round(time.time() - start, 1)


def _kind(message: str) -> str:
    head = message.split(" has ")[0]
    return "arrow function" if "rrow function" in head else "method" if "ethod" in head or "etter" in head or "onstructor" in head else "function"


def eslint_functions(items: list) -> dict:
    """(file, line) -> the function ESLint saw there, with its values. The core rules report at the function's first
    line and end there too, so the span comes from max-lines-per-function's count; sonarjs reports cognitive complexity
    at the name or the arrow, which can be a later line of a multi-line head, so cognitive values and max-depth blocks
    are folded into the innermost core function whose span holds them."""
    fns, later = {}, []
    for t in items:
        m = re.search(r"\((\d+)\)|complexity of (\d+)|Complexity from (\d+)", t["what"])
        value = int(next(g for g in m.groups() if g)) if m else None
        if t["rule"] in CORE:
            _core_value(fns, t, value)
        elif t["rule"] in ("sonarjs/cognitive-complexity", "max-depth"):
            later.append((t, value))
    _fold_later(fns, later)
    return fns


def _fold_later(fns: dict, later: list):
    for t, value in later:
        fn = _innermost(fns, t["file"], t["line"])
        if fn is not None:
            key = "nesting" if t["rule"] == "max-depth" else "cognitive"
            fn[key] = max(fn[key], value)


CORE = {"max-lines-per-function": "lines", "complexity": "cyclomatic", "max-params": "params"}


def _core_value(fns: dict, t: dict, value: int):
    fn = fns.setdefault((t["file"], t["line"]), dict(file=t["file"], line=t["line"], end=t["end"], name=None, kind="function", lines=0, cyclomatic=1, cognitive=0, params=0, nesting=0))
    fn["kind"] = _kind(t["what"]); fn["name"] = (NAMED.match(t["what"]) or [None, None])[1] or fn["name"]
    fn[CORE[t["rule"]]] = value
    if t["rule"] == "max-lines-per-function":
        fn["end"] = t["line"] + value - 1   # ESLint's report ends on its start line; the line count gives the span


def _innermost(fns: dict, file: str, line: int):
    inner = [f for f in fns.values() if f["file"] == file and f["line"] <= line <= f["end"]]
    return max(inner, key=lambda f: f["line"]) if inner else None


# ---- pairing ----------------------------------------------------------------------------------------------------

def pair(ours: list, theirs: dict) -> list:
    """(ours, eslint) pairs: the innermost ESLint function whose span holds ours' brace line (a head may span lines),
    the same name when both have one, each ESLint function used once."""
    by_file = {}
    for fn in theirs.values():
        by_file.setdefault(fn["file"], []).append(fn)
    taken, pairs = set(), []
    for r in ours:
        cands = [f for f in by_file.get(r["file"], []) if (f["file"], f["line"]) not in taken and f["line"] <= r["line"] <= f["end"] and f["name"] in (None, r["name"])]
        if cands:
            f = max(cands, key=lambda f: (f["name"] == r["name"], f["line"])); taken.add((f["file"], f["line"])); pairs.append((r, f))
    return pairs


def _source_line(tmp: Path, file: str, line: int) -> str:
    try:
        return (tmp / file).read_text(encoding="utf-8", errors="replace").splitlines()[line - 1].strip()[:110]
    except (OSError, IndexError):
        return ""


def metric_table(pairs: list) -> dict:
    return {k: _metric_row(pairs, k) for k in METRICS}


def _metric_row(pairs: list, k: str) -> dict:
    lim = LIMITS[k]
    diffs = [(r[k] - f[k], r, f) for r, f in pairs]
    show = lambda r, f: f"{r['file']}:{r['name']} ours {r[k]} eslint {f[k]}"
    row = dict(equal=sum(d == 0 for d, _, _ in diffs), within_one=sum(abs(d) == 1 for d, _, _ in diffs), apart=sum(abs(d) > 1 for d, _, _ in diffs),
               worst=[show(r, f) for d, r, f in sorted(diffs, key=lambda x: -abs(x[0]))[:6] if abs(d) > 1])
    row.update(_over_limit(pairs, k, lim, show))
    return row


def _over_limit(pairs: list, k: str, lim: int, show) -> dict:
    return dict(ours_over=sum(r[k] > lim for r, _ in pairs), eslint_over=sum(f[k] > lim for _, f in pairs), both_over=sum(r[k] > lim and f[k] > lim for r, f in pairs),
                ours_only=[show(r, f) for r, f in pairs if r[k] > lim >= f[k]], eslint_only=[show(r, f) for r, f in pairs if f[k] > lim >= r[k]])


def line_rows(rows: list, items: list, tmp: Path) -> dict:
    return {title: _line_row(rows, items, tmp, selector, rule) for title, selector, rule in LINE_ROWS}


def _line_row(rows: list, items: list, tmp: Path, selector: str, rule: str) -> dict:
    ours = {(r["file"], line) for r in rows for line, msg in r["hygiene"] if selector in msg}
    theirs = {(t["file"], t["line"]) for t in items if t["rule"] == rule and (rule != "no-empty" or _is_catch(tmp, t))}
    return dict(ours=len(ours), eslint=len(theirs), both=len(ours & theirs), ours_only=sorted(f"{f}:{ln}" for f, ln in ours - theirs),
                eslint_only=sorted(f"{f}:{ln}  {_message(items, f, ln, rule)}" for f, ln in theirs - ours))


def _is_catch(tmp: Path, t: dict) -> bool:
    return "catch" in (tmp / t["file"]).read_text(encoding="utf-8", errors="replace").splitlines()[t["line"] - 1]


def _message(items: list, file: str, line: int, rule: str) -> str:
    return next((t["what"] for t in items if t["file"] == file and t["line"] == line and t["rule"] == rule), "")


# ---- one project --------------------------------------------------------------------------------------------------

def bench(name: str) -> dict:
    project = next(p for p in engines.PROJECTS if p["name"] == name)
    tmp = engines.prepare(project)
    rows, ours_secs = run_ours(tmp)
    files = sorted({r["file"] for r in rows})
    items, es_secs = run_eslint(tmp, files)
    ours = [r for r in rows if r["kind"] == "function"]
    theirs = eslint_functions(items)
    pairs = pair(ours, theirs)
    result = dict(project=name, secs=dict(ours=ours_secs, eslint=es_secs), files=len(files), fatal=_fatal(items), functions=_inventory(tmp, ours, theirs, pairs),
                  metrics=metric_table(pairs), file_lines=_file_lines(rows, items), line_rows=line_rows(rows, items, tmp), pairs=_pairs_dump(pairs))
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"jsstyle-{name}.json").write_text(json.dumps(result, indent=1))
    return result


def _fatal(items: list) -> list:
    return [f"{t['file']}:{t['line']} {t['what'][:80]}" for t in items if t["rule"] == "fatal"]


def _pairs_dump(pairs: list) -> list:
    return [dict(file=r["file"], name=r["name"], ours_line=r["line"], eslint_line=f["line"], ours={k: r[k] for k in METRICS}, eslint={k: f[k] for k in METRICS}) for r, f in pairs]


def _inventory(tmp: Path, ours: list, theirs: dict, pairs: list) -> dict:
    paired_ours = {(r["file"], r["line"]) for r, _ in pairs}; paired_theirs = {(f["file"], f["line"]) for _, f in pairs}
    unseen = [f for k, f in theirs.items() if k not in paired_theirs]
    ours_only = [f"{r['file']}:{r['line']} {r['name']}  | {_source_line(tmp, r['file'], r['line'])}" for r in ours if (r["file"], r["line"]) not in paired_ours]
    return dict(ours=len(ours), eslint=len(theirs), paired=len(pairs), ours_only=ours_only[:40], **_unseen_lists(tmp, unseen))


def _unseen_lists(tmp: Path, unseen: list) -> dict:
    by_kind = Counter((f["kind"], "named" if f["name"] else "anonymous") for f in unseen).most_common()
    return dict(eslint_only_by_kind={f"{k} {n}": v for (k, n), v in by_kind},
                eslint_only_sample=[f"{f['file']}:{f['line']} {f['kind']} {f['name'] or '(anonymous)'} {f['lines']} lines" for f in sorted(unseen, key=lambda f: -f["lines"])[:12]],
                eslint_only_named=[f"{f['file']}:{f['line']} {f['kind']} {f['name']}  | {_source_line(tmp, f['file'], f['line'])}" for f in unseen if f["name"]][:40])


def _file_lines(rows: list, items: list) -> dict:
    ours = {r["file"]: r["lines"] for r in rows if r["kind"] == "file"}
    theirs = {t["file"]: int(re.search(r"\((\d+)\)", t["what"]).group(1)) for t in items if t["rule"] == "max-lines"}
    return dict(ours=sum(v > 400 for v in ours.values()), eslint=sum(v > 400 for v in theirs.values()), both=sum(ours.get(f, 0) > 400 and v > 400 for f, v in theirs.items()))


# ---- report -------------------------------------------------------------------------------------------------------

def render(results: list) -> str:
    out = ["| project | files | functions ours | functions ESLint | paired | ESLint-only functions by kind | ours s | ESLint s |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        fn = r["functions"]; kinds = ", ".join(f"{k} {v}" for k, v in sorted(fn["eslint_only_by_kind"].items(), key=lambda kv: -kv[1]))
        out.append(f"| {r['project']} | {r['files']} | {fn['ours']} | {fn['eslint']} | {fn['paired']} | {kinds} | {r['secs']['ours']} | {r['secs']['eslint']} |")
    out += ["", "| metric (paired functions) | project | equal | within 1 | further apart | ours over limit | ESLint over limit | both |", "|---|---|---|---|---|---|---|---|"]
    for k in METRICS:
        for r in results:
            m = r["metrics"][k]
            out.append(f"| {k} > {LIMITS[k]} | {r['project']} | {m['equal']} | {m['within_one']} | {m['apart']} | {m['ours_over']} | {m['eslint_over']} | {m['both_over']} |")
    out += ["", "| row | project | ours | ESLint | both |", "|---|---|---|---|---|"]
    for r in results:
        out.append(f"| file lines > 400 | {r['project']} | {r['file_lines']['ours']} | {r['file_lines']['eslint']} | {r['file_lines']['both']} |")
    for title, *_ in LINE_ROWS:
        for r in results:
            c = r["line_rows"][title]
            out.append(f"| {title} | {r['project']} | {c['ours']} | {c['eslint']} | {c['both']} |")
    return "\n".join(out)


def details(results: list) -> str:
    out = []
    for r in results:
        fn = r["functions"]
        out.append(f"\n== {r['project']}: ESLint could not parse {len(r['fatal'])} file(s) {r['fatal'][:3]}")
        out.append(f"  ESLint-only functions, longest: {fn['eslint_only_sample']}")
        out.append(f"  ours-only functions: {fn['ours_only'][:12]}")
        out.append(f"  ESLint-only named functions: {fn['eslint_only_named'][:12]}")
        for k in METRICS:
            m = r["metrics"][k]
            if m["worst"] or m["ours_only"] or m["eslint_only"]:
                out.append(f"  {k}: furthest apart {m['worst']}; over limit on ours only {m['ours_only'][:8]}; on ESLint only {m['eslint_only'][:8]}")
        for title, c in r["line_rows"].items():
            if c["ours_only"] or c["eslint_only"]:
                out.append(f"  {title}: ours only {c['ours_only'][:10]}; ESLint only ({len(c['eslint_only'])}) {c['eslint_only'][:10]}")
    return "\n".join(out)


def main(argv: list):
    if "--bench" in argv:
        i = argv.index("--bench"); engines.BENCH = Path(argv[i + 1]); del argv[i:i + 2]
    names = [a for a in argv if not a.startswith("--")] or JS_PROJECTS
    results = [bench(n) for n in names]
    print(render(results)); print(details(results))


if __name__ == "__main__":
    main(sys.argv[1:])
