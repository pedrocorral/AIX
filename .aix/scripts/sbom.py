#!/usr/bin/env python3
"""aix code sbom (aix blackduck) — the software bill of materials and the composition policy, what a Black Duck
scan gives: every package the project installs (manifests and lockfiles, transitives resolved through deps.dev),
its licence (from the metadata installed on disk, aix code licenses), its known advisories with a severity (OSV,
CVSS 3.x computed from the vector), written as CycloneDX 1.5 JSON (or SPDX 2.3 with --spdx), and one verdict:
no advisory at or above `sbom_max_severity` (default high), no licence undecided.

  aix code sbom [--spdx] [--out FILE] [--gate] [--report]
  aix blackduck                       = aix code sbom --gate"""
import json, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from codefiles import ROOT
import cvss
from cvecheck import all_dependencies, fixed_version, osv_query, osv_vuln, severity
from licenses import config_licenses, rows as licence_rows
import layers

PURL = {"PyPI": "pypi", "npm": "npm", "Maven": "maven", "crates.io": "cargo", "RubyGems": "gem", "Packagist": "composer", "Go": "golang"}
ECO_OF_INSTALLED = {"python": "PyPI", "npm": "npm", "cargo": "crates.io", "maven": "Maven"}
DEFAULT_MAX = "high"


def purl(eco: str, name: str, version: str) -> str:
    kind = PURL.get(eco, eco.lower())
    path = name.replace(":", "/") if eco == "Maven" else name.replace("@", "%40") if eco == "npm" else name
    return f"pkg:{kind}/{path}@{version}"


def max_severity() -> str:
    value = str(layers.config(ROOT).get("sbom_max_severity") or DEFAULT_MAX).lower()
    return value if value in cvss.LABELS else DEFAULT_MAX


# ---- the bill --------------------------------------------------------------------------------------------------------

def _licences(root: Path) -> dict:
    """{(ecosystem, name lower): (licence, class)} from what is installed on disk."""
    return {(ECO_OF_INSTALLED.get(eco, eco), name.lower()): (lic, cls) for name, _v, lic, eco, cls in licence_rows(root, config_licenses())}


def _advisory(d: tuple, vid: str) -> dict:
    v = osv_vuln(vid)
    label, score = severity(v)
    return dict(id=vid, package=d, severity=label, score=score, summary=v.get("summary", "")[:120], fixed=fixed_version(v, d[1], d[2]))


def _advisories(deps: list, hits: dict) -> list:
    """One record per (package, advisory): id, severity label and score, summary, the fixed version to move to."""
    pairs = [(d, vid) for d in deps for vid in hits.get(d[:3], [])]
    with ThreadPoolExecutor(max_workers=8) as pool:   # one OSV read per advisory the first day, hundreds on a big lockfile
        return list(pool.map(lambda p: _advisory(*p), pairs))


def build(root: Path = ROOT) -> dict:
    """{components, advisories, stats, unreachable}: the bill, with the network for OSV and deps.dev."""
    deps, stats = all_dependencies(root)
    hits = osv_query(deps)
    licences = _licences(root)
    components = [dict(eco=eco, name=name, version=version, manifest=file, purl=purl(eco, name, version), licence=licences.get((eco, name.lower()), ("", "")))
                  for eco, name, version, file in deps]   # licence ("", ""): not installed on disk, so not read
    return dict(components=components, advisories=_advisories(deps, hits) if hits else [], stats=stats, unreachable=hits is None or stats["unreachable"], licences_read=bool(licences))


# ---- CycloneDX / SPDX --------------------------------------------------------------------------------------------------

def _tool() -> dict:
    return {"name": "aix", "version": str(layers.config(ROOT).get("version", ""))}


def cyclonedx(bill: dict) -> dict:
    comps = [{"type": "library", "bom-ref": c["purl"], "name": c["name"], "version": c["version"], "purl": c["purl"],
              **({"licenses": [{"license": {"name": c["licence"][0]}}]} if c["licence"][0] else {}),
              "properties": [{"name": "aix:manifest", "value": c["manifest"]}, {"name": "aix:ecosystem", "value": c["eco"]}]} for c in bill["components"]]
    vulns = {}
    for a in bill["advisories"]:
        v = vulns.setdefault(a["id"], {"id": a["id"], "source": {"name": "OSV", "url": f"https://osv.dev/vulnerability/{a['id']}"},
                                        "ratings": [{"severity": a["severity"] if a["severity"] != "unknown" else "unknown", **({"score": a["score"], "method": "CVSSv31"} if a["score"] is not None else {})}],
                                        "description": a["summary"], "affects": [], **({"recommendation": f"upgrade to {a['fixed']}"} if a["fixed"] else {})})
        v["affects"].append({"ref": purl(*a["package"][:3])})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tools": [_tool()], "component": {"type": "application", "name": ROOT.name}},
            "components": comps, "vulnerabilities": list(vulns.values())}


def spdx(bill: dict) -> dict:
    """SPDX 2.3 carries packages and licences, not advisories (CycloneDX does): the vulnerabilities stay in the report."""
    pkgs = [{"SPDXID": f"SPDXRef-{i}", "name": c["name"], "versionInfo": c["version"], "downloadLocation": "NOASSERTION",
             "licenseConcluded": c["licence"][0] or "NOASSERTION", "licenseDeclared": c["licence"][0] or "NOASSERTION",
             "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": c["purl"]}]} for i, c in enumerate(bill["components"], 1)]
    return {"spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT", "name": ROOT.name,
            "documentNamespace": f"https://aix.local/{ROOT.name}/sbom", "creationInfo": {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "creators": [f"Tool: aix-{_tool()['version']}"]},
            "packages": pkgs, "relationships": [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": p["SPDXID"]} for p in pkgs]}


# ---- policy and report --------------------------------------------------------------------------------------------------

def verdict(bill: dict, threshold: str) -> tuple:
    """(over the threshold, licence problems): the advisories at or above the severity threshold, and the components
    whose licence class needs a decision (strong copyleft, proprietary, unknown); a component not installed on disk
    has no licence read and nothing to decide."""
    over = [a for a in bill["advisories"] if cvss.rank(a["severity"]) <= cvss.rank(threshold)]
    bad = [c for c in bill["components"] if c["licence"][1] in ("strong copyleft", "proprietary", "unknown")]
    return over, bad


LISTED = 40   # packages listed under the threshold line; the bill has them all


def _upgrade_target(items: list) -> str:
    fixes = sorted({a["fixed"] for a in items if a["fixed"]}, key=lambda s: [(0, int(x)) if x.isdigit() else (1, x) for x in s.replace("-", ".").split(".")])
    return f"  -> upgrade to {fixes[-1]}" if fixes else ""


def _advisory_line(package: tuple, items: list) -> str:
    eco, name, version, manifest = package
    worst = items[0]
    score = f" {worst['score']}" if worst["score"] is not None else ""
    return f"    {name} {version} ({eco}, {manifest}): {len(items)} at {worst['severity']}{score}  {worst['id']}{_upgrade_target(items)}"


def _advisory_lines(over: list) -> list:
    by_pkg = {}
    for a in sorted(over, key=lambda a: (cvss.rank(a["severity"]), -(a["score"] or 0))):
        by_pkg.setdefault(a["package"], []).append(a)
    lines = [_advisory_line(package, items) for package, items in list(by_pkg.items())[:LISTED]]
    return lines + ([f"    ... and {len(by_pkg) - LISTED} more packages"] if len(by_pkg) > LISTED else [])


def _licence_summary(comps: list) -> str:
    classes = Counter(c["licence"][1] for c in comps if c["licence"][1])
    if not classes:
        return "nothing installed on disk to read (aix code licenses reads dist-info, node_modules, the Cargo and Maven caches)"
    return ", ".join(f"{k} {v}" for k, v in classes.most_common()) + f"; {sum(1 for c in comps if not c['licence'][1])} components not installed on disk, licence not read"


def _summary_lines(bill: dict, out: Path) -> list:
    stats, comps, adv = bill["stats"], bill["components"], bill["advisories"]
    sev = Counter(a["severity"] for a in adv)
    where = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    return [f"Software bill of materials — {ROOT.name}", "",
            f"  components {len(comps)} from {len(stats['manifests'])} manifest(s): " + ", ".join(f"{k} {v}" for k, v in Counter(c["eco"] for c in comps).most_common())
            + f"; {stats['transitive']} pulled in by the {stats['direct']} direct declarations",
            f"  advisories {len(adv)}: " + (", ".join(f"{k} {sev[k]}" for k in (*cvss.LABELS, "unknown") if sev[k]) or "none") + ("  (OSV or deps.dev unreachable: partial)" if bill["unreachable"] else ""),
            "  licences: " + _licence_summary(comps), f"  wrote {where}", ""]


def _policy_lines(bill: dict, threshold: str, over: list, bad: list) -> list:
    lines = [f"  POLICY  advisories at or above {threshold}: {len(over)}   licences to decide: {len(bad)}   (sbom_max_severity in .aix/config.yaml; licenses_allow / licenses_known for licences)"]
    if over:
        lines += ["  ADVISORIES over the threshold, worst first:", *_advisory_lines(over)]
    if bad:
        lines += ["  LICENCES to decide:", *[f"    {c['name']} {c['version']}: {c['licence'][0] or '(none)'} [{c['licence'][1]}]" for c in bad[:30]]]
    unresolved = bill["stats"]["unresolved"]
    if unresolved:
        lines.append(f"  not in the bill: {len(unresolved)} Maven dependencies without a resolvable version ({', '.join(unresolved[:3])})")
    return lines + ["  A bill is an inventory, not a proof: a package present is exposed only where it is used; an advisory applies to the version, read it before rotating priorities."]


def render(bill: dict, threshold: str, out: Path) -> str:
    over, bad = verdict(bill, threshold)
    return "\n".join(_summary_lines(bill, out) + _policy_lines(bill, threshold, over, bad))


def _gate(bill: dict, threshold: str):
    over, bad = verdict(bill, threshold)
    if over or bad:
        sys.exit(f"GATE FAILED: {len(over)} advisory(ies) at or above {threshold}, {len(bad)} licence(s) to decide")
    print("GATE PASSED" + ("  (OSV or deps.dev unreachable: partial bill)" if bill["unreachable"] else ""))


def main(args):
    """Write the bill, print the report, apply the policy when asked."""
    if "--selftest" in args:
        return selftest()
    threshold = max_severity()
    fmt = "spdx" if "--spdx" in args else "cyclonedx"
    out = Path(args[args.index("--out") + 1]) if "--out" in args else ROOT / "docs" / "security" / ("sbom.spdx.json" if fmt == "spdx" else "sbom.cdx.json")
    bill = build()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spdx(bill) if fmt == "spdx" else cyclonedx(bill), indent=1), encoding="utf-8")
    text = render(bill, threshold, out)
    print(text)
    if "--report" in args:
        rep = ROOT / "docs" / "tests" / "code-sbom.md"
        rep.write_text("# Software bill of materials (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {rep.relative_to(ROOT)}")
    if "--gate" in args:
        _gate(bill, threshold)


def selftest():
    """The CVSS arithmetic on published scores and the purl shapes."""
    cases = [("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0), ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
             ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1), ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N", 5.5)]
    failed = 0
    for vector, want in cases:
        got = cvss.base_score(vector); failed += got != want
        print(f"  {'PASS' if got == want else 'FAIL'}  {vector} = {got} (published {want})")
    for args, want in [(("Maven", "org.apache:x", "1"), "pkg:maven/org.apache/x@1"), (("npm", "@s/n", "2"), "pkg:npm/%40s/n@2"), (("PyPI", "django", "4.2"), "pkg:pypi/django@4.2")]:
        got = purl(*args); failed += got != want
        print(f"  {'PASS' if got == want else 'FAIL'}  purl {got}")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
