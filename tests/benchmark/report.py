"""The Markdown tables of docs/tests/benchmark-engines.md from the JSON that engines.py wrote (~/.cache/aix/benchmark/).

Every number is a count of findings, a time in seconds, or an overlap: two findings agree when they name the same file
within a window of lines (±1 for line rules, ±10 for security, where one engine anchors at the string build and the
other at the call). Usage: python3 tests/benchmark/report.py > tables.md"""
import collections, json, os, re, sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "benchmark"
KNOWN = json.loads((KIT / "tests" / "extended" / "known.json").read_text())
PROJECTS = json.loads((KIT / "tests" / "extended" / "projects.json").read_text())
VENDORED = re.compile(r"\.min\.js$|/(vendor|libs|third[-_]party)/|jquery|ace\.js$|three\.js$|dat\.gui|highlighting-speed-src")
VULNERABLE = [p["name"] for p in PROJECTS if p["kind"] == "vulnerable"]


def load() -> dict:
    return {p["name"]: json.loads((OUT / f"{p['name']}.json").read_text()) for p in PROJECTS if (OUT / f"{p['name']}.json").exists()}


def near(a: dict, items: list, window: int) -> bool:
    return any(b["file"] == a["file"] and abs(b["line"] - a["line"]) <= window for b in items)


def nontest(items: list) -> list:
    return [x for x in items if not x.get("test")]


def security_ours(d: dict) -> list:
    return d["ours"]["security"]["items"] + d["ours"]["taint"]["items"]


def by_rule(items: list, key: str) -> str:
    return ", ".join(f"{k} {v}" for k, v in collections.Counter(x[key] for x in items).most_common())


def table(head: list, rows: list) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def recall(name: str, items: list, window: int) -> int:
    return sum(1 for k in KNOWN[name] if any(f["file"] == k["file"] and abs(f["line"] - k["line"]) <= window for f in items))


# ---- sections -----------------------------------------------------------------------------------------------------

def security(D: dict) -> str:
    rows = []
    for n, d in D.items():
        o, sg, bd = security_ours(d), d["theirs"]["semgrep"]["items"], d["theirs"].get("bandit", {}).get("items")
        on, sn = nontest(o), nontest(sg)
        b = f"{len(nontest(bd))} / {len(bd) - len(nontest(bd))} | {d['theirs']['bandit']['secs']}" if bd is not None else "– | –"
        rows.append([n, f"{len(on)} / {len(o) - len(on)}", f"{d['ours']['security']['secs'] + d['ours']['taint']['secs']:.1f}", f"{len(sn)} / {len(sg) - len(sn)}", d["theirs"]["semgrep"]["secs"], b,
                     f"{sum(near(x, sn, 10) for x in on)} of {len(on)}", f"{sum(near(x, on, 10) for x in sn)} of {len(sn)}", f"{sum(1 for x in on if VENDORED.search(x['file']))} / {sum(1 for x in sn if VENDORED.search(x['file']))}"])
    return table(["project", "ours security+taint: non-test / test", "s", "semgrep p/default: non-test / test", "s", "bandit: non-test / test", "s", "ours also in semgrep (±10)", "semgrep also in ours (±10)", "in vendored files: ours / semgrep"], rows)


def recall_table(D: dict) -> str:
    rows, tot = [], collections.Counter()
    for n in [v for v in VULNERABLE if v in D]:
        d = D[n]; o, sg, bd = security_ours(d), d["theirs"]["semgrep"]["items"], d["theirs"].get("bandit", {}).get("items")
        cells = [recall(n, o, 1), recall(n, o, 10), recall(n, sg, 1), recall(n, sg, 10), recall(n, bd, 1) if bd else "–", recall(n, bd, 10) if bd else "–"]
        for i, v in enumerate(cells):
            tot[i] += v if v != "–" else 0
        tot["n"] += len(KNOWN[n]); tot["b"] += len(KNOWN[n]) if bd else 0
        rows.append([n, len(KNOWN[n]), *cells])
    rows.append(["total", tot["n"], tot[0], tot[1], tot[2], tot[3], f"{tot[4]} of {tot['b']}", f"{tot[5]} of {tot['b']}"])
    return table(["project", "documented vulnerabilities", "ours ±1", "ours ±10", "semgrep ±1", "semgrep ±10", "bandit ±1", "bandit ±10"], rows)


def only_rules(D: dict) -> str:
    sg_only, bd_only, ours_only = collections.Counter(), collections.Counter(), collections.Counter()
    for d in D.values():
        o = security_ours(d); sn = nontest(d["theirs"]["semgrep"]["items"])
        sg_only.update(s["rule"] for s in sn if not near(s, o, 10))
        bd_only.update(b["rule"] for b in nontest(d["theirs"].get("bandit", {}).get("items", [])) if not near(b, o, 10))
        ours_only.update(x["what"] for x in nontest(o) if not near(x, sn, 10))
    fmt = lambda c: ", ".join(f"{k} {v}" for k, v in c.most_common())
    return f"semgrep-only, by rule: {fmt(sg_only)}\n\nbandit-only, by test id: {fmt(bd_only)}\n\nours-only, by rule: {fmt(ours_only)}"


def hygiene(D: dict) -> str:
    rows = []
    for n, d in D.items():
        if "ruff" not in d["theirs"]:
            continue
        hy = d["ours"]["hygiene"]["items"]; rf = [r for r in d["theirs"]["ruff"]["items"] if r["rule"] != "C901"]; rn = nontest(rf)
        rows.append([n, len(hy), d["ours"]["hygiene"]["secs"], f"{len(rn)} / {len(rf) - len(rn)}", d["theirs"]["ruff"]["secs"], by_rule(rn, "rule"), f"{sum(near(h, rf, 1) for h in hy)} of {len(hy)}", f"{sum(near(r, hy, 1) for r in rn)} of {len(rn)}"])
    return table(["project", "ours hygiene (leftover, swallowed, bug)", "s (whole style run)", "ruff F401,F841,ARG,B006,E722,S110: non-test / test", "s", "ruff by rule (non-test)", "ours also in ruff (±1)", "ruff non-test also in ours (±1)"], rows)


def _func_key(name: str) -> str:
    return name.split("/")[-1].split("::")[-1].split(".")[-1]


def _same_functions(ours: list, lizard: list) -> int:
    """Functions over the limit in both, matched by file basename and function name (ours abbreviates long paths)."""
    ours_keys = {f["func"].split(":")[0].split("/")[-1] + ":" + _func_key(f["func"].split(":")[-1]) for f in ours}
    lizard_keys = {l["file"].split("/")[-1] + ":" + _func_key(l["func"]) for l in lizard}
    return len(ours_keys & lizard_keys)


def _vendored(items: list, key: str) -> int:
    return sum(1 for x in items if VENDORED.search(x[key]))


def complexity(D: dict) -> str:
    rows = []
    for n, d in D.items():
        oc, lz = d["ours"]["cyclomatic"]["items"], d["theirs"]["lizard"]["items"]
        c901 = sum(1 for r in d["theirs"]["ruff"]["items"] if r["rule"] == "C901") if "ruff" in d["theirs"] else "–"
        rows.append([n, len(oc), _vendored(oc, "func"), f"{len(nontest(lz))} / {len(lz) - len(nontest(lz))}", _vendored(lz, "file"), d["theirs"]["lizard"]["secs"], _same_functions(oc, lz), c901])
    return table(["project", "ours functions with cyclomatic > 10", "of them in vendored files", "lizard CCN > 10: non-test / test", "of them in vendored files", "lizard s", "same function in both (file:name)", "ruff C901 (mccabe > 10)"], rows)


def dead(D: dict) -> str:
    rows = []
    for n, d in D.items():
        if "vulture" not in d["theirs"]:
            continue
        vu = [v for v in d["theirs"]["vulture"]["items"] if v["kind"] in ("function", "method")]; od = d["ours"]["dead"]["items"]
        both = sum(1 for v in vu if any(x["file"] == v["file"] and x["line"] == v["line"] for x in od))
        rows.append([n, len(od), d["ours"]["dead"]["secs"], f"{len(nontest(vu))} / {len(vu) - len(nontest(vu))}", d["theirs"]["vulture"]["secs"], both, len(nontest(vu)) - both, len(od) - both])
    return table(["project", "ours dead functions", "s", "vulture unused function/method (≥ 60 %): non-test / test", "s", "both (same file:line)", "vulture-only (non-test)", "ours-only"], rows)


def _paired_by_cpd(group: dict, cpd_groups: list) -> bool:
    """CPD has a duplication touching the same files as this group of ours (two of them, or its only file)."""
    files = {w[0] for w in group["where"]}
    return any(len({w[0] for w in c["where"]} & files) >= min(2, len(files)) for c in cpd_groups)


def clones(D: dict) -> str:
    rows = []
    for n, d in D.items():
        cl, cp = d["ours"]["clones"], d["theirs"]["cpd"]
        hit = sum(1 for g in cl["items"] if _paired_by_cpd(g, cp["items"]))
        rows.append([n, cl["total"], f"{sum(c['test'] for c in cl['items'])} of {len(cl['items'])} listed", cl["secs"], len(cp["items"]), sum(c["test"] for c in cp["items"]), ", ".join(cp.get("langs", [])) or "none (Rust unsupported)", cp["secs"], f"{hit} of {len(cl['items'])}"])
    return table(["project", "ours exact clone groups", "test-only groups", "s", "CPD duplications (60 tokens)", "test-only", "CPD languages", "s", "ours listed groups that CPD also pairs (same files)"], rows)


def secrets(D: dict) -> str:
    rows = []
    for n, d in D.items():
        oh, gl = d["ours"]["history"]["items"], d["theirs"]["gitleaks"]["items"]
        rows.append([n, len(oh), d["ours"]["history"]["secs"], len(gl), d["theirs"]["gitleaks"]["secs"], by_rule(gl, "rule") or "–", len({h["file"] for h in oh} & {g["file"] for g in gl}), len({h["file"] for h in oh}), len({g["file"] for g in gl})])
    return table(["project", "ours secrets in history", "s", "gitleaks", "s", "gitleaks by rule", "files flagged by both", "files ours", "files gitleaks"], rows)


def cves(D: dict) -> str:
    rows = [[n, d["ours"]["cve"]["summary"][:90], d["ours"]["cve"]["secs"], "; ".join(f"{f[0]} ({f[1]} packages, {f[2]})" for f in d["theirs"]["osv-scanner"]["files"]) or "–", d["theirs"]["osv-scanner"]["vulns"], d["theirs"]["osv-scanner"]["secs"]] for n, d in D.items()]
    return table(["project", "ours (`--cve`, OSV querybatch)", "s", "osv-scanner: manifest (packages, vulnerable)", "osv vulns", "s"], rows)


SECTIONS = [("Security findings, time and overlap", security), ("Recall on the documented vulnerabilities (tests/extended/known.json)", recall_table),
            ("Rules with no counterpart on the other side (non-test findings, all projects)", only_rules), ("Hygiene: ours vs ruff (Python projects)", hygiene),
            ("Cyclomatic complexity over 10: ours vs lizard", complexity), ("Dead functions: ours vs vulture (Python projects)", dead),
            ("Clones: ours vs PMD CPD", clones), ("Secrets in git history: ours vs gitleaks", secrets), ("Known CVEs: ours vs osv-scanner", cves)]


def main():
    D = load()
    if not D:
        sys.exit(f"no results in {OUT}; run tests/benchmark/engines.py first")
    for i, (title, fn) in enumerate(SECTIONS, 1):
        print(f"### {i}. {title}\n\n{fn(D)}\n")


if __name__ == "__main__":
    main()
