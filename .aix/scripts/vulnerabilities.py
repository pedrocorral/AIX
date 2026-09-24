#!/usr/bin/env python3
"""aix code vulnerabilities — the deep security layer: taint paths, known CVEs, secrets in git history.

  --taint     Python, per file through the parser: input sources (route/handler parameters, request objects, argv,
              environment, stdin) followed through assignments, f-strings, concatenation and calls into functions of
              the same file, to dangerous sinks (shell, eval, SQL, file paths, redirects, template strings,
              deserialisation, outbound requests). Sanitisers (int/float, shlex.quote, escape, secure_filename,
              uuid, parameterised execute, Path.resolve with is_relative_to) clear the taint.
              Result: "input reaches sink" with the path. Static, one call deep across functions, one file at a time.
  --cve       pinned dependencies (requirements, uv/poetry locks, package-lock, pnpm-lock, Cargo.lock) checked in one
              batch against the OSV database (api.osv.dev). Needs the network; stops cleanly and says so otherwise.
  --history   `git log -p` through the secret rules: keys, tokens and hard-coded passwords in past commits (a rotated
              key in history is still a leak). Bounded by --commits N (default 300).
Every finding names the VUL row and CWE it feeds; --audit writes the audit report with the evidence table.
aix: skip-security-scan this file describes sources and sinks and holds the self-test snippets"""
import subprocess, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import ROOT, default_roots
from codesecurity import is_test, register_rows
from taint import taint
from cvecheck import cve, dependencies
from secrethistory import history




# ---- report -------------------------------------------------------------------------------------------------------

def _finding_lines(findings, rows) -> list:
    by_vul = defaultdict(list)
    for f in findings:
        by_vul[f[0]].append(f)
    lines = []
    for vul in sorted(by_vul):
        desc, status = rows.get(vul, ("", "?"))
        lines.append(f"    {vul}  {desc[:60]}  [register: {status}]")
        for _, cwe, what, file, ln, snippet, advice, acc in by_vul[vul][:20]:
            where = f"{file}:{ln}" if ln else file
            tag = f"accepted: {acc}" if acc else "test" if is_test(ROOT / file) else "REVIEW"
            lines.append(f"      {where}  {what} ({cwe})  [{tag}]\n        {snippet}\n        -> {advice}")
    return lines


def render(sections, paths, strict):
    rows = register_rows()
    lines = [f"Code vulnerabilities — {', '.join(paths)}", ""]
    total_live = 0
    for title, findings, note in sections:
        if findings is None:
            lines += [f"  {title}: {note}", ""]
            continue
        total_live += sum(1 for f in findings if not f[7] and (strict or not is_test(ROOT / f[3])))
        lines.append(f"  {title}: {len(findings)} finding(s)" + (f"  ({note})" if note else ""))
        lines += _finding_lines(findings, rows) + [""]
    lines.append("  A taint path is static evidence that input can reach a sink, not a proof of exploitability in production;")
    lines.append("  a CVE applies to the version, not necessarily to how you use it; a history leak is real until the secret is rotated.")
    lines.append("  Fix: taint -> the code (see advice) ; CVE -> upgrade ; history -> rotate now.  `--audit` writes the evidence report.")
    return "\n".join(lines), total_live


def write_audit(all_findings, paths, unreachable):
    rows = register_rows()
    today = date.today().isoformat()
    out = ROOT / "docs" / "security" / "audits" / f"AUDIT-{today}-vulnerabilities.md"
    body = [f"---\nid: AUDIT-{today}-vulnerabilities\nskill: aix code vulnerabilities (taint, CVE, history)\ndate: {today}\nscope: [{', '.join(paths)}]\nresult: {'findings' if all_findings else 'pass'}\n---",
            f"# Audit — deep code checks — {today}", "", "## Method (what was checked, tools run)",
            "`aix code vulnerabilities`: Python taint analysis (input sources to dangerous sinks, one call deep, per file), pinned dependencies against the OSV database"
            + (" (unreachable in this run)" if unreachable else "") + ", secrets in git history. Findings are evidence to review; a quiet check is not proof of absence.", "",
            "## Findings", "| VUL id | Asset / threat | Impact | Likelihood rationale | Control | Verification method | Evidence | Status before → after | Residual risk |", "|---|---|---|---|---|---|---|---|---|"]
    for vul, cwe, what, file, ln, snippet, advice, _ in sorted(all_findings, key=lambda f: (f[0], f[3], f[4])):
        desc, status = rows.get(vul, ("", "?"))
        ev = f"`{file}{':' + str(ln) if ln else ''}` {what} ({cwe}): {snippet[:60]}"
        body.append(f"| {vul} | {desc[:50]} | | {'data flow' if 'reaches' in what else 'known CVE' if 'vulnerability' in what else 'history'} | {advice[:60]} | code review / upgrade / rotation | {ev} | {status} → confirmed? review | |")
    body += ["", "## New vulnerabilities discovered (added to register)", "- none by this scan", "", "## Follow-ups (tasks created)", "- review every row; fix, upgrade or rotate; re-run", ""]
    out.write_text("\n".join(body), encoding="utf-8")
    idx = out.parent / "INDEX.md"
    if idx.exists() and out.name not in idx.read_text(encoding="utf-8"):
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(f"| `{out.name}` | Deep code checks (`aix code vulnerabilities`), {len(all_findings)} findings | Verifying VUL statuses; release |\n")
    return out


# ---- self-test ---------------------------------------------------------------------------------------------------------

SELFTEST_APP = '''
import subprocess, os, shlex
from flask import request, redirect
BASE = "/srv"
def helper(cmd):
    return subprocess.run(cmd, shell=True)
def run_argv():
    return subprocess.run(["ls", request.args.get("d")])
@app.route("/x")
def handler():
    name = request.args.get("name")
    helper("ls " + name)
    n = int(request.args.get("n"))
    subprocess.run("x" + str(n), shell=True)
    safe = shlex.quote(name)
    subprocess.run("ls " + safe, shell=True)
    path = os.path.join(BASE, request.args["f"])
    return open(path).read()
@app.route("/r")
def go(target: str):
    return redirect(target)
def sql(cur, uid):
    cur.execute("SELECT 1 WHERE id = ?", (uid,))
def reviewed():
    return open(request.args["p"]).read()  # aix: accepted VUL-INJ-002 demo
'''


def _selftest_project(base: Path):
    """A throwaway project with a taint sample, a pinned requirement and a leaked password in history."""
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    (base / "app.py").write_text(SELFTEST_APP, encoding="utf-8")
    (base / "requirements.txt").write_text("requests==2.19.0\nflask\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=base); subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], cwd=base)
    (base / "cfg.py").write_text('password = "hunter2xyz"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=base); subprocess.run([*git, "commit", "-q", "-m", "leak"], cwd=base)


def _selftest_run():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        _selftest_project(base)
        return taint([str(base)]), dependencies(base), history(50, base)


def _selftest_checks(taints, deps, history) -> list:
    """(name, passed) for every expectation on the built-in snippets."""
    kinds = sorted(f[2] + "@" + str(f[4]) for f in taints)
    hit = lambda k: k in kinds
    return [("taint: helper() shell via argument", hit("input reaches shell command@6")),
            ("taint: open(path) from request", hit("input reaches file path@18")),
            ("taint: redirect(target) from route param", hit("input reaches redirect target@21")),
            ("taint: int() sanitises", not hit("input reaches shell command@13")),
            ("taint: shlex.quote sanitises", not hit("input reaches shell command@15")),
            ("taint: argument list, no shell", not hit("input reaches shell command@8")),
            ("taint: parameterised SQL not flagged", not any("SQL" in k for k in kinds)),
            ("taint: accepted marker kept with its reason", any(f[4] == 25 and f[7] == "demo" for f in taints)),
            ("deps: pinned requests parsed, unpinned flask ignored", [(e, n, v) for e, n, v, _ in deps] == [("PyPI", "requests", "2.19.0")]),
            ("history: hard-coded password in a past commit", history is not None and len(history) == 1 and "cfg.py" in history[0][3])], kinds


def selftest():
    """Run the taint, dependency and history checks on the built-in snippets; exit 1 on any failure."""
    checks, kinds = _selftest_checks(*_selftest_run())
    failed = sum(not ok for _, ok in checks)
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print("  taint kinds seen:", kinds)
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code vulnerabilities [PATH...] [--taint] [--cve] [--history] [--commits N] [--strict] [--gate] [--audit] [--report] [--selftest]"


def _sections(modes, paths, commits):
    """The report sections for the chosen modes; unreachable = OSV could not be queried."""
    sections, unreachable = [], False
    if "--taint" in modes:
        sections.append(("taint paths (Python)", taint(paths), "input sources followed to sinks, one call deep, per file"))
    if "--cve" in modes:
        found, n = cve(paths)
        unreachable = found is None
        note = f"OSV unreachable (network); {n} pinned dependencies not checked" if unreachable else f"{n} pinned dependencies queried"
        sections.append(("known CVEs (OSV)", found, note))
    if "--history" in modes:
        h = history(commits)
        sections.append(("secrets in git history", h, f"last {commits} commits, all branches" if h is not None else "no git repository"))
    return sections, unreachable


def _write_outputs(text: str, sections, paths, unreachable: bool, args):
    if "--report" in args:
        out = ROOT / "docs" / "tests" / "code-vulnerabilities.md"
        out.write_text("# Code vulnerabilities (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if "--audit" in args:
        all_findings = [f for _, fs, _ in sections if fs for f in fs]
        print(f"\n  wrote {write_audit(all_findings, paths, unreachable).relative_to(ROOT)}  (complete the Status column after review)")


def _gate(n_live: int, unreachable: bool):
    if n_live:
        sys.exit(f"GATE FAILED: {n_live} finding(s) to review")
    print("GATE PASSED" + ("  (CVE check skipped: OSV unreachable)" if unreachable else ""))


def _commits_flag(args, default=300) -> int:
    """Remove `--commits N` from args (in place) and return N."""
    if "--commits" not in args:
        return default
    i = args.index("--commits"); value = int(args[i + 1]); del args[i:i + 2]
    return value


def main(args):
    if "--selftest" in args:
        return selftest()
    modes = {m for m in ("--taint", "--cve", "--history") if m in args} or {"--taint", "--cve", "--history"}
    commits = _commits_flag(args)
    paths = [a for a in args if not a.startswith("--")] or default_roots()
    sections, unreachable = _sections(modes, paths, commits)
    text, n_live = render(sections, paths, "--strict" in args)
    print(text)
    _write_outputs(text, sections, paths, unreachable, args)
    if "--gate" in args:
        _gate(n_live, unreachable)


if __name__ == "__main__":
    main(sys.argv[1:])
