#!/usr/bin/env python3
"""Generate docs/tests/coverage-matrix.md: requirement -> test specs -> code markers.
Reads IDs from docs front-matter and grep-scans code roots for @implements / @tests / @mitigates markers.
This is the ONLY sanctioned 'whole project' scan; it is cheap (regex, no LLM) and produces a small table."""
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOTS = ["backend", "frontend", "shared", "infra", "src", "app", "tests"]
SKIP = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git"}
MARK = re.compile(r"@(implements|tests|mitigates)\s+([A-Z]+-[A-Z0-9]+(?:-\d{3,4})?(?:\s*,\s*[A-Z]+-[A-Z0-9]+(?:-\d{3,4})?)*)")


def fm_ids(folder, prefix):
    out = {}
    for md in (ROOT / folder).rglob("*.md"):
        t = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"^id:\s*({prefix}-[A-Z0-9-]+)", t, re.M)
        if m:
            cov = re.search(r"^covers:\s*\[?([^\]\n]*)", t, re.M)
            out[m.group(1)] = (md.relative_to(ROOT), [c.strip() for c in cov.group(1).split(",")] if cov else [])
    return out


def fm_status(folder, prefix):
    """id -> front-matter status for every doc with that ID prefix."""
    out = {}
    for md in (ROOT / folder).rglob("*.md"):
        t = md.read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"^id:\s*({prefix}-[A-Z0-9-]+)", t, re.M)
        s = re.search(r"^status:\s*([a-z-]+)", t, re.M)
        if m and s:
            out[m.group(1)] = s.group(1)
    return out


def status_drift():
    """Docs that claim more than the code shows. Errors: a status nobody can reach without a marker.
    FR/NFR/API `implemented`|`verified` need @implements; TS `automated` needs @tests; VUL `mitigated` needs @mitigates."""
    code = scan_code()
    errs = []
    for prefix in ("FR", "NFR", "API"):
        for rid, st in fm_status("docs/requirements", prefix).items():
            if st in ("implemented", "verified") and rid not in code:
                errs.append(f"{rid} is `{st}` but no code carries `@implements {rid}`")
    for tid, st in fm_status("docs/tests", "TS").items():
        if st == "automated" and tid not in code:
            errs.append(f"{tid} is `automated` but no test carries `@tests {tid}`")
    for vid, st in fm_status("docs/security", "VUL").items():
        if st == "mitigated" and vid not in code:
            errs.append(f"{vid} is `mitigated` but no code carries `@mitigates {vid}`")
    return errs


def scan_code():
    hits = defaultdict(set)
    for root in CODE_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_dir() or any(s in f.parts for s in SKIP) or f.suffix in {".png", ".jpg", ".lock", ".min.js"}:
                continue
            try:
                for m in MARK.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                    for rid in re.split(r"\s*,\s*", m.group(2)):
                        hits[rid].add(str(f.relative_to(ROOT)))
            except Exception:
                pass
    return hits


if __name__ == "__main__":
    reqs = {**fm_ids("docs/requirements", "FR"), **fm_ids("docs/requirements", "NFR"), **fm_ids("docs/requirements", "API")}
    tests = fm_ids("docs/tests", "TS")
    vuls = fm_ids("docs/security", "VUL")
    code = scan_code()
    by_req = defaultdict(list)
    for tid, (_, covers) in tests.items():
        for r in covers:
            by_req[r].append(tid)
    lines = ["# Coverage matrix (generated — do not edit)", "",
             "| Requirement | Test specs | Implemented in | Tested in | Gap |", "|---|---|---|---|---|"]
    for rid in sorted(reqs):
        ts = by_req.get(rid, [])
        impl = sorted(code.get(rid, []))
        tested = sorted({f for t in ts for f in code.get(t, [])})
        gap = []
        if not ts: gap.append("no test spec")
        if not impl: gap.append("no code")
        if ts and not tested: gap.append("spec not automated")
        lines.append(f"| {rid} | {', '.join(ts) or '—'} | {', '.join(impl) or '—'} | {', '.join(tested) or '—'} | {', '.join(gap) or 'ok'} |")
    orphans = [t for t, (_, c) in tests.items() if not c or all(r not in reqs for r in c)]
    if orphans:
        lines += ["", "## Orphan test specs (no valid requirement)", *[f"- {t}" for t in sorted(orphans)]]
    mit = [f"- {v}: {', '.join(sorted(code[v]))}" for v in sorted(vuls) if v in code]
    lines += ["", "## Vulnerability mitigations found in code", *(mit or ["- none"])]
    out = ROOT / "docs" / "tests" / "coverage-matrix.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(reqs)} requirements, {len(tests)} test specs)")
