#!/usr/bin/env python3
"""aix security — where does the vulnerability register stand?

Reads docs/security/vulnerability-register.md and docs/security/audits/. Reports which VUL rows are validated
(closed with evidence or an owned decision) and which are not, plus rows whose status has no audit evidence.
The audits themselves are done by the security-audit-* skills; this command only reports and gates."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "docs" / "security" / "vulnerability-register.md"
AUDITS = ROOT / "docs" / "security" / "audits"
DECISIONS = ROOT / "docs" / "requirements" / "decisions"
VALIDATED = {"addressed", "accepted", "not-applicable"}
OPEN_ORDER = ["confirmed", "mitigated", "unverified", "expected"]  # worst first


def rows():
    """VUL rows as dicts: id, description, component, status, skill, last_audit."""
    out = []
    if not REGISTER.exists():
        sys.exit("no docs/security/vulnerability-register.md in this project")
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if line.startswith("| VUL-"):
            c = [x.strip() for x in line.strip("|").split("|")]
            if len(c) >= 6:
                out.append(dict(id=c[0], description=c[1], component=c[2], status=c[3], skill=c[4], last_audit=c[5]))
    return out


def evidence():
    """VUL ids mentioned in any audit report, and in any ADR (for `accepted`)."""
    audits = set(re.findall(r"\bVUL-[A-Z]+-\d{3}\b", "".join(p.read_text(encoding="utf-8", errors="replace")
                 for p in AUDITS.rglob("*.md") if p.name != "INDEX.md"))) if AUDITS.exists() else set()
    adrs = set(re.findall(r"\bVUL-[A-Z]+-\d{3}\b", "".join(p.read_text(encoding="utf-8", errors="replace")
               for p in DECISIONS.rglob("*.md") if p.name != "INDEX.md"))) if DECISIONS.exists() else set()
    return audits, adrs


def missing_evidence(r, audits, adrs):
    """A status beyond `expected` needs an audit report; `accepted` needs an ADR too."""
    if r["status"] == "expected":
        return None
    if r["id"] not in audits:
        return f"{r['id']} is `{r['status']}` but no audit report in docs/security/audits/ mentions it"
    if r["status"] == "accepted" and r["id"] not in adrs:
        return f"{r['id']} is `accepted` but no ADR in docs/requirements/decisions/ mentions it"
    return None


def problems():
    audits, adrs = evidence()
    return [m for r in rows() if (m := missing_evidence(r, audits, adrs))]


def category(r):
    return r["id"].split("-")[1]


def print_group(title, group):
    print(f"{title} ({len(group)})")
    for r in group:
        print(f"  {r['id']:16s} {r['status']:14s} {r['component']:28s} {r['description'][:60]}")
    if not group:
        print("  none")
    print()


def cmd_report(which=None, gate=False):
    all_rows = rows()
    validated = [r for r in all_rows if r["status"] in VALIDATED]
    open_rows = sorted((r for r in all_rows if r["status"] not in VALIDATED), key=lambda r: OPEN_ORDER.index(r["status"]))
    counts = {}
    for r in all_rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("Vulnerability register: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"  (total {len(all_rows)})\n")
    if which in (None, "open"):
        print_group("NOT VALIDATED — run the audit skill named in the register", open_rows)
    if which in (None, "validated"):
        print_group("VALIDATED — addressed with evidence, accepted by ADR, or not applicable", validated)
    if which in (None, "open"):
        todo = sorted({r["skill"] for r in open_rows})
        if todo:
            print("Audit skills still to run: " + ", ".join(todo) + "\n")
    probs = problems()
    for p in probs:
        print(f"PROBLEM {p}")
    if probs:
        print("        fix: write the audit report (templates/audit-report.md) or revert the status\n")
    if gate:
        bad = [r["id"] for r in open_rows]
        if bad or probs:
            print(f"GATE FAILED: {len(bad)} rows not validated, {len(probs)} without evidence")
            sys.exit(1)
        print("GATE PASSED: every row validated with evidence")


def main(args):
    gate = "--gate" in args
    args = [a for a in args if a != "--gate"]
    which = args[0] if args else None
    if which not in (None, "open", "validated"):
        sys.exit("usage: aix security [open|validated] [--gate]")
    cmd_report(which, gate)


if __name__ == "__main__":
    main(sys.argv[1:])
