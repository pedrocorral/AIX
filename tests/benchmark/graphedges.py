"""Section 30 of docs/tests/benchmark-engines.md: the module graph's edges (depedges.py, what `aix code graph` and
`aix code isolations` read) against a referee per language, file to file, on the cached extended projects.

  Python   grimp, the graph under import-linter (BENCH_DIR/venv)
  JS/TS    dependency-cruiser with TypeScript (BENCH_DIR/node/bin)
  Rust     cargo-modules `dependencies` with items (BENCH_DIR/cargo/bin), each item mapped to the file of its module;
           an edge into another crate of the workspace is compared at the crate
  Java     jdeps -verbose:class on the classes javac builds from src/main/java (a project javac can build alone)

Recall = referee edges ours has; precision = our edges the referee has. Only files both sides see, tests left out.
Every edge on one side only is printed with `--diff`, to be read by hand. A missing referee is skipped and said so.
Not part of the test suite. Run: `python tests/benchmark/graphedges.py [PROJECT...] [--diff]`."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engines import BENCH, PROJECTS, env, is_test, prepare

NODE_BIN, CARGO_BIN = BENCH / "node" / "bin", BENCH / "cargo" / "bin"
PY = BENCH / "venv" / "bin" / "python"
# project -> (language, roots ours reads, referee arguments)
CASES = {
    "flask": ("python", ["src"], {"src": "src", "package": "flask"}),
    "requests": ("python", ["src"], {"src": "src", "package": "requests"}),
    "pygoat": ("python", ["pygoat", "introduction", "challenge"], {"src": ".", "package": ["pygoat", "introduction", "challenge"]}),
    "express": ("js", ["lib", "index.js"], {"roots": ["lib", "index.js"]}),
    "NodeGoat": ("js", ["app", "server.js"], {"roots": ["app", "server.js"]}),
    "juice-shop": ("js", ["routes", "lib", "models", "data", "server.ts", "app.ts"], {"roots": ["routes", "lib", "models", "data", "server.ts", "app.ts"]}),
    "excalidraw": ("js", ["src"], {"roots": ["src"]}),
    "ripgrep": ("rust", ["crates"], {}),
    "bat": ("rust", ["src"], {}),
    "commons-lang": ("java", ["src/main/java"], {}),
}
OURS = ("import sys, json; sys.path.insert(0, '.aix/scripts'); from depedges import module_graph; "
        "n, e = module_graph({roots!r}, ownership={own}); print(json.dumps(sorted(e)))")


def ours(tmp: Path, roots: list, lang: str) -> set:
    """Our edges; for Rust without `mod x;` declarations, as the referee runs with --no-owns (uses only)."""
    out = subprocess.run([sys.executable, "-c", OURS.format(roots=roots, own=lang != "rust")], cwd=tmp, env=env(), capture_output=True, text=True, timeout=1800).stdout
    return {tuple(e) for e in json.loads(out or "[]")}


# ---- referees ----------------------------------------------------------------------------------------------------

GRIMP = """import grimp, json, sys
sys.path.insert(0, sys.argv[1])
pkgs = json.loads(sys.argv[2])
g = grimp.build_graph(*pkgs, include_external_packages=False)
print(json.dumps([(m, i) for m in g.modules for i in g.find_modules_directly_imported_by(m)]))"""


def _py_file(tmp: Path, src: str, module: str):
    base = tmp / src / Path(*module.split("."))
    for f in (base.with_suffix(".py"), base / "__init__.py"):
        if f.is_file():
            return str(f.relative_to(tmp))
    return None


def grimp_edges(tmp: Path, a: dict):
    if not PY.exists():
        return None
    pkgs = a["package"] if isinstance(a["package"], list) else [a["package"]]
    out = subprocess.run([str(PY), "-c", GRIMP, str(tmp / a["src"]), json.dumps(pkgs)], capture_output=True, text=True, timeout=1800)
    pairs = json.loads(out.stdout or "[]")
    files = {(_py_file(tmp, a["src"], m), _py_file(tmp, a["src"], i)) for m, i in pairs}
    return {(x, y) for x, y in files if x and y and x != y}


JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs")


def depcruise_edges(tmp: Path, a: dict):
    tool = NODE_BIN / "depcruise"
    if not tool.exists():
        return None
    cmd = [str(tool), *a["roots"], "--no-config", "--ts-pre-compilation-deps", "--output-type", "json", "--exclude", "node_modules"]
    if (tmp / "tsconfig.json").exists():
        cmd += ["--ts-config", "tsconfig.json"]
    run_env = dict(env(), PATH=os.pathsep.join([str(NODE_BIN), env()["PATH"]]), NODE_PATH=str(BENCH / "node" / "lib" / "node_modules"))
    out = subprocess.run(cmd, cwd=tmp, env=run_env, capture_output=True, text=True, timeout=1800).stdout
    data = json.loads(out or '{"modules": []}')
    edges = set()
    for m in data["modules"]:
        for d in m.get("dependencies", []):
            r = d.get("resolved", "")
            if not d.get("couldNotResolve") and not d.get("coreModule") and r.endswith(JS_EXT) and "node_modules" not in r:
                edges.add((m["source"], r))
    return edges


def _crate_of(tmp: Path, f: str):
    """The folder holding the Cargo.toml a file belongs to."""
    p = (tmp / f).parent
    while p != tmp and not (p / "Cargo.toml").exists():
        p = p.parent
    return p


def _members(tmp: Path) -> dict:
    """crate name (underscored) -> crate folder, for every Cargo.toml in the project."""
    out = {}
    for c in sorted(tmp.rglob("Cargo.toml"), key=lambda c: len(c.parts), reverse=True):   # the shallowest written last, so it wins
        if "target" in c.parts:
            continue
        m = re.search(r'^\[package\](?:(?!^\[).)*?^name\s*=\s*"([^"]+)"', c.read_text(encoding="utf-8"), re.M | re.S)
        if m:
            out[m.group(1).replace("-", "_")] = c.parent
    return out


def _rust_module_file(crate_dir: Path, path: list, root_file: Path):
    """The file of `crate::a::b` (an inline module is its enclosing file)."""
    for n in range(len(path), 0, -1):
        base = crate_dir / "src" / Path(*path[:n])
        for f in (base.with_suffix(".rs"), base / "mod.rs"):
            if f.is_file():
                return f
    return root_file


DOT_EDGE = re.compile(r'"([\w:]+)"\s*->\s*"([\w:]+)"\s*\[label="uses"')


def _crate_edges(tmp: Path, name: str, cdir: Path, members: dict) -> set:
    root = cdir / "src" / "lib.rs" if (cdir / "src" / "lib.rs").exists() else cdir / "src" / "main.rs"
    kind = ["--lib"] if root.name == "lib.rs" else ["--bin", name.replace("_", "-")]
    cmd = [str(CARGO_BIN / "cargo-modules"), "dependencies", "--package", name.replace("_", "-"), *kind, "--no-sysroot", "--no-owns"]   # items kept: a use of another crate's type is an item edge
    out = subprocess.run(cmd, cwd=cdir, env=dict(env(), PATH=os.pathsep.join([str(CARGO_BIN), env()["PATH"]])), capture_output=True, text=True, timeout=1800).stdout
    edges = set()
    for a, b in DOT_EDGE.findall(out):
        fa = _rust_module_file(cdir, a.split("::")[1:], root)
        head = b.split("::")[0]
        if head == name:
            fb = _rust_module_file(cdir, b.split("::")[1:], root)
        elif head in members:
            fb = "crate:" + str(members[head].relative_to(tmp))
        else:
            continue
        edges.add((str(fa.relative_to(tmp)), fb if isinstance(fb, str) else str(fb.relative_to(tmp))))
    return edges


def cargo_modules_edges(tmp: Path, _a: dict):
    if not (CARGO_BIN / "cargo-modules").exists():
        return None
    members = _members(tmp)
    edges = set()
    for name, cdir in members.items():
        edges |= _crate_edges(tmp, name, cdir, members)
    return {(a, b) for a, b in edges if a != b}


def jdeps_edges(tmp: Path, _a: dict):
    if not shutil.which("jdeps"):
        return None
    src, out_dir = tmp / "src" / "main" / "java", tmp / "jdeps-classes"
    files = [str(f) for f in src.rglob("*.java") if f.name != "module-info.java"]
    built = subprocess.run(["javac", "-nowarn", "-encoding", "UTF-8", "-proc:none", "-d", str(out_dir), *files], capture_output=True, text=True, timeout=1800)
    if built.returncode:
        print(f"  javac failed: {built.stderr[-400:]}")
        return None
    out = subprocess.run(["jdeps", "-verbose:class", "-filter:none", str(out_dir)], capture_output=True, text=True, timeout=1800).stdout
    edges = set()
    for a, b in re.findall(r"^\s+([\w.$]+)\s+->\s+([\w.$]+)\s", out, re.M):
        fa, fb = (src / (x.split("$")[0].replace(".", "/") + ".java") for x in (a, b))
        if fa.is_file() and fb.is_file() and fa != fb:
            edges.add((str(fa.relative_to(tmp)), str(fb.relative_to(tmp))))
    return edges


REFEREES = {"python": ("grimp", grimp_edges), "js": ("dependency-cruiser", depcruise_edges),
            "rust": ("cargo-modules", cargo_modules_edges), "java": ("jdeps", jdeps_edges)}


# ---- comparison ----------------------------------------------------------------------------------------------------

def _to_crates(tmp: Path, edges: set) -> set:
    """Ours with an edge into another workspace crate named by that crate, as the referee names it."""
    out = set()
    for a, b in edges:
        ca, cb = _crate_of(tmp, a), _crate_of(tmp, b)
        out.add((a, "crate:" + str(cb.relative_to(tmp))) if ca != cb else (a, b))
    return out


def _comparable(mine: set, ref: set) -> tuple:
    """Both sides restricted to the files both see (tests out); an edge into another crate stays as the crate."""
    seen = {x for e in mine for x in e} & {x for e in ref for x in e}
    return {e for e in mine if _counted(e, seen)}, {e for e in ref if _counted(e, seen)}


def _counted(edge: tuple, seen: set) -> bool:
    a, b = edge
    return a in seen and (b in seen or b.startswith("crate:")) and not is_test(a) and not is_test(b)


def _pct(part: int, whole: int):
    return round(100 * part / whole, 1) if whole else None


def _row(name: str, referee: str, mine: set, ref: set, diff: bool) -> dict:
    both = mine & ref
    row = dict(project=name, referee=referee, ours=len(mine), referee_edges=len(ref), both=len(both),
               recall=_pct(len(both), len(ref)), precision=_pct(len(both), len(mine)))
    if diff:
        row["only_referee"], row["only_ours"] = sorted(ref - mine), sorted(mine - ref)
    return row


def compare(name: str, diff: bool) -> dict:
    lang, roots, args = CASES[name]
    tmp = prepare(next(p for p in PROJECTS if p["name"] == name))
    try:
        referee, fn = REFEREES[lang]
        ref, mine = fn(tmp, args), ours(tmp, roots, lang)
        if ref is None:
            return dict(project=name, referee=referee, skipped=True)
        mine = _to_crates(tmp, mine) if lang == "rust" else mine
        return _row(name, referee, *_comparable(mine, ref), diff)
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def _line(r: dict) -> str:
    if r.get("skipped"):
        return f"{r['project']:<14}{r['referee']:<20}  skipped: the referee is not installed"
    return f"{r['project']:<14}{r['referee']:<20}{r['ours']:>7}{r['referee_edges']:>9}{r['both']:>7}{str(r['recall']) + ' %':>9}{str(r['precision']) + ' %':>11}"


def _diff_lines(rows: list) -> list:
    return [f"  {r['project']} {side}: {a} -> {b}" for r in rows for side in ("only_referee", "only_ours") for a, b in r.get(side, [])[:60]]


def main(argv):
    diff = "--diff" in argv
    names = [a for a in argv if not a.startswith("--")] or list(CASES)
    rows = [compare(n, diff) for n in names]
    print(f"{'project':<14}{'referee':<20}{'ours':>7}{'referee':>9}{'both':>7}{'recall':>9}{'precision':>11}")
    print("\n".join([_line(r) for r in rows] + (_diff_lines(rows) if diff else [])))
    out = Path(tempfile.gettempdir()) / "aix-graphedges.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nrows written to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
