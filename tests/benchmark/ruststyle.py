"""Rust style: `aix code style` against two references on ripgrep and bat. rust-code-analysis (Mozilla) implements
SonarSource's cognitive complexity and reports per function cognitive, nargs and sloc (every line of the span, as ours
counts); clippy's cognitive_complexity, too_many_arguments and too_many_lines lints, every threshold at its minimum so
clippy reports a value per function, are a second column (clippy's lint is its own algorithm, not SonarSource's; its
line count leaves out blank and comment lines; its argument count includes `self`). Functions are paired by file and
the line of the `fn` head. Not part of the test suite.
Needs the JSON lines of `cargo clippy --message-format json` run beforehand on a copy of the project (a toolchain with
clippy, the project compiled), passed as --clippy FILE, and BENCH_DIR/rust/cargo/bin/rust-code-analysis-cli; ours is
read from the cached clone itself. Usage: python3 tests/benchmark/ruststyle.py PROJECT --clippy FILE"""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

LIMITS = dict(cognitive=15, params=5, lines=60)
LINT = {"clippy::cognitive_complexity": "cognitive", "clippy::too_many_arguments": "params", "clippy::too_many_lines": "lines"}


def clippy_functions(path: Path) -> dict:
    """(file, line of fn) -> {metric: value} from clippy's JSON lines."""
    out = {}
    for line in path.read_text().splitlines():
        d = json.loads(line)
        if d.get("reason") != "compiler-message":
            continue
        m = d["message"]; code = (m.get("code") or {}).get("code")
        if code in LINT and m.get("spans"):
            value = int(re.search(r"\((\d+)/", m["message"]).group(1))
            out.setdefault((m["spans"][0]["file_name"], m["spans"][0]["line_start"]), {})[LINT[code]] = value
    return out


def rca_functions(root: Path, files: list) -> dict:
    """(file, line of fn) -> {cognitive, params, lines} from rust-code-analysis, one run per file."""
    cli = engines.BENCH / "rust" / "cargo" / "bin" / "rust-code-analysis-cli"
    out = {}
    for file in files:
        r = subprocess.run([str(cli), "-m", "-O", "json", "-p", str(root / file)], capture_output=True, text=True)
        if r.stdout.strip():
            _walk(json.loads(r.stdout), file, out)
    return out


def _walk(node: dict, file: str, out: dict):
    if node.get("kind") == "function" and node.get("name") != "<anonymous>":
        m = node["metrics"]
        out[(file, node["start_line"])] = dict(cognitive=int(m["cognitive"]["sum"]), params=int(m["nargs"].get("total_functions", m["nargs"].get("sum", 0))), lines=int(m["loc"]["sloc"]))
    for child in node.get("spaces", []):
        _walk(child, file, out)


def ours_functions(root: Path) -> list:
    code = ("import sys, json; sys.path.insert(0, %r); from pathlib import Path; import stylemetrics as sm; from codefiles import source_files\n"
            "rows = [dict(file=str(f.relative_to(%r)), head=fx['head_line'], name=fx['name'], cognitive=fx['cognitive'], params=fx['params'], lines=fx['lines'], line=fx['line']) for f in sorted(source_files([%r])) if f.suffix == '.rs' for fx in sm.functions_in(f)]\n"
            "print(json.dumps(rows))") % (str(engines.KIT / ".aix" / "scripts"), str(root), str(root))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    if not r.stdout:
        sys.exit(r.stderr[-1500:])
    return json.loads(r.stdout)


def compare(ours: list, theirs: dict) -> dict:
    keys = {(r["file"], r["head"]) for r in ours}
    pairs = [(r, theirs[(r["file"], r["head"])]) for r in ours if (r["file"], r["head"]) in theirs]
    unpaired_ours = [f"{r['file']}:{r['name']} (l.{r['head']})" for r in ours if (r["file"], r["head"]) not in theirs]
    return dict(ours=len(ours), clippy=len(theirs), paired=len(pairs), unpaired_ours=unpaired_ours[:10],
                unpaired_clippy=[f"{f}:{ln}" for f, ln in theirs if (f, ln) not in keys][:10], metrics={k: _metric(pairs, k, lim) for k, lim in LIMITS.items()})


def _metric(pairs: list, k: str, lim: int) -> dict:
    diffs = [(r[k] - v[k], r, v[k]) for r, v in pairs if k in v]
    apart = [f"{r['file']}:{r['name']} (l.{r['head']}) ours {r[k]} clippy {v}" for d, r, v in sorted(diffs, key=lambda x: -abs(x[0])) if abs(d) > 1]
    return dict(**_agreement(diffs), apart_list=apart[:12], **_over(diffs, k, lim))


def _agreement(diffs: list) -> dict:
    return dict(equal=sum(d == 0 for d, _, _ in diffs), within_one=sum(abs(d) == 1 for d, _, _ in diffs), apart=sum(abs(d) > 1 for d, _, _ in diffs))


def _over(diffs: list, k: str, lim: int) -> dict:
    return dict(ours_over=sum(r[k] > lim for _, r, _ in diffs), clippy_over=sum(v > lim for _, _, v in diffs), both_over=sum(r[k] > lim and v > lim for _, r, v in diffs))


def _print(name: str, ref: str, c: dict):
    print(f"| {name} vs {ref} | functions ours {c['ours']} | {ref} {c['clippy']} | paired {c['paired']} |")
    print("| metric | equal | within 1 | further apart | ours over | theirs over | both |"); print("|---|---|---|---|---|---|---|")
    for k, m in c["metrics"].items():
        print(f"| {k} > {LIMITS[k]} | {m['equal']} | {m['within_one']} | {m['apart']} | {m['ours_over']} | {m['clippy_over']} | {m['both_over']} |")
    for k, m in c["metrics"].items():
        print(f"== {ref} {k} apart: {m['apart_list'][:8]}")
    print(f"== {ref} unpaired ours: {c['unpaired_ours'][:6]}"); print(f"== {ref} unpaired theirs: {c['unpaired_clippy'][:6]}"); print()


def main(argv: list):
    name = argv[0]; clippy = Path(argv[argv.index("--clippy") + 1])
    root = next(engines.CACHE.glob(f"{name}-*"))
    ours = ours_functions(root)
    files = sorted({r["file"] for r in ours})
    result = dict(project=name, clippy=compare(ours, clippy_functions(clippy)), rca=compare(ours, rca_functions(root, files)))
    engines.OUT.mkdir(parents=True, exist_ok=True)
    (engines.OUT / f"ruststyle-{name}.json").write_text(json.dumps(result, indent=1))
    for ref in ("rca", "clippy"):
        _print(name, ref, result[ref])


if __name__ == "__main__":
    main(sys.argv[1:])
