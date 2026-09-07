#!/usr/bin/env python3
"""aix code stats — distribution of function sizes (or any style metric) as a terminal histogram, plus the offenders.

Reuses the per-function records of `aix code style` (Python exact; JS/TS, Rust, Java approximate).
  histogram   fixed, comparable bins scaled to the terminal width; the limit from .aix/config.yaml is marked
  numbers     count, mean, standard deviation, median, p90, p95, max, share over the limit
  offenders   top functions by the metric, files and folders by how many functions they push over the limit
--metric lines (default) | cognitive | cyclomatic | nesting | params"""
import math, shutil, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import CODE_ROOTS, ROOT, rel, source_files
from style import functions_in, limit, thresholds

BINS = {
    "lines": [(1, 5), (6, 10), (11, 20), (21, 30), (31, 40), (41, 60), (61, 100), (101, 200), (201, None)],
    "cognitive": [(0, 0), (1, 2), (3, 5), (6, 10), (11, 15), (16, 25), (26, 50), (51, None)],
    "cyclomatic": [(1, 1), (2, 3), (4, 5), (6, 10), (11, 15), (16, 25), (26, 50), (51, None)],
    "nesting": [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, None)],
    "params": [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 7), (8, None)],
}
LABEL = {"lines": "lines per function", "cognitive": "cognitive complexity", "cyclomatic": "cyclomatic complexity",
         "nesting": "nesting depth", "params": "parameters"}
BAR, HALF = "█", "▌"


# ---- numbers -------------------------------------------------------------------------------------------------------

def describe(values):
    n = len(values)
    if n == 0:
        return {}
    s = sorted(values)
    mean = sum(s) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in s) / (n - 1)) if n > 1 else 0.0
    pct = lambda p: s[min(n - 1, int(round(p * (n - 1))))]
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return dict(n=n, mean=mean, sd=sd, median=median, p90=pct(0.9), p95=pct(0.95), max=s[-1], min=s[0])


def bin_counts(values, edges):
    counts = [0] * len(edges)
    for v in values:
        for i, (lo, hi) in enumerate(edges):
            if v >= lo and (hi is None or v <= hi):
                counts[i] += 1
                break
    return counts


def bar(count, biggest, width):
    """A bar scaled to `width` cells; half blocks give twice the resolution."""
    if biggest == 0:
        return ""
    cells = count / biggest * width
    full = int(cells)
    return BAR * full + (HALF if cells - full >= 0.5 else "")


def histogram(values, metric, lim, width):
    edges = BINS[metric]
    counts = bin_counts(values, edges)
    biggest = max(counts) if counts else 0
    label_w = 10
    bar_w = max(10, width - label_w - 14)
    lines = []
    for (lo, hi), c in zip(edges, counts):
        label = f"{lo}-{hi}" if hi is not None and hi != lo else (f"{lo}+" if hi is None else f"{lo}")
        over = lim is not None and lo > lim
        straddle = lim is not None and hi is not None and lo <= lim < hi
        mark = "  <- over the limit" if over else ("  <- limit inside this bin" if straddle else "")
        lines.append(f"  {label:>{label_w}} {bar(c, biggest, bar_w)} {c}{mark}")
    return lines


# ---- offenders -----------------------------------------------------------------------------------------------------

def offenders(fxs, metric, th, top=10):
    key = lambda fx: fx[metric]
    worst = sorted(fxs, key=key, reverse=True)[:top]
    over = [fx for fx in fxs if fx[metric] > limit(fx, th, metric)]
    by_file, by_folder = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0, 0])   # [functions, over, excess]
    for fx in fxs:
        lim = limit(fx, th, metric)
        f = fx["file"]
        d = "/".join(Path(f).parts[:2]) if len(Path(f).parts) > 2 else str(Path(f).parent)
        for bucket in (by_file[f], by_folder[d]):
            bucket[0] += 1
            if fx[metric] > lim:
                bucket[1] += 1; bucket[2] += fx[metric] - lim
    files = sorted(by_file.items(), key=lambda kv: (-kv[1][1], -kv[1][2]))[:5]
    folders = sorted(by_folder.items(), key=lambda kv: (-kv[1][1], -kv[1][2]))[:5]
    return worst, over, files, folders


# ---- report ----------------------------------------------------------------------------------------------------------

def render(fxs, metric, th, width, paths):
    values = [fx[metric] for fx in fxs]
    d = describe(values)
    if not d:
        return f"Code stats — {', '.join(paths)}\n\n  no functions found", 0
    lim = th.get("max_" + metric)
    over = sum(1 for fx in fxs if fx[metric] > limit(fx, th, metric))
    head = [f"Code stats — {LABEL[metric]} — {', '.join(paths)}", "",
            f"  functions {d['n']}   mean {d['mean']:.1f}   sd {d['sd']:.1f}   median {d['median']:g}   p90 {d['p90']}   p95 {d['p95']}   max {d['max']}"
            + (f"   limit {lim}: {over} over ({over / d['n'] * 100:.1f} %)" if lim is not None else ""), ""]
    body = histogram(values, metric, lim, width)
    worst, over_fx, files, folders = offenders(fxs, metric, th)
    tail = ["", f"  largest functions ({LABEL[metric]}):"]
    for fx in worst:
        flag = " *" if fx[metric] > limit(fx, th, metric) else ""
        tail.append(f"    {fx[metric]:>5}{flag:2}  {fx['file']}:{fx['name']}  (line {fx['line']})")
    if any(v[1] for _, v in files):
        tail.append("  files pushing most functions over the limit (functions over / total, excess):")
        for f, (n, o, ex) in files:
            if o:
                tail.append(f"    {o:>3} / {n:<3}  +{ex:<5} {f}")
    if any(v[1] for _, v in folders):
        tail.append("  folders (depth 2):")
        for f, (n, o, ex) in folders:
            if o:
                tail.append(f"    {o:>3} / {n:<3}  +{ex:<5} {f}/")
    tail.append(f"  * = over its limit.  Detail: aix code style FILE:FUNCTION   Other metrics: --metric cognitive | cyclomatic | nesting | params")
    return "\n".join(head + body + tail), over


# ---- self-test --------------------------------------------------------------------------------------------------------

def selftest():
    vals = [2, 4, 4, 4, 5, 5, 7, 9]  # classic: mean 5, population sd 2 -> sample sd 2.138
    d = describe(vals)
    checks = [("mean", round(d["mean"], 3), 5.0), ("sample sd", round(d["sd"], 3), 2.138), ("median (even count)", d["median"], 4.5),
              ("max", d["max"], 9), ("bins lines", bin_counts(vals, BINS["lines"]), [6, 2, 0, 0, 0, 0, 0, 0, 0]),
              ("bar full width", bar(10, 10, 20), BAR * 20), ("bar half", bar(1, 4, 10), BAR * 2 + HALF), ("bar zero", bar(0, 10, 20), "")]
    failed = 0
    for name, got, want in checks:
        ok = got == want; failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got} (expected {want})")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code stats [PATH...] [--metric lines|cognitive|cyclomatic|nesting|params] [--report] [--selftest]"


def main(args):
    if "--selftest" in args:
        return selftest()
    metric = "lines"
    if "--metric" in args:
        i = args.index("--metric"); metric = args[i + 1]; del args[i:i + 2]
    if metric not in BINS:
        sys.exit(USAGE)
    report = "--report" in args
    paths = [a for a in args if not a.startswith("--")] or [r for r in CODE_ROOTS if (ROOT / r).exists()]
    fxs = []
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            fxs += functions_in(f)
    width = shutil.get_terminal_size((100, 20)).columns
    text, _ = render(fxs, metric, thresholds(), width, paths)
    print(text)
    if report:
        out = ROOT / "docs" / "tests" / "code-stats.md"
        out.write_text("# Code stats (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
