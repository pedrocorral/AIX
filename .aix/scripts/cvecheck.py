"""Leaf: known CVEs of pinned dependencies, asked from OSV (osv.dev) for every manifest and lock file found."""
import json, re, urllib.request
from pathlib import Path

from codefiles import ROOT, SKIP, rel


# ---- known CVEs via OSV ----------------------------------------------------------------------------------------

LOCK_TOML = re.compile(r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"')
PNPM_LINE = re.compile(r"^\s{2}['\"]?/?(@?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?)@(\d[0-9A-Za-z.\-+]*)", re.M)


def _manifest_files(root: Path, pattern: str):
    return [f for f in root.rglob(pattern) if not any(s in f.relative_to(root).parts for s in SKIP)]


def _pinned_requirements(root: Path):
    for f in _manifest_files(root, "requirements*.txt"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([0-9][^\s;#]*)", line)
            if m:
                yield ("PyPI", m.group(1).lower(), m.group(2), rel(f))


def _toml_locks(root: Path):
    for name in ("uv.lock", "poetry.lock", "pdm.lock", "Cargo.lock"):
        eco = "crates.io" if name == "Cargo.lock" else "PyPI"
        for f in _manifest_files(root, name):
            for m in LOCK_TOML.finditer(f.read_text(encoding="utf-8", errors="replace")):
                yield (eco, m.group(1), m.group(2), rel(f))


def _npm_locks(root: Path):
    for f in _manifest_files(root, "package-lock.json"):
        try:
            pk = json.loads(f.read_text(encoding="utf-8", errors="replace")).get("packages", {})
        except json.JSONDecodeError:
            continue
        for path, info in pk.items():
            if path.startswith("node_modules/") and "version" in info:
                yield ("npm", path.split("node_modules/")[-1], info["version"], rel(f))
    for f in _manifest_files(root, "pnpm-lock.yaml"):
        for m in PNPM_LINE.finditer(f.read_text(encoding="utf-8", errors="replace")):
            yield ("npm", m.group(1), m.group(2), rel(f))


def dependencies(root: Path):
    """[(ecosystem, name, version, manifest)] from pinned manifests and lockfiles."""
    seen, out = set(), []
    for d in [*_pinned_requirements(root), *_toml_locks(root), *_npm_locks(root)]:
        if d[:3] not in seen:
            seen.add(d[:3]); out.append(d)
    return out


def osv_query(deps, timeout=25):
    """One querybatch call; returns {(eco, name, version): [vuln ids]} or None when unreachable."""
    if not deps:
        return {}
    body = json.dumps({"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v, _ in deps]}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/querybatch", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            results = json.loads(r.read().decode()).get("results", [])
    except Exception:
        return None
    out = {}
    for d, res in zip(deps, results):
        ids = [v["id"] for v in res.get("vulns", [])]
        if ids:
            out[d[:3]] = ids
    return out


def _version_key(s: str):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.\-]", s)]


def osv_detail(vid, name, timeout=15):
    """Summary and the first fixed version FOR THIS PACKAGE (an advisory may cover several packages)."""
    try:
        with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vid}", timeout=timeout) as r:
            v = json.loads(r.read().decode())
    except Exception:
        return "", ""
    mine = [a for a in v.get("affected", []) if a.get("package", {}).get("name", "").lower() == name.lower()] or v.get("affected", [])
    fixed = sorted({e["fixed"] for a in mine for rg in a.get("ranges", []) for e in rg.get("events", []) if "fixed" in e}, key=_version_key)
    return v.get("summary", "")[:70], fixed[0] if fixed else ""


def cve():
    deps = dependencies(ROOT)
    hits = osv_query(deps)
    if hits is None:
        return None, len(deps)
    findings = []
    for (eco, name, version), ids in hits.items():
        manifest = next(d[3] for d in deps if d[:3] == (eco, name, version))
        for vid in ids[:3]:
            summary, fixed = osv_detail(vid, name)
            findings.append(("VUL-DEP-001", "CWE-1395", f"known vulnerability {vid}", manifest, 0,
                             f"{name} {version} ({eco}): {summary}" + (f" — fixed in {fixed}" if fixed else ""),
                             f"upgrade {name} to {fixed or 'a fixed version'} and re-run", None))
    return findings, len(deps)
