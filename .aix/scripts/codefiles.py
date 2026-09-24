"""Leaf: which files are code. The configured code roots (`aix code find`, paths.code_roots), the source
extensions the `aix code` tools understand, and the walk that yields source files below a root."""
import re, sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git", "target", ".next", ".aix", "docs", "vendor", "vendors", "third_party", "third-party"}
MINIFIED = (".min.js", ".min.css", ".bundle.js", "-min.js")   # never the project's code


def code_roots():
    """Where the code tools look by default: the `paths.code_roots` of .aix/config.yaml that exist in this project;
    when none does (code at the root, or in a package named after the project) the whole project, hidden and
    SKIP folders excepted."""
    if (ROOT / "AIX-DEVELOPMENT.md").exists():
        return [".aix/scripts", "tests"]  # the kit itself: its code is the tools, skipped as `.aix` in every project
    roots = ["backend", "frontend", "shared", "infra", "src", "app", "tests", "lib"]
    cfg = ROOT / ".aix" / "config.yaml"
    if cfg.exists():
        m = re.search(r"^\s+code_roots:\s*\[(.*?)\]", cfg.read_text(encoding="utf-8"), re.M)
        if m:
            roots = [x.strip() for x in m.group(1).split(",") if x.strip()]
    found = [r for r in roots if (ROOT / r).exists()]
    return outermost(found) or ["."]


def outermost(roots: list) -> list:
    """Roots with those inside another root dropped: `.` with `src` and `tests` is `.` alone, else every file
    under `src/` would be measured twice (and every function would be its own clone)."""
    def inside(r: str, other: str) -> bool:
        return r != other and (other == "." or (ROOT / r).resolve().is_relative_to((ROOT / other).resolve()))
    return [r for r in roots if not any(inside(r, o) for o in roots)]


CODE_ROOTS = code_roots()


def default_roots():
    """CODE_ROOTS for a tool run without paths, saying so once when it falls back to the whole project."""
    if CODE_ROOTS == ["."]:
        print("code_roots: none of the configured folders exists here; scanning the whole project (`aix code find` sets them)", file=sys.stderr)
    return CODE_ROOTS
EXT = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".rs": "rust", ".java": "java"}
HUB_FAN = 3


# ---- file discovery -------------------------------------------------------------------------------------

def _is_source(f: Path, base: Path) -> bool:
    """A non-empty source file whose path below `base` crosses no skipped or hidden folder."""
    inner = f.relative_to(base).parts[:-1] if base.is_dir() else ()
    return f.is_file() and f.suffix in EXT and not f.name.endswith(MINIFIED) and not any(s in SKIP or s.startswith(".") for s in inner) and f.stat().st_size > 0


def source_files(roots):
    for root in roots:
        base = (ROOT / root) if not Path(root).is_absolute() else Path(root)
        if not base.exists():
            continue
        for f in ([base] if base.is_file() else base.rglob("*")):  # SKIP applies below the given base only: an explicit `.aix/scripts` target is measured
            if _is_source(f, base):
                yield f  # empty files (bare __init__.py) are not nodes


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)
