#!/usr/bin/env python3
"""Leaf: detect the language runtimes a project targets, and where that is declared.

Python   pyproject.toml requires-python | .python-version | <venv>/pyvenv.cfg | python3 on PATH (assumed)
JS/TS    tsconfig.json compilerOptions.target (ES year) | package.json engines.node
Rust     Cargo.toml rust-version | edition
Java     pom.xml maven.compiler.release/source | build.gradle(.kts) languageVersion / sourceCompatibility
Returns {lang: (version_tuple_or_None, human_label, source)}; unknown versions are reported, never guessed."""
import json, re, shutil, subprocess
from pathlib import Path


def _min_version(spec: str):
    """'>=3.10,<4' -> (3, 10); '^3.11' / '~=3.9' / '3.12.*' -> the lower bound."""
    m = re.search(r"(?:>=|\^|~=|==|~)?\s*(\d+)\.(\d+)", spec)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _first(root: Path, names, depth=2):
    for d in [root, *[p for p in root.rglob("*") if p.is_dir() and len(p.relative_to(root).parts) <= depth and not any(s in p.parts for s in (".git", "node_modules", ".venv", "venv", "target", "dist", "build"))]]:
        for n in names:
            if (d / n).is_file():
                yield d / n


def python(root: Path):
    for f in _first(root, ["pyproject.toml"]):
        m = re.search(r'requires-python\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8", errors="replace"))
        if m and _min_version(m.group(1)):
            return _min_version(m.group(1)), f"Python {m.group(1)}", f"{f.relative_to(root)} requires-python"
    for f in _first(root, [".python-version"]):
        v = _min_version(f.read_text(encoding="utf-8").strip())
        if v:
            return v, f"Python {v[0]}.{v[1]}", str(f.relative_to(root))
    venvs = [root / d / "pyvenv.cfg" for d in (".venv", "venv")] + [c for sub in root.iterdir() if sub.is_dir() and not sub.name.startswith(".") for c in (sub / ".venv" / "pyvenv.cfg", sub / "venv" / "pyvenv.cfg")]
    for f in [v for v in venvs if v.is_file()]:
        m = re.search(r"^version(?:_info)?\s*=\s*(\d+)\.(\d+)", f.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            return (int(m.group(1)), int(m.group(2))), f"Python {m.group(1)}.{m.group(2)}", f"{f.relative_to(root)} (venv)"
    exe = shutil.which("python3") or shutil.which("python")
    if exe:
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10).stdout
            v = _min_version(out)
            if v:
                return v, f"Python {v[0]}.{v[1]}", "python on PATH (assumed: nothing in the project declares a version)"
        except Exception:
            pass
    return None, "Python: version unknown", "nothing declares it"


ES_TARGETS = {"es3": 3, "es5": 5, "es6": 2015, "es2015": 2015, "es2016": 2016, "es2017": 2017, "es2018": 2018, "es2019": 2019,
              "es2020": 2020, "es2021": 2021, "es2022": 2022, "es2023": 2023, "es2024": 2024, "esnext": 2024}


def javascript(root: Path):
    for f in _first(root, ["tsconfig.json", "tsconfig.base.json"]):
        m = re.search(r'"target"\s*:\s*"([^"]+)"', f.read_text(encoding="utf-8", errors="replace"))
        if m and m.group(1).lower() in ES_TARGETS:
            year = ES_TARGETS[m.group(1).lower()]
            return (year,), f"TypeScript, target {m.group(1)}", f"{f.relative_to(root)} compilerOptions.target"
    for f in _first(root, ["package.json"]):
        try:
            node = json.loads(f.read_text(encoding="utf-8", errors="replace")).get("engines", {}).get("node")
        except json.JSONDecodeError:
            node = None
        if node and _min_version(node):
            major = _min_version(node)[0]
            year = 2022 if major >= 18 else 2020 if major >= 14 else 2018 if major >= 10 else 2015
            return (year,), f"Node {node} (≈ ES{year})", f"{f.relative_to(root)} engines.node"
    return None, "JavaScript: target unknown", "no tsconfig target or engines.node"


def rust(root: Path):
    for f in _first(root, ["Cargo.toml"]):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'rust-version\s*=\s*"(\d+)\.(\d+)', text)
        if m:
            return (int(m.group(1)), int(m.group(2))), f"Rust {m.group(1)}.{m.group(2)}", f"{f.relative_to(root)} rust-version"
        m = re.search(r'edition\s*=\s*"(\d{4})"', text)
        if m:
            floor = {"2015": (1, 0), "2018": (1, 31), "2021": (1, 56), "2024": (1, 85)}.get(m.group(1), (1, 0))
            return floor, f"Rust edition {m.group(1)} (≥ {floor[0]}.{floor[1]})", f"{f.relative_to(root)} edition"
    return None, "Rust: version unknown", "no Cargo.toml"


def java(root: Path):
    for f in _first(root, ["pom.xml"]):
        m = re.search(r"<(?:maven\.compiler\.(?:release|source)|java\.version|release)>\s*(?:1\.)?(\d+)", f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return (int(m.group(1)),), f"Java {m.group(1)}", f"{f.relative_to(root)}"
    for f in _first(root, ["build.gradle", "build.gradle.kts"]):
        m = re.search(r"(?:languageVersion\s*=?\s*JavaLanguageVersion\.of\(|sourceCompatibility\s*=?\s*(?:JavaVersion\.VERSION_)?['\"]?(?:1\.)?)(\d+)", f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return (int(m.group(1)),), f"Java {m.group(1)}", f"{f.relative_to(root)}"
    return None, "Java: version unknown", "no pom.xml / build.gradle"


def detect(root: Path, langs=("python", "js", "rust", "java")):
    fns = {"python": python, "js": javascript, "rust": rust, "java": java}
    return {lang: fns[lang](root) for lang in langs}


if __name__ == "__main__":
    import sys
    for lang, (v, label, src) in detect(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()).items():
        print(f"{lang:7s} {label:40s} {src}")
