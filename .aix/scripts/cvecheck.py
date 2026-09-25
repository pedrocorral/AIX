"""Leaf: known CVEs of the dependencies, asked from OSV (osv.dev) for what the manifests declare and, for a
requirements.txt or a pom.xml, for what those declarations pull in (resolved through deps.dev, see depsdev.py).
Lockfiles are queried as they are: they already hold the whole tree."""
import json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codefiles import ROOT
import cvss
import depsdev
from manifests import lockfile_dependencies, pinned_requirements, poms

BATCH = 1000   # OSV's querybatch limit
OSV_CACHE = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "osv"
OSV_TTL = 24 * 3600   # an advisory can be amended: re-read after a day


def dependencies(root: Path) -> list:
    """[(ecosystem, name, version, manifest)] declared by the project: lockfile entries and `==` pins. No network."""
    seen, out = set(), []
    for d in [*pinned_requirements(root), *lockfile_dependencies(root)]:
        if d not in seen:
            seen.add(d); out.append(d)
    return out


# ---- resolution ------------------------------------------------------------------------------------------------------

class _Declared:
    """A direct declaration (eco, name, version, file) and what constrains its transitives: Maven exclusions and
    managed versions."""
    def __init__(self, dep: tuple, excluded=(), managed=None):
        self.eco, self.name, self.version, self.file = dep
        self.excluded, self.managed = excluded, managed or {}


def _pom_direct(root: Path, stats: dict) -> list:
    """The direct Maven dependencies of every pom.xml with a version, managed ones resolved through the parent;
    each carries the pom's managed versions (its own and the inherited ones), which override transitives."""
    out, parents = [], {}
    for file, deps, own, parent in poms(root):
        stats["manifests"].add(file)
        if parent and parent not in parents:
            parents[parent] = depsdev.managed(*parent)
            stats["unreachable"] |= parents[parent] is None
        managed = {**(parents.get(parent) or {}), **own}
        for name, version, _scope, excluded in deps:
            version = version or managed.get(name, "")
            if version:
                out.append(_Declared(("Maven", name, version, file), excluded, managed))
            else:
                stats["unresolved"].append(f"{file}: {name}")
    return out


def _resolved(direct: list, stats: dict) -> list:
    """Direct declarations plus everything they pull in, one version per package and manifest: the declared
    version, else the managed one, else the first met (Maven's nearest wins), carrying the manifest."""
    chosen = {}
    for d in direct:
        graph = depsdev.resolve(d.eco, d.name, d.version, d.excluded)
        if graph is None:
            stats["unreachable"] = True
        for i, (eco, name, version) in enumerate(graph or [(d.eco, d.name, d.version)]):
            version = d.managed.get(name, version) if i else d.version   # the declared spelling (`4.2`, not deps.dev's `4.2.0`): OSV lists it so
            if (eco, name, d.file) not in chosen or i == 0:
                chosen[(eco, name, d.file)] = version
                stats["transitive"] += i > 0
    return [(eco, name, version, file) for (eco, name, file), version in chosen.items()]


def all_dependencies(root: Path) -> tuple:
    """(deps, stats): everything to query, once per package and manifest (a package in two lockfiles is two
    findings: each lockfile is fixed on its own), with stats manifests, direct, transitive, unresolved, unreachable."""
    stats = dict(manifests=set(), direct=0, transitive=0, unresolved=[], unreachable=False)
    pins = [_Declared(d) for d in pinned_requirements(root)]; locks = lockfile_dependencies(root)
    direct = pins + _pom_direct(root, stats)
    stats["direct"] = len(direct)
    stats["manifests"] |= {d.file for d in pins} | {d[3] for d in locks}
    seen, out = set(), []
    for d in _resolved(direct, stats) + locks:
        if d not in seen:
            seen.add(d); out.append(d)
    return out, stats


# ---- OSV -------------------------------------------------------------------------------------------------------------

def _post(body: bytes):
    req = urllib.request.Request("https://api.osv.dev/v1/querybatch", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode()).get("results", [])
    except Exception:
        return None


POST = _post


def osv_query(deps: list):
    """{(eco, name, version): [vuln ids]} for the vulnerable ones, in batches of BATCH; None when unreachable."""
    out, unique = {}, list({d[:3]: d for d in deps}.values())
    for start in range(0, len(unique), BATCH):
        chunk = unique[start:start + BATCH]
        results = POST(json.dumps({"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v, _ in chunk]}).encode())
        if results is None:
            return None
        for d, res in zip(chunk, results):
            ids = [v["id"] for v in res.get("vulns", [])]
            if ids:
                out[d[:3]] = ids
    return out


def _version_key(s: str) -> list:
    """Numeric parts before textual ones, so `1.0.0` and `1.0.0rc1` compare without a TypeError."""
    return [(0, int(x)) if x.isdigit() else (1, x) for x in re.split(r"[.\-]", s)]


def _fetch_vuln(vid: str, timeout=15):
    try:
        with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vid}", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


FETCH_VULN = _fetch_vuln


def osv_vuln(vid: str) -> dict:
    """The advisory record, cached on disk for a day; {} when it cannot be read."""
    key = OSV_CACHE / f"{vid}.json"
    if key.exists() and time.time() - key.stat().st_mtime < OSV_TTL:
        return json.loads(key.read_text(encoding="utf-8"))
    v = FETCH_VULN(vid)
    if v is not None:
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps(v), encoding="utf-8")
    return v or {}


def severity(v: dict) -> tuple:
    """(label, score) of an advisory: the CVSS 3.x base score computed from its vector when it has one, else the
    label its database gives (GHSA says CRITICAL/HIGH/MODERATE/LOW), else unknown."""
    for entry in v.get("severity", []):
        score = cvss.base_score(str(entry.get("score", "")))
        if score is not None:
            return cvss.label(score), score
    given = str(v.get("database_specific", {}).get("severity", "") or next((a.get("ecosystem_specific", {}).get("severity", "") for a in v.get("affected", [])), "")).lower()
    return ({"moderate": "medium"}.get(given, given) if given in ("critical", "high", "moderate", "medium", "low") else "unknown"), None


def _fixed_versions(v: dict, name: str) -> list:
    """Every fixed version an advisory lists FOR THIS PACKAGE (it may cover several), lowest first."""
    mine = [a for a in v.get("affected", []) if a.get("package", {}).get("name", "").lower() == name.lower()] or v.get("affected", [])
    return sorted({e["fixed"] for a in mine for rg in a.get("ranges", []) for e in rg.get("events", []) if "fixed" in e}, key=_version_key)


def fixed_version(v: dict, name: str, current: str = "") -> str:
    """The fixed version to move to: the smallest above the current one (an advisory may fix several release
    branches), else the highest listed; '' when none is listed."""
    fixed = _fixed_versions(v, name)
    above = [f for f in fixed if not current or _version_key(f) > _version_key(current)]
    return above[0] if above else fixed[-1] if fixed else ""


def osv_detail(vid, name, current: str = ""):
    """Summary and the fixed version to move to for this package."""
    v = osv_vuln(vid)
    return (v.get("summary", "")[:70], fixed_version(v, name, current)) if v else ("", "")


def _finding(dep: tuple, ids: list) -> tuple:
    """One finding per vulnerable package: the first three advisories with summaries, the rest by id."""
    eco, name, version, manifest = dep
    told = [f"{vid} ({s}{', fixed in ' + f if f else ''})" if s else vid for vid, (s, f) in ((vid, osv_detail(vid, name, version)) for vid in ids[:3])]
    fixes = [x.split("fixed in ")[-1].rstrip(")") for x in told if "fixed in" in x]
    return ("VUL-DEP-001", "CWE-1395", f"{len(ids)} known vulnerabilit{'y' if len(ids) == 1 else 'ies'}: {name} {version} ({eco})", manifest, 0,
            "; ".join(told + ids[3:])[:240], f"upgrade {name} to {fixes[0] if fixes else 'a fixed version'} and re-run", None)


def cve() -> tuple:
    """(findings, stats): findings per vulnerable package; stats adds packages, vulnerable, advisories."""
    deps, stats = all_dependencies(ROOT)
    hits = osv_query(deps)
    stats.update(packages=len(deps), vulnerable=0, advisories=0)
    if hits is None:
        stats["unreachable"] = True
        return None, stats
    with ThreadPoolExecutor(max_workers=8) as pool:   # one advisory lookup per call: hundreds on a big lockfile
        findings = list(pool.map(lambda d: _finding(d, hits[d[:3]]), [d for d in deps if d[:3] in hits]))
    stats.update(vulnerable=len(findings), advisories=sum(len(hits[d[:3]]) for d in deps if d[:3] in hits))
    return findings, stats
