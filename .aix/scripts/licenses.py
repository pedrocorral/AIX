"""aix code licenses — the licence of every installed dependency, read from the package metadata on disk (never the
network): Python dist-info under the project's venv, npm node_modules, the Cargo registry cache for Cargo.lock,
the local Maven repository for pom.xml. Each licence is classed permissive / weak copyleft / strong copyleft /
proprietary / unknown; the gate fails on strong copyleft, proprietary and unknown unless `.aix/config.yaml` says
otherwise (`licenses_allow: [...]`, `licenses_known:` package -> licence). A package listed in a manifest but
not installed is reported as such: install, then re-run. What this is not: legal advice, or a scan of what the
code links to at runtime."""
import json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import ROOT

PERMISSIVE = ("MIT", "BSD", "APACHE", "ISC", "0BSD", "UNLICENSE", "ZLIB", "PSF", "PYTHON", "CC0", "BLUEOAK", "WTFPL", "BOOST", "BSL-1", "X11", "MIT-0", "PUBLIC DOMAIN", "ARTISTIC", "MPL-1")
WEAK = ("LGPL", "MPL", "EPL", "CDDL", "CPL", "OSL", "CC-BY", "EUROPEAN UNION PUBLIC")
STRONG = ("AGPL", "GPL", "SSPL", "EUPL", "CC-BY-SA", "BUSL", "COMMONS CLAUSE")
CLASSES = ("permissive", "weak copyleft", "strong copyleft", "proprietary", "unknown")


def _by_keywords(licence: str) -> str:
    """The class of one licence id or name, by the words in it; LGPL is weak although it contains GPL."""
    if licence in ("UNLICENSED", "PROPRIETARY", "COMMERCIAL"):
        return "proprietary"
    if any(k in licence for k in STRONG) and "LGPL" not in licence:
        return "strong copyleft"
    if any(k in licence for k in WEAK):
        return "weak copyleft"
    return "permissive" if any(k in licence for k in PERMISSIVE) else "unknown"


def classify(text, allow=frozenset()) -> str:
    """One class for a licence string; `A OR B` takes the most permissive, `A AND B` the most restrictive; an id in
    `allow` counts as permissive wherever it appears."""
    licence = (text or "").strip().upper().replace("LICENCE", "LICENSE")
    if licence in allow:
        return "permissive"
    if not licence or "UNKNOWN" in licence or licence.startswith("SEE LICENSE"):
        return "unknown"
    if " OR " in licence:
        return min((classify(p, allow) for p in licence.split(" OR ")), key=CLASSES.index)
    if " AND " in licence:
        return max((classify(p, allow) for p in licence.split(" AND ")), key=CLASSES.index)
    return _by_keywords(licence)


# ---- the four ecosystems, from disk --------------------------------------------------------------------------------

def _python_installed(root: Path) -> list:
    """(name, version, licence, 'python') from every dist-info under the project's virtual environment."""
    out = []
    for info in list(root.glob(".venv/lib*/python*/site-packages/*.dist-info")) + list(root.glob("venv/lib*/python*/site-packages/*.dist-info")):
        meta = (info / "METADATA").read_text(encoding="utf-8", errors="replace") if (info / "METADATA").exists() else ""
        name = re.search(r"^Name:\s*(.+)$", meta, re.M)
        version = re.search(r"^Version:\s*(.+)$", meta, re.M)
        out.append((name.group(1).strip() if name else info.name.split("-")[0], version.group(1).strip() if version else "?", _python_licence(meta), "python"))
    return out


def _python_licence(meta: str) -> str:
    expr = re.search(r"^License-Expression:\s*(.+)$", meta, re.M)
    if expr:
        return expr.group(1).strip()
    classifier = re.findall(r"^Classifier:\s*License ::(?: OSI Approved ::)?\s*(.+)$", meta, re.M)
    if classifier:
        return classifier[0].strip()
    field = re.search(r"^License:\s*(.+)$", meta, re.M)
    return field.group(1).strip() if field and field.group(1).strip().upper() != "UNKNOWN" else ""


def _npm_installed(root: Path) -> list:
    """(name, version, licence, 'npm') from every package.json inside a node_modules folder (scoped ones included)."""
    out = []
    for f in list(root.rglob("node_modules/*/package.json")) + list(root.rglob("node_modules/@*/*/package.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            continue
        lic = data.get("license") or data.get("licenses") or ""
        lic = lic.get("type", "") if isinstance(lic, dict) else " OR ".join(x.get("type", "") for x in lic) if isinstance(lic, list) else lic
        out.append((data.get("name", f.parent.name), str(data.get("version", "?")), lic, "npm"))
    return out


def _cargo_installed(root: Path) -> list:
    """(name, version, licence, 'cargo') for Cargo.lock packages whose source sits in the registry cache."""
    lock = root / "Cargo.lock"
    if not lock.exists():
        return []
    registry = Path(os.environ.get("CARGO_HOME") or (Path.home() / ".cargo")) / "registry" / "src"
    out = []
    for name, version in re.findall(r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"', lock.read_text(encoding="utf-8", errors="replace")):
        toml = next(iter(registry.glob(f"*/{name}-{version}/Cargo.toml")), None)
        if toml is None:
            continue
        lic = re.search(r'^license\s*=\s*"([^"]+)"', toml.read_text(encoding="utf-8", errors="replace"), re.M)
        out.append((name, version, lic.group(1) if lic else "", "cargo"))
    return out


def _maven_installed(root: Path) -> list:
    """(name, version, licence, 'maven') for pom.xml dependencies present in the local Maven repository."""
    pom = root / "pom.xml"
    if not pom.exists():
        return []
    repo = Path(os.environ.get("MAVEN_REPO") or (Path.home() / ".m2" / "repository"))
    out = []
    for group, artifact, version in re.findall(r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<$]+)</version>", pom.read_text(encoding="utf-8", errors="replace")):
        dep_pom = repo / group.replace(".", "/") / artifact / version / f"{artifact}-{version}.pom"
        if not dep_pom.exists():
            continue
        lic = re.search(r"<licenses>\s*<license>\s*<name>([^<]+)</name>", dep_pom.read_text(encoding="utf-8", errors="replace"))
        out.append((f"{group}:{artifact}", version, lic.group(1).strip() if lic else "", "maven"))
    return out


def declared_not_installed(root: Path, installed: set) -> list:
    """Names in requirements*.txt / package.json / Cargo.lock / pom.xml that no metadata on disk covers."""
    names = set()
    for f in root.glob("requirements*.txt"):
        names |= {re.split(r"[<>=!~\[; ]", l.strip())[0].lower() for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip() and not l.startswith(("#", "-"))}
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            names |= set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
        except ValueError:
            pass   # a package.json that is not JSON declares nothing we can name
    return sorted(n for n in names if n.lower() not in installed)


# ---- config, report, gate ------------------------------------------------------------------------------------------

def config_licenses() -> dict:
    """From .aix/config.yaml: `licenses_allow` (licence ids accepted whatever their class) and `licenses_known`
    (package -> licence, what a LICENSE file said when the metadata did not)."""
    import layers
    cfg = layers.config(ROOT)
    return {"allow": {str(x).upper() for x in (cfg.get("licenses_allow") or [])}, "known": {str(k).lower(): str(v) for k, v in (cfg.get("licenses_known") or {}).items()}}


def rows(root: Path, cfg: dict) -> list:
    """(name, version, licence, ecosystem, class) for every installed package, `known:` applied, sorted worst first."""
    out = []
    for name, version, lic, eco in _python_installed(root) + _npm_installed(root) + _cargo_installed(root) + _maven_installed(root):
        lic = cfg["known"].get(name.lower(), lic)
        cls = classify(lic, cfg["allow"])
        out.append((name, version, lic or "(none)", eco, cls))
    return sorted(out, key=lambda r: (-CLASSES.index(r[4]), r[0].lower()))


ADVICE = {"strong copyleft": "allowed only when the product's licence is compatible (an ADR says so); else replace, or `licenses_allow:` with the reason",
          "proprietary": "check the terms you agreed to; record them in an ADR",
          "unknown": "read the package's LICENSE file; record it under `licenses_known:` in .aix/config.yaml",
          "weak copyleft": "fine as an unmodified library; keep the notice, share changes to the library itself"}


def _head_lines(root: Path, table: list, missing: list) -> list:
    counts = {c: sum(1 for r in table if r[4] == c) for c in CLASSES}
    ecosystems = sorted({r[3] for r in table})
    per_eco = ", ".join(f"{e} {sum(1 for r in table if r[3] == e)}" for e in ecosystems)
    return [f"Licences — {root.name}", "", f"  installed packages {len(table)} ({per_eco or 'nothing installed'}); declared but not installed: {len(missing)}",
            "  " + "   ".join(f"{c} {counts[c]}" for c in CLASSES), ""]


def render(root: Path, table: list, missing: list) -> str:
    """The report: the counts, then every package that is not permissive with its advice, then what is not installed."""
    lines = _head_lines(root, table, missing)
    lines += [f"  {cls.upper().replace(' COPYLEFT', ''):8s} {name} {version}  {lic}  ({eco})   -> {ADVICE[cls]}" for name, version, lic, eco, cls in table if cls != "permissive"]
    lines += [f"  NOT INSTALLED  {n}   -> install the dependencies, then re-run" for n in missing[:20]]
    lines.append("  Read from metadata on disk, never the network; not legal advice; runtime linking and vendored code are not seen.")
    lines.append("  --gate fails on strong copyleft, proprietary and unknown; `.aix/config.yaml` `licenses_allow: [...]` and `licenses_known:` decide exceptions.")
    return "\n".join(lines)


def main(args):
    root = ROOT
    cfg = config_licenses()
    table = rows(root, cfg)
    missing = declared_not_installed(root, {r[0].lower() for r in table})
    text = render(root, table, missing)
    print(text)
    if "--report" in args:
        out = ROOT / "docs" / "tests" / "code-licenses.md"
        out.write_text("# Licences (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    bad = [r for r in table if r[4] in ("strong copyleft", "proprietary", "unknown")]
    if "--gate" in args and bad:
        sys.exit(f"GATE FAILED: {len(bad)} licence(s) to decide")
    if "--gate" in args:
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
