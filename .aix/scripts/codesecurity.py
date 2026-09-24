#!/usr/bin/env python3
"""aix code security — deterministic static checks mapped to the vulnerability register, producing audit evidence.

Every rule names the VUL row it feeds and the CWE it detects. A match is a FINDING TO REVIEW, never proof of
exploitability; a clean scan is not proof of absence. Rules follow bandit, semgrep, gitleaks and
eslint-plugin-security; categories follow the OWASP Top 10 and the seeded register.

Suppress a reviewed finding in place with a comment on the same line:  # aix: accepted VUL-INJ-002 <why>
Suppressions are listed, never hidden. `--audit` writes docs/security/audits/AUDIT-<date>-code.md with the findings
table filled in: the evidence `aix docs security` requires before a status may change.
aix: skip-security-scan this file holds the rule patterns and the known-bad self-test snippets"""
import re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import ROOT, default_roots, SKIP, rel
import assembled
from securityrules import ACCEPT, DOCKER_RULES, LANG, MARKER_LINES, RULES, SKIP_FILE, TEXT_EXT
from depscan import scan_dependencies


# ---- scanning -----------------------------------------------------------------------------------------------------

def is_test(p: Path) -> bool:
    return any(part in ("tests", "test", "__tests__", "fixtures") for part in p.parts) or p.name.startswith("test_") \
        or ".test." in p.name or ".spec." in p.name


LITERAL = r"(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`[^`]*`)"


def strip_comment(line: str, lang: str) -> str:
    """The line without its trailing comment; a `#` or `//` inside a string literal (a URL, a colour) is not one."""
    if lang is None:
        return line
    marker = r"#.*$" if lang == "py" else r"//.*$|/\*.*?\*/"
    return re.sub(LITERAL + "|" + marker, lambda m: m.group(1) or "", line)


def _skip_marker(lines, f: Path):
    for raw in lines[:MARKER_LINES]:
        m = SKIP_FILE.search(raw)
        if m:
            return ("SKIPPED", "", "file skipped by marker", rel(f), 1, "aix: skip-security-scan " + m.group(1).strip(), "", "skip")
    return None


def _line_findings(f: Path, i: int, raw: str, lang, langs: set):
    acc = ACCEPT.search(raw)
    code = strip_comment(raw, lang)
    for vul, cwe, title, rlangs, rx, advice in RULES:
        if rlangs & langs and re.search(rx, code):
            accepted = f"{acc.group(1)} {acc.group(2).strip()}".strip() if acc and acc.group(1) == vul else None
            yield (vul, cwe, title, rel(f), i, raw.strip()[:110], advice, accepted)


def scan_file(f: Path):
    """[(vul, cwe, title, file, line_no, snippet, advice, accepted)]"""
    lang = LANG.get(f.suffix)
    langs = {lang, "*"} if lang else {"*"}
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    skipped = _skip_marker(lines, f)
    if skipped:
        return [skipped]
    found = [fx for i, raw in enumerate(lines, 1) for fx in _line_findings(f, i, raw, lang, langs)]
    return found + (assembled.findings(f, lines, lang, lambda l: strip_comment(l, lang)) if lang else [])


def scan_dockerfile(f: Path):
    text = f.read_text(encoding="utf-8", errors="replace")
    out = []
    if re.search(r"^\s*FROM\b", text, re.M) and not re.search(r"^\s*USER\s+(?!root\b)\w", text, re.M):
        out.append(("VUL-INFRA-001", "CWE-250", DOCKER_RULES[0][2], rel(f), 1, "no USER instruction", DOCKER_RULES[0][3], None))
    for m in re.finditer(r"^\s*FROM\s+([^\s]+)", text, re.M):
        image = m.group(1)
        if image.lower() not in ("scratch",) and not re.search(r"@sha256:|:[\w.-]+$", image) or image.endswith(":latest"):
            out.append(("VUL-DEP-001", "CWE-1104", DOCKER_RULES[1][2], rel(f), text.count("\n", 0, m.start()) + 1, m.group(0).strip(), DOCKER_RULES[1][3], None))
    return out


ENV_FILES = (".env", ".env.local", ".env.production")


def _scan_target(f: Path):
    """The findings of one file, by its kind: a Dockerfile, a text file with rules, or nothing."""
    if f.name.startswith("Dockerfile") or f.name.endswith(".dockerfile"):
        return scan_dockerfile(f)
    if f.name != ".env.example" and (f.suffix in TEXT_EXT or f.name in ENV_FILES):
        return scan_file(f)
    return []


def _files_of(root: str):
    base = (ROOT / root) if not Path(root).is_absolute() else Path(root)
    if not base.exists():
        return
    if base.is_file():
        yield base
        return
    for f in base.rglob("*"):
        if f.is_file() and not any(s in f.relative_to(base).parts for s in SKIP):
            yield f


def _dedupe(findings):
    seen, out = set(), []
    for fx in findings:
        key = (fx[0], fx[3], fx[4], fx[2])
        if key not in seen:
            seen.add(key); out.append(fx)
    return out


def scan(paths):
    findings = [fx for root in paths for f in _files_of(root) for fx in _scan_target(f)]
    for root in {ROOT} | {(ROOT / r) for r in paths if (ROOT / r).is_dir()}:
        findings += scan_dependencies(root)
    return _dedupe(findings)


# ---- reporting ----------------------------------------------------------------------------------------------------

def register_rows():
    reg = ROOT / "docs" / "security" / "vulnerability-register.md"
    rows = {}
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            if line.startswith("| VUL-"):
                c = [x.strip() for x in line.strip("|").split("|")]
                rows[c[0]] = (c[1], c[3])
    return rows


def _group(findings):
    by_vul = defaultdict(list)
    for fx in findings:
        by_vul[fx[0]].append(fx)
    return by_vul


def _vul_lines(vul: str, fxs: list, rows: dict) -> list:
    desc, status = rows.get(vul, ("(not in register)", "?"))
    lines = [f"  {vul}  {desc[:70]}  [register: {status}]"]
    for _, cwe, title, file, ln, snippet, advice, acc in sorted(fxs, key=lambda x: (x[3], x[4]))[:25]:
        tag = "accepted: " + acc if acc else ("test" if is_test(ROOT / file) else "REVIEW")
        lines += [f"    {file}:{ln}  {title} ({cwe})  [{tag}]", f"      {snippet}"]
        if not acc:
            lines.append(f"      -> {advice}")
    if len(fxs) > 25:
        lines.append(f"    ... {len(fxs) - 25} more")
    return lines + [""]


def _summary_line(live, tests, accepted, covered, by_vul) -> str:
    return (f"  findings to review {len(live)}" + (f"; in tests (not gated, --strict to gate) {len(tests)}" if tests else "")
            + (f"; accepted in code {len(accepted)}" if accepted else "") + f"; register rows with rules {len(covered)}, with findings {len(by_vul)}")


def _classify(findings, strict: bool):
    """(to review, in tests, accepted) among the real findings."""
    live = [fx for fx in findings if not fx[7] and (strict or not is_test(ROOT / fx[3]))]
    tests = [fx for fx in findings if not fx[7] and is_test(ROOT / fx[3])]
    accepted = [fx for fx in findings if fx[7]]
    return live, tests, accepted


def _closing_lines(covered, by_vul, skipped) -> list:
    lines = [f"  skipped by marker: {fx[3]}  ({fx[5]})" for fx in skipped]
    lines.append("  no pattern matched for: " + ", ".join(v for v in covered if v not in by_vul) + "  (rules ran; absence of a match is not evidence of absence)")
    lines.append("  next: review each REVIEW line; fix or mark `# aix: accepted VUL-… <why>`; `aix code security --audit` writes the audit report;")
    lines.append("        then `aix docs security` / the security-audit-* skills move register rows on that evidence.")
    return lines


def _by_open_count(by_vul) -> list:
    return sorted(by_vul, key=lambda v: (-len([f for f in by_vul[v] if not f[7]]), v))


def render(findings, paths, strict):
    """(report text, number of findings to review) for the scan of `paths`."""
    rows = register_rows()
    covered = sorted({r[0] for r in RULES} | {r[0] for r in DOCKER_RULES})
    skipped = [fx for fx in findings if fx[0] == "SKIPPED"]
    findings = [fx for fx in findings if fx[0] != "SKIPPED"]
    by_vul = _group(findings)
    live, tests, accepted = _classify(findings, strict)
    lines = [f"Code security — {', '.join(paths)}", "", _summary_line(live, tests, accepted, covered, by_vul),
             "  A match is a finding to review, not proof of exploitability; a clean row is not proof of absence.", ""]
    for vul in _by_open_count(by_vul):
        lines += _vul_lines(vul, by_vul[vul], rows)
    return "\n".join(lines + _closing_lines(covered, by_vul, skipped)), len(live)


AUDIT_TABLE_HEAD = ("| VUL id | Asset / threat | Impact | Likelihood rationale | Control | Verification method | Evidence | Status before → after | Residual risk |",
                    "|---|---|---|---|---|---|---|---|---|")


def _audit_rows(by_vul, rows, covered) -> list:
    body = []
    for vul in sorted(by_vul):
        desc, status = rows.get(vul, ("", "?"))
        for _, cwe, title, file, ln, _snippet, advice, acc in sorted(by_vul[vul], key=lambda x: (x[3], x[4])):
            after = "accepted (in code)" if acc else "confirmed? review"
            body.append(f"| {vul} | {desc[:50]} | | static match | {advice[:60]} | code review | `{file}:{ln}` {title} ({cwe}) | {status} → {after} | |")
    for vul in [v for v in covered if v not in by_vul]:
        desc, status = rows.get(vul, ("", "?"))
        body.append(f"| {vul} | {desc[:50]} | | no static match | | static scan | no pattern matched | {status} → {status} (unverified by scan alone) | |")
    return body


def _add_index_row(out: Path, n_findings: int, n_covered: int):
    idx = out.parent / "INDEX.md"
    if idx.exists() and out.name not in idx.read_text(encoding="utf-8"):
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(f"| `{out.name}` | Deterministic code scan (`aix code security`), {n_findings} findings, {n_covered} rows checked | Verifying VUL statuses; release |\n")


def write_audit(findings, paths):
    findings = [fx for fx in findings if fx[0] != "SKIPPED"]
    rows = register_rows()
    today = date.today().isoformat()
    out = ROOT / "docs" / "security" / "audits" / f"AUDIT-{today}-code.md"
    by_vul = _group(findings)
    covered = sorted({r[0] for r in RULES} | {r[0] for r in DOCKER_RULES})
    result = "findings" if any(not f[7] for f in findings) else "pass"
    body = [f"---\nid: AUDIT-{today}-code\nskill: aix code security (deterministic scan)\ndate: {today}\nscope: [{', '.join(paths)}]\nresult: {result}\n---",
            f"# Audit — code scan — {today}", "", "## Method (what was checked, tools run)",
            f"`aix code security` static rules ({len(RULES)} line rules + Dockerfile + dependency manifests) mapped to VUL rows and CWEs. "
            "A match is a finding to review; a clean row means no pattern matched, not absence. Human review recorded in the Status column.", "",
            "## Findings", *AUDIT_TABLE_HEAD, *_audit_rows(by_vul, rows, covered),
            "", "## New vulnerabilities discovered (added to register)", "- none by this scan (static rules only match seeded categories)", "",
            "## Follow-ups (tasks created)", "- review every `confirmed? review` row; fix or accept with rationale", ""]
    out.write_text("\n".join(body), encoding="utf-8")
    _add_index_row(out, len(findings), len(covered))
    return out


# ---- self-test ------------------------------------------------------------------------------------------------------

SELFTEST = {
    "bad.py": '''import subprocess, pickle, hashlib, random, yaml
def run(cmd): return subprocess.run(cmd, shell=True)
def load(b): return pickle.loads(b)
def cfg(s): return yaml.load(s)
def safe(s): return yaml.load(s, Loader=yaml.SafeLoader)
def q(cur, name): cur.execute("SELECT * FROM t WHERE n = '%s'" % name)
def ok(cur, name): cur.execute("SELECT * FROM t WHERE n = ?", (name,))
password = "hunter2xyz"
token = random.randint(0, 99999)
h = hashlib.md5(b"x")  # aix: accepted VUL-AUTHN-001 checksum only
DEBUG = True
''',
    "bad.ts": '''const q = (db: any, id: string) => db.query(`SELECT * FROM t WHERE id = ${id}`);
el.innerHTML = user;
const token = "t" + Math.random();
fetch(u, { rejectUnauthorized: false });
''',
    "Dockerfile": "FROM python\nRUN pip install x\nCMD [\"python\", \"app.py\"]\n",
    "requirements.txt": "flask\nrequests==2.31.0\n",
}


SELFTEST_WANT = [("VUL-INJ-002", "bad.py", "open", 1), ("VUL-INPUT-002", "bad.py", "open", 2), ("VUL-INJ-001", "bad.py", "open", 1),
                 ("VUL-SECRET-001", "bad.py", "open", 1), ("VUL-AUTHN-001", "bad.py", "open", 1), ("VUL-AUTHN-001", "bad.py", "acc", 1),
                 ("VUL-SECRET-002", "bad.py", "open", 1), ("VUL-INJ-001", "bad.ts", "open", 1), ("VUL-WEB-001", "bad.ts", "open", 1),
                 ("VUL-AUTHN-001", "bad.ts", "open", 1), ("VUL-SECRET-002", "bad.ts", "open", 1), ("VUL-INFRA-001", "Dockerfile", "open", 1),
                 ("VUL-DEP-001", "Dockerfile", "open", 1), ("VUL-DEP-001", "requirements.txt", "open", 1)]


def _scan_snippets():
    """Scan the known-bad snippets in a temporary project; ROOT is swapped for the duration."""
    import tempfile
    global ROOT
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        for name, text in SELFTEST.items():
            (base / name).write_text(text, encoding="utf-8")
        saved, ROOT = ROOT, base
        try:
            return scan([str(base)])
        finally:
            ROOT = saved


def _count_found(found) -> dict:
    got = defaultdict(int)
    for vul, _cwe, _title, file, _ln, _snippet, _advice, acc in found:
        got[(vul, Path(file).name, "acc" if acc else "open")] += 1
    return got


def _check_wanted(got: dict) -> int:
    failed = 0
    for vul, file, state, n in SELFTEST_WANT:
        ok = got[(vul, file, state)] == n; failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {vul} in {file} ({state}): {got[(vul, file, state)]} (expected {n})")
    return failed


def selftest():
    """Scan the built-in snippets and compare with SELFTEST_WANT; exit 1 on any mismatch."""
    found = _scan_snippets()
    failed = _check_wanted(_count_found(found))
    safe_hits = [f for f in found if f[4] in (5, 7) and Path(f[3]).name == "bad.py"]
    failed += bool(safe_hits)
    print(f"  {'FAIL' if safe_hits else 'PASS'}  safe yaml.load(Loader=SafeLoader) and parameterised execute not flagged")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]"


def _write_report(text: str):
    out = ROOT / "docs" / "tests" / "code-security.md"
    out.write_text("# Code security (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
    print(f"\n  wrote {out.relative_to(ROOT)}")


def main(args):
    if "--selftest" in args:
        return selftest()
    paths = [a for a in args if not a.startswith("--")] or default_roots()
    findings = scan(paths)
    text, n_live = render(findings, paths, "--strict" in args)
    print(text)
    if "--report" in args:
        _write_report(text)
    if "--audit" in args:
        print(f"\n  wrote {write_audit(findings, paths).relative_to(ROOT)}  (fill Status per row after review; aix docs security reads it)")
    if "--gate" in args:
        if n_live:
            sys.exit(f"GATE FAILED: {n_live} security finding(s) to review")
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
