"""Leaf: the dependency manifests and lockfiles of a project, read into (ecosystem, name, version, file).

Lockfiles are complete (every package that will be installed): uv/poetry/pdm/Cargo.lock, package-lock.json,
pnpm-lock.yaml, yarn.lock (v1 and berry), Pipfile.lock, Gemfile.lock, composer.lock, go.sum. Declarations are
direct only and need resolution before they say anything about what runs: `==` pins in requirements*.txt and the
dependencies of a pom.xml (`read_pom`, with properties, dependencyManagement and the parent it inherits from).
Ecosystem names are OSV's (PyPI, npm, Maven, crates.io, RubyGems, Packagist, Go)."""
import json, re
import xml.etree.ElementTree as ET
from pathlib import Path

from codefiles import SKIP, rel

LOCK_TOML = re.compile(r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"')
PNPM_LINE = re.compile(r"^\s{2}['\"]?/?(@?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?)@(\d[0-9A-Za-z.\-+]*)", re.M)
YARN_VERSION = re.compile(r'^\s+version:?\s*"?([^"\s]+)"?\s*$')
GEM_SPEC = re.compile(r"^    ([A-Za-z0-9_.\-]+) \(([^)\s]+)\)", re.M)
GO_SUM = re.compile(r"^(\S+) v([^\s/]+) h1:", re.M)
PROPERTY = re.compile(r"\$\{([^}]+)\}")
GRADLE_DEP = re.compile(r"^\s*(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|annotationProcessor|developmentOnly)\s*\(?\s*['\"]([\w.-]+):([\w.-]+)(?::([\w.-]+))?['\"]", re.M)
TOML_SECTION = re.compile(r"^\[(\w+)\]\s*$", re.M)
TOML_LIB = re.compile(r"^([\w-]+)\s*=\s*(?:\"([^\"]+)\"|\{([^}]*)\})\s*$", re.M)


def manifest_files(root: Path, pattern: str) -> list:
    return [f for f in root.rglob(pattern) if not any(s in f.relative_to(root).parts for s in SKIP)]


def _text(f: Path) -> str:
    return f.read_text(encoding="utf-8", errors="replace")


def _json(f: Path):
    try:
        return json.loads(_text(f))
    except json.JSONDecodeError:
        return {}


# ---- declarations: direct dependencies only ------------------------------------------------------------------------

def pinned_requirements(root: Path):
    for f in manifest_files(root, "*requirements*.txt"):
        for line in _text(f).splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([0-9][^\s;#]*)", line)
            if m:
                yield ("PyPI", m.group(1).lower(), m.group(2), rel(f))


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _child(node, name: str) -> str:
    for c in node:
        if _local(c.tag) == name:
            return (c.text or "").strip()
    return ""


def _find(node, name: str):
    return next((c for c in node if _local(c.tag) == name), None)


def _properties(project) -> dict:
    props = {"project.version": _child(project, "version"), "project.groupId": _child(project, "groupId")}
    parent = _find(project, "parent")
    if parent is not None:
        props["project.parent.version"] = props["parent.version"] = _child(parent, "version")
        props["project.version"] = props["project.version"] or props["parent.version"]
    node = _find(project, "properties")
    for c in (node if node is not None else []):
        props[_local(c.tag)] = (c.text or "").strip()
    return props


def _substitute(value: str, props: dict, depth=0) -> str:
    out = PROPERTY.sub(lambda m: props.get(m.group(1), m.group(0)), value)
    return out if out == value or depth > 5 else _substitute(out, props, depth + 1)


def _dependency_nodes(project, *path: str) -> list:
    node = project
    for name in path:
        node = _find(node, name) if node is not None else None
    return [c for c in node if _local(c.tag) == "dependency"] if node is not None else []


def _coordinates(dep, props: dict) -> tuple:
    """(group:artifact, version or '', scope, exclusions) with properties substituted; a still-unresolved `${x}` is ''."""
    name = f"{_substitute(_child(dep, 'groupId'), props)}:{_substitute(_child(dep, 'artifactId'), props)}"
    version = _substitute(_child(dep, "version"), props)
    exclusions = _find(dep, "exclusions")
    excluded = [f"{_child(e, 'groupId')}:{_child(e, 'artifactId')}" for e in (exclusions if exclusions is not None else []) if _local(e.tag) == "exclusion"]
    return name, "" if "${" in version else version, _child(dep, "scope"), excluded


def read_pom(f: Path) -> tuple:
    """(dependencies, managed, parent): dependencies as (name, version or '', scope, exclusions), managed as the
    pom's own dependencyManagement {name: version} (already applied to the dependencies), parent as (name, version)
    or None. A version left '' is managed by the parent (resolve it there)."""
    try:
        project = ET.parse(f).getroot()
    except ET.ParseError:
        return [], {}, None
    props = _properties(project)
    managed = {n: v for n, v, _s, _x in (_coordinates(d, props) for d in _dependency_nodes(project, "dependencyManagement", "dependencies")) if v}
    deps = [(name, version or managed.get(name, ""), scope, excluded)
            for name, version, scope, excluded in (_coordinates(d, props) for d in _dependency_nodes(project, "dependencies"))]
    parent = _find(project, "parent")
    parent_key = (f"{_child(parent, 'groupId')}:{_child(parent, 'artifactId')}", _substitute(_child(parent, "version"), props)) if parent is not None else None
    return deps, managed, parent_key


def poms(root: Path) -> list:
    """[(file, dependencies, managed, parent)] for every pom.xml, see read_pom."""
    return [(rel(f), *read_pom(f)) for f in manifest_files(root, "pom.xml")]


# ---- lockfiles: complete -------------------------------------------------------------------------------------------

def toml_locks(root: Path):
    for name in ("uv.lock", "poetry.lock", "pdm.lock", "Cargo.lock"):
        eco = "crates.io" if name == "Cargo.lock" else "PyPI"
        for f in manifest_files(root, name):
            for m in LOCK_TOML.finditer(_text(f)):
                yield (eco, m.group(1), m.group(2), rel(f))


def npm_locks(root: Path):
    for f in manifest_files(root, "package-lock.json"):
        for path, info in _json(f).get("packages", {}).items():
            if path.startswith("node_modules/") and "version" in info:
                yield ("npm", path.split("node_modules/")[-1], info["version"], rel(f))
    for f in manifest_files(root, "pnpm-lock.yaml"):
        for m in PNPM_LINE.finditer(_text(f)):
            yield ("npm", m.group(1), m.group(2), rel(f))
    for f in manifest_files(root, "yarn.lock"):
        yield from _yarn(f)


def _yarn(f: Path):
    """yarn v1 (`"name@range", "name@range":` then `  version "x"`) and berry (`"name@npm:range":` then `  version: x`)."""
    name = None
    for line in _text(f).splitlines():
        if line and not line[0].isspace() and line.rstrip().endswith(":") and not line.startswith("#"):
            key = line.rstrip(":").split(",")[0].strip().strip('"')
            name = key[:key.rfind("@")] if "@" in key[1:] else None
            continue
        m = YARN_VERSION.match(line)
        if m and name:
            yield ("npm", name, m.group(1), rel(f))
            name = None


def _pipfile_locks(root: Path):
    for f in manifest_files(root, "Pipfile.lock"):
        data = _json(f)
        for section in ("default", "develop"):
            for name, info in data.get(section, {}).items():
                if isinstance(info, dict) and info.get("version", "").startswith("=="):
                    yield ("PyPI", name.lower(), info["version"][2:], rel(f))


def _gem_locks(root: Path):
    for f in manifest_files(root, "Gemfile.lock"):
        for m in GEM_SPEC.finditer(_text(f)):
            yield ("RubyGems", m.group(1), m.group(2), rel(f))


def _composer_locks(root: Path):
    for f in manifest_files(root, "composer.lock"):
        data = _json(f)
        for pk in data.get("packages", []) + data.get("packages-dev", []):
            if pk.get("name") and pk.get("version"):
                yield ("Packagist", pk["name"], pk["version"].lstrip("v"), rel(f))


def _go_sums(root: Path):
    for f in manifest_files(root, "go.sum"):
        for m in GO_SUM.finditer(_text(f)):
            yield ("Go", m.group(1), m.group(2), rel(f))


def other_locks(root: Path):
    yield from _pipfile_locks(root)
    yield from _gem_locks(root)
    yield from _composer_locks(root)
    yield from _go_sums(root)


def lockfile_dependencies(root: Path) -> list:
    """Every (ecosystem, name, version, file) the lockfiles pin, once per lockfile (each lockfile is fixed on its own)."""
    seen, out = set(), []
    for d in [*toml_locks(root), *npm_locks(root), *other_locks(root)]:
        if d not in seen:
            seen.add(d); out.append(d)
    return out


# ---- Gradle: the version catalog and the build scripts -----------------------------------------------------------------

def _toml_sections(text: str) -> dict:
    """{section: text} of a flat TOML file (gradle/libs.versions.toml has versions, libraries, bundles, plugins)."""
    parts = TOML_SECTION.split(text)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _catalog_entry(body: str, versions: dict) -> tuple:
    """(group:artifact, version) of one `{ module = "g:a", version = "1" }` / `version.ref = "v"` / `group =, name =` entry."""
    fields = dict(re.findall(r"([\w.]+)\s*=\s*\"([^\"]*)\"", body))
    name = fields.get("module") or (f"{fields.get('group')}:{fields.get('name')}" if fields.get("group") else "")
    version = fields.get("version") or versions.get(fields.get("version.ref", ""), "")
    return name, version


def version_catalog(f: Path) -> tuple:
    """(libraries [(name, version)], plugins {id: version}) of a Gradle version catalog."""
    sections = _toml_sections(_text(f))
    versions = dict(re.findall(r"^([\w-]+)\s*=\s*\"([^\"]+)\"", sections.get("versions", ""), re.M))
    libraries, plugins = [], {}
    for alias, literal, body in TOML_LIB.findall(sections.get("libraries", "")):
        name, version = (literal.rsplit(":", 1)[0], literal.rsplit(":", 1)[1]) if literal and literal.count(":") == 2 else _catalog_entry(body or "", versions)
        if name:
            libraries.append((name, version))
    for alias, literal, body in TOML_LIB.findall(sections.get("plugins", "")):
        fields = dict(re.findall(r"([\w.]+)\s*=\s*\"([^\"]*)\"", body or ""))
        if fields.get("id"):
            plugins[fields["id"]] = fields.get("version") or versions.get(fields.get("version.ref", ""), "")
    return libraries, plugins


def read_gradle(root: Path) -> list:
    """[(file, dependencies, managed, parent)] shaped like read_pom, one per Gradle project root: the catalog's
    libraries and every `implementation "g:a[:v]"` of its build scripts as direct dependencies; a version left ''
    is managed by the Spring Boot plugin's BOM when the catalog or a script names that plugin."""
    out = []
    for build in manifest_files(root, "build.gradle") + manifest_files(root, "build.gradle.kts"):
        base = build.parent
        catalog = base / "gradle" / "libs.versions.toml"
        libraries, plugins = version_catalog(catalog) if catalog.exists() else ([], {})
        scripts = _gradle_scripts(base)
        boot = plugins.get("org.springframework.boot") or next(iter(re.findall(r"id\s*\(?['\"]org\.springframework\.boot['\"]\)?\s*version\s*['\"]([\w.-]+)['\"]", scripts)), "")
        deps = _gradle_deps(libraries, scripts)
        if deps:
            out.append((rel(build), deps, {}, ("org.springframework.boot:spring-boot-dependencies", boot) if boot else None))
    return out


def _gradle_scripts(base: Path) -> str:
    return "\n".join(_text(g) for g in list(base.glob("*.gradle")) + list(base.glob("gradle/*.gradle")) + list(base.glob("*.gradle.kts")))


def _gradle_deps(libraries: list, scripts: str) -> list:
    return [(name, version, "", []) for name, version in libraries] + [(f"{g}:{a}", v or "", "", []) for g, a, v in GRADLE_DEP.findall(scripts)]
