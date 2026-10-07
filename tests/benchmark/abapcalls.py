"""Section 24 of docs/tests/benchmark-engines.md: ABAP `--functions` on abap2xlsx and abapGit. Ours: units, call
edges and the resolved ratio by shape, the dead candidates (private/protected gated, public noted). The reference
for dead methods is abaplint's `unused_methods` (private and protected only); for the call graph there is none, so
a sample of edges is printed to read by hand. Run: `python tests/benchmark/abapcalls.py [abap2xlsx abapGit]`."""
import json, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import abapcalls   # noqa: E402
from pyfuncgraph import RESOLUTION   # noqa: E402


def abaplint_unused(project: Path) -> list:
    """(file, line, method) abaplint's unused_methods reports."""
    base = json.loads(subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), "--default"], capture_output=True, text=True, env=_env()).stdout)
    cfg = project / "abaplint-unused.json"
    cfg.write_text(json.dumps({"global": base["global"], "syntax": base.get("syntax", {}), "rules": {"unused_methods": base["rules"]["unused_methods"]}}))
    out = subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), str(cfg)], cwd=project, capture_output=True, text=True, env=_env()).stdout
    cfg.unlink()
    return [(m.group(1), int(m.group(2)), m.group(3).lower()) for m in re.finditer(r'(\S+)\[(\d+), \d+\]\s+- Method "(\w+)" not used', out)]


def _env() -> dict:
    return dict(os.environ, PATH=os.pathsep.join([str(engines.BENCH / "node" / "bin"), os.environ["PATH"]]))


def _shape(recv: str, unit, idx) -> str:
    if recv in ("me", "super"):
        return "me/super"
    t = abapcalls._receiver_type(recv, unit.types, unit.owner, unit.name, idx)
    if not t:
        return "untyped receiver"
    if t not in idx.classes:
        return "typed, SAP or dictionary"
    return "typed, project interface" if idx.classes[t].interface else "typed, project class"


def shapes(files: list) -> Counter:
    """How the receiver and static calls of a project split by what the reader can know about them."""
    c, idx = Counter(), abapcalls._Index(files)
    for fx in files:
        for unit in fx.units:
            u = abapcalls._Unit(fx, unit, idx)
            for _w, text, _l in u.body:
                c.update(_shape(abapcalls._call_parts(m)[0].lower(), u, idx) for m in abapcalls.RECEIVER.finditer(text))
                c["static zcl_x=>m("] += sum(1 for m in abapcalls.STATIC.finditer(text) if abapcalls._call_parts(m)[0].lower() in idx.classes)
    return c


def _key(node: str) -> tuple:
    return node.split(":")[0].split("/")[-1], node.split(":")[-1]


def _dead_lines(dead: list, ab: list) -> list:
    ours = {_key(n) for n, _l, public in dead if not public}
    theirs = {(Path(f).name, m) for f, _l, m in ab}
    public = sum(1 for _n, _l, p in dead if p)
    lines = [f"   dead: private/protected {len(ours)} (gated), public noted {public}; abaplint unused_methods {len(ab)}, of which in ours {len(ours & theirs)}"]
    lines += [f"     abaplint only: {f}:{l} {m}" for f, l, m in ab if (Path(f).name, m) not in ours]
    return lines + _ours_only(dead, theirs)


def _ours_only(dead: list, theirs: set) -> list:
    rows = [(n, l) for n, l, public in dead if not public and _key(n) not in theirs]
    return [f"     ours only (private/protected): {n} (line {l})" for n, l in rows[:15]]


def report(project: dict) -> str:
    tmp = engines.prepare(project)
    roots = [str(tmp / r) for r in ("src", "deps", "test") if (tmp / r).is_dir()]
    files = abapcalls._files(roots)
    RESOLUTION.update(seen=0, matched=0)
    nodes, edges = abapcalls.function_graph(roots)
    ratio = 100 * RESOLUTION["matched"] / max(1, RESOLUTION["seen"])
    lines = [f"== {project['name']}: units {len(nodes)}, call edges {len(edges)}, resolved calls {RESOLUTION['matched']} of {RESOLUTION['seen']} ({ratio:.0f} %)"]
    lines += [f"   {k:28s} {v:6d}" for k, v in shapes(files).most_common()]
    lines += _dead_lines(abapcalls.dead_functions(roots), abaplint_unused(tmp))
    return "\n".join(lines + ["   edges to read by hand:"] + [f"     {a.split('/')[-1]} -> {b.split('/')[-1]}" for a, b in sorted(edges)[:10]])


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name]))


if __name__ == "__main__":
    main(sys.argv[1:])
