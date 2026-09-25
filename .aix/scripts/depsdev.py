"""Leaf: dependency resolution through deps.dev (Google's open dependency graph, no key), the way osv-scanner does it.

A pinned version's full dependency graph (`resolve`) and the versions a Maven parent manages for its children
(`managed`) are immutable facts, so every answer is cached on disk under AIX_CACHE/depsdev and fetched once.
`FETCH` is the one function that touches the network; tests replace it."""
import json, os, urllib.error, urllib.parse, urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("AIX_CACHE") or (Path.home() / ".cache" / "aix")) / "depsdev"
SYSTEM = {"PyPI": "pypi", "npm": "npm", "Maven": "maven", "crates.io": "cargo", "Go": "go"}
ECOSYSTEM = {v: k for k, v in SYSTEM.items()}
API = "https://api.deps.dev"


def fetch_json(url: str, timeout=20):
    """One GET; {} when deps.dev does not know the package or version (a fact, cached), None when the network or
    the service is not there (never cached)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {} if e.code == 404 else None
    except Exception:
        return None


FETCH = fetch_json


def _cached(kind: str, system: str, name: str, version: str, url: str):
    key = CACHE / kind / system / f"{urllib.parse.quote(name, safe='')}@{urllib.parse.quote(version, safe='')}.json"
    if key.exists():
        return json.loads(key.read_text(encoding="utf-8"))
    data = FETCH(url)
    if data is not None:
        key.parent.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps(data), encoding="utf-8")
    return data


def _package_url(version_tag: str, system: str, name: str, version: str, suffix: str) -> str:
    return f"{API}/{version_tag}/systems/{system}/packages/{urllib.parse.quote(name, safe='')}/versions/{urllib.parse.quote(version, safe='')}:{suffix}"


def _reachable(nodes: list, edges: list, excluded: set) -> list:
    """Node indexes reachable from the package itself (node 0) without passing through an excluded name."""
    out_edges = {}
    for e in edges:
        out_edges.setdefault(e.get("fromNode", 0), []).append(e.get("toNode"))
    seen, todo = [], [0]
    while todo:
        i = todo.pop()
        if i in seen or i is None or i >= len(nodes) or (i and nodes[i].get("versionKey", {}).get("name") in excluded):
            continue
        seen.append(i); todo.extend(out_edges.get(i, []))
    return sorted(seen)


def resolve(eco: str, name: str, version: str, excluded=()):
    """[(ecosystem, name, version)] of the whole dependency graph of one pinned package, itself first, with the
    subtrees under `excluded` names left out (Maven exclusions); [] when the ecosystem is not covered; None when
    unreachable."""
    system = SYSTEM.get(eco)
    if not system:
        return []
    data = _cached("dependencies", system, name, version, _package_url("v3", system, name, version, "dependencies"))
    if data is None:
        return None
    nodes = data.get("nodes", [])
    keep = _reachable(nodes, data.get("edges", []), set(excluded)) if excluded else range(len(nodes))
    return [(eco, nodes[i]["versionKey"]["name"], nodes[i]["versionKey"]["version"]) for i in keep if nodes[i].get("versionKey", {}).get("version")]


def managed(name: str, version: str, depth=0):
    """{group:artifact: version} a Maven parent (and its own parents) manages for the poms that inherit from it;
    {} when nothing is known, None when unreachable."""
    data = _cached("requirements", "maven", name, version, _package_url("v3alpha", "maven", name, version, "requirements"))
    if data is None:
        return None
    maven = data.get("maven", {})
    out = {d["resolvedName"]: d["resolvedVersion"] for d in maven.get("dependencyManagement", []) if d.get("resolvedName") and d.get("resolvedVersion")}
    parent = maven.get("parent")
    if parent and parent.get("name") and parent.get("version") and depth < 5:
        above = managed(parent["name"], parent["version"], depth + 1) or {}
        out = {**above, **out}
    return out
