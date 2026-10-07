"""Section 25 of docs/tests/benchmark-engines.md: ABAP security, ours vs abaplint's `dangerous_statement` (dynamic
SQL, INSERT/DELETE REPORT, INSERT/DELETE TEXTPOOL) and `call_transaction_authority_check` on abap2xlsx and abapGit.
Ours: `aix code security` on the installed copy, the ABAP findings by rule, each abaplint finding matched by file
and line, and every finding abaplint does not have listed to read by hand."""
import json, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
ABAPLINT_RULES = ("dangerous_statement", "call_transaction_authority_check")


def _env() -> dict:
    return dict(os.environ, PATH=os.pathsep.join([str(engines.BENCH / "node" / "bin"), os.environ["PATH"]]))


def abaplint(project: Path) -> list:
    """(file, line, message) of abaplint's two security rules."""
    base = json.loads(subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), "--default"], capture_output=True, text=True, env=_env()).stdout)
    cfg = project / "abaplint-sec.json"
    cfg.write_text(json.dumps({"global": base["global"], "syntax": base.get("syntax", {}), "rules": {k: base["rules"][k] for k in ABAPLINT_RULES}}))
    out = subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), str(cfg)], cwd=project, capture_output=True, text=True, env=_env()).stdout
    cfg.unlink()
    return [(m.group(1), int(m.group(2)), m.group(3)) for m in re.finditer(r"(\S+)\[(\d+), \d+\]\s+- (.*?) \((?:dangerous_statement|call_transaction_authority_check)\)", out)]


AUDIT_ROW = re.compile(r"`(\S+\.abap):(\d+)` (.*?) \((CWE-\d+)\)")
SCREEN_ROW = re.compile(r"^\s+(\S+\.abap):(\d+)\s+(.*?) \((CWE-\d+)\)", re.M)


def ours(project: Path) -> list:
    """(file, line, title, cwe) of every ABAP finding of `aix code security --audit` on the copy, from the audit
    report it writes (the screen report lists 25 per row)."""
    out = subprocess.run([str(project / ".aix" / "bin" / "aix"), "code", "security", "--audit"], cwd=project, env=engines.env(), capture_output=True, text=True).stdout
    written = re.search(r"wrote (\S+\.md)", out)
    audit = (project / written.group(1)).read_text(encoding="utf-8") if written and (project / written.group(1)).is_file() else ""
    rows = {(m.group(1), int(m.group(2)), m.group(3), m.group(4)) for rx, text in ((AUDIT_ROW, audit), (SCREEN_ROW, out)) for m in rx.finditer(text)}
    return sorted(rows)


def _by_rule(us: list) -> list:
    counts = Counter((t, c) for _f, _l, t, c in us)
    return [f"   ours by rule: {t} ({c}): {n}" for (t, c), n in sorted(counts.items(), key=lambda kv: -kv[1])]


def _differences(ab: list, us: list) -> list:
    ours_at, theirs_at = {(f, l) for f, l, _t, _c in us}, {(f, l) for f, l, _m in ab}
    lines = [f"   abaplint only: {f}:{l} {m}" for f, l, m in ab if (f, l) not in ours_at][:10]
    return lines + [f"   ours only: {f}:{l} {t} ({c})" for f, l, t, c in us if (f, l) not in theirs_at][:25]


def report(project: dict) -> str:
    tmp = engines.prepare(project)
    ab, us = abaplint(tmp), ours(tmp)
    ours_at = {(f, l) for f, l, _t, _c in us}
    matched = sum(1 for f, l, _m in ab if (f, l) in ours_at)
    head = f"== {project['name']}: ours {len(us)} ABAP findings, abaplint {len(ab)}, of which at the same line in ours {matched}"
    return "\n".join([head] + _by_rule(us) + _differences(ab, us))


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name]))


if __name__ == "__main__":
    main(sys.argv[1:])
