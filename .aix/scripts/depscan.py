"""Leaf: dependency hygiene per VUL-DEP-001. Unpinned requirements, manifests without a lock file, for Python, Node
and Rust."""
import re
from pathlib import Path

from codefiles import SKIP, rel
from securityrules import DOCKER_RULES


DEP = ("VUL-DEP-001", "CWE-1104")
PY_LOCKS = ("uv.lock", "poetry.lock", "pdm.lock", "requirements.txt", "requirements.lock")
JS_LOCKS = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb")


def _manifests(root: Path, pattern: str):
    return [f for f in root.rglob(pattern) if not any(s in f.parts for s in SKIP)]


def _has_lock(f: Path, locks) -> bool:
    return any((f.parent / l).exists() for l in locks)


def _unpinned_requirements(root: Path):
    for f in _manifests(root, "requirements*.txt"):
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            s = line.split("#")[0].strip()
            if s and not s.startswith(("-", "git+", "http")) and "==" not in s and "@" not in s:
                yield (*DEP, "unpinned dependency", rel(f), i, s, "pin exact versions (==) or use a lockfile (uv/poetry/pip-tools)", None)


ENGINES = {"node", "npm", "yarn", "pnpm", "bun"}   # `engines` names a runtime, not a dependency


def _is_library(text: str) -> bool:
    """A published package: no lockfile by convention (the consumer locks). package.json not private with an entry
    point; pyproject with classifiers or project URLs."""
    return ('"private": true' not in text and re.search(r'"(?:main|exports|module|types|files)"\s*:', text) is not None) \
        or re.search(r"^\s*classifiers\s*=|^\[project\.urls\]", text, re.M) is not None


def _node_manifests(root: Path):
    for f in _manifests(root, "package.json"):
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"([^"]+)"\s*:\s*"(\*|latest|>=?[^"]*|x)"', text):
            if m.group(1) in ENGINES:
                continue
            yield (*DEP, "unbounded dependency range", rel(f), text.count("\n", 0, m.start()) + 1, m.group(0), "use ^/~ ranges with a committed lockfile, or exact versions", None)
        if not _has_lock(f, JS_LOCKS) and not _is_library(text):
            yield (*DEP, "no lockfile next to package.json", rel(f), 1, "package.json without lockfile", "commit package-lock.json / pnpm-lock.yaml so builds are reproducible", None)


def _python_and_rust_manifests(root: Path):
    for f in _manifests(root, "pyproject.toml"):
        text = f.read_text(encoding="utf-8", errors="replace")
        declares = re.search(r"^\s*(?:dependencies|requires)\s*=", text, re.M)
        if declares and not _has_lock(f, PY_LOCKS) and not _is_library(text):
            yield (*DEP, "no lockfile next to pyproject.toml", rel(f), 1, "pyproject without uv.lock/poetry.lock", "commit a lockfile so builds are reproducible", None)
    for f in _manifests(root, "Cargo.toml"):
        has_deps = re.search(r"^\[dependencies\]", f.read_text(encoding="utf-8", errors="replace"), re.M)
        if has_deps and not any((p / "Cargo.lock").exists() for p in (f.parent, *f.parent.parents)):   # a workspace locks at its root
            yield (*DEP, "no Cargo.lock", rel(f), 1, "Cargo.toml without Cargo.lock", "commit Cargo.lock", None)


def scan_dependencies(root: Path):
    """Unpinned dependency declarations and missing lockfiles (VUL-DEP-001)."""
    return [*_unpinned_requirements(root), *_node_manifests(root), *_python_and_rust_manifests(root)]


# ---- Dockerfiles: the image runs as root, the base image is not pinned -------------------------------------------

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
