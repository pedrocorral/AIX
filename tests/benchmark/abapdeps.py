"""Section 23 of docs/tests/benchmark-engines.md: the ABAP module graph, dead objects and clones on abap2xlsx and
abapGit. No engine builds a module graph for ABAP to compare against, so the numbers are ours (`aix code graph`,
`dead`, `clones` on the installed copy) plus what the reader can be checked on by hand: the references by shape,
how many resolve to a project object, a sample of edges, and every dead candidate with the entry points that
exist. Run: `python tests/benchmark/abapdeps.py [abap2xlsx abapGit] [--edges N]`."""
import json, re, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import abapdeps   # noqa: E402

SHAPES = {"static or constant (x=>)": r"\b([A-Za-z_/][\w/]*)=>", "TYPE REF TO x": r"\bTYPE\s+REF\s+TO\s+([A-Za-z_/][\w/]*)",
          "NEW x( / CREATE OBJECT TYPE x": r"\bNEW\s+([A-Za-z_/][\w/]*)\s*\(|\bCREATE\s+OBJECT\s+\S+\s+TYPE\s+([A-Za-z_/][\w/]*)",
          "INHERITING FROM / INTERFACES": r"\bINHERITING\s+FROM\s+([A-Za-z_/][\w/]*)|^\s*INTERFACES\s+([A-Za-z_/][\w/]*)",
          "RAISE EXCEPTION TYPE / CATCH": r"\bRAISE\s+EXCEPTION\s+TYPE\s+([A-Za-z_/][\w/]*)|\bCATCH\s+([A-Za-z_/][\w/]*)",
          "CALL FUNCTION / INCLUDE / SUBMIT": r"\bCALL\s+FUNCTION\s+'([^']+)'|^\s*INCLUDE\s+([A-Za-z_/][\w/]*)|\bSUBMIT\s+([A-Za-z_/][\w/]*)"}


def _bucket(name: str, idx: dict) -> str:
    return "project" if name in idx["objects"] else "standard" if name.startswith(("cl_", "if_", "cx_")) else "other"


def shapes(project: Path, idx: dict) -> list:
    """Per shape: references, those naming a project object, those naming SAP standard (cl_, if_, cx_), the rest."""
    counts = {k: Counter() for k in SHAPES}
    for f in [f for f in project.rglob("*.abap") if ".aix" not in f.parts]:
        text = f.read_text(encoding="utf-8", errors="replace")
        for shape, rx in SHAPES.items():
            for m in re.finditer(rx, text, re.I | re.M):
                counts[shape]["refs"] += 1
                counts[shape][_bucket(next(g for g in m.groups() if g).lower(), idx)] += 1
    return [f"   {shape:34s} refs {c['refs']:6d}  project {c['project']:6d}  SAP standard {c['standard']:6d}  other {c['other']:6d}" for shape, c in counts.items()]


def tool(copy: Path, *args) -> str:
    return subprocess.run([str(copy / ".aix" / "bin" / "aix"), "code", *args], cwd=copy, env=engines.env(), capture_output=True, text=True).stdout


def _summary_lines(graph: str, dead: str, clones: str) -> list:
    keep = ("A (the code)", "cycles", "distance", "entry modules", "DEAD MODULES", "functions analysed")
    lines = [l.strip() for text in (graph, dead, clones) for l in text.splitlines() if l.strip().startswith(keep)]
    return ["   " + l for l in lines] + ["   " + l.strip() for l in re.findall(r"^    \S+\.abap$", dead, re.M)[:20]]


def _edge_sample(files: list, idx: dict, n: int) -> list:
    """The first n edges the reader produces, file by file, to read by hand against the code."""
    out = []
    for f in sorted(files, key=str):
        out += [f"     {f.name} -> {t.name}" for t in abapdeps.module_edges(f, idx)]
        if len(out) >= n:
            break
    return ["   edges to read by hand:"] + out[:n]


def report(project: dict, n_edges: int) -> str:
    tmp = engines.prepare(project)
    files = [f for f in tmp.rglob("*.abap") if ".aix" not in f.parts]
    idx = abapdeps.index(files)
    lines = [f"== {project['name']}: {len(files)} .abap files, {len(set(idx['node'].values()))} nodes"] + shapes(tmp, idx)
    lines += _summary_lines(tool(tmp, "graph"), tool(tmp, "dead"), tool(tmp, "clones"))
    return "\n".join(lines + _edge_sample(files, idx, n_edges))


def main(argv):
    n_edges = int(argv[argv.index("--edges") + 1]) if "--edges" in argv else 10
    names = [a for a in argv if not a.startswith("--") and not a.isdigit()] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name], n_edges))


if __name__ == "__main__":
    main(sys.argv[1:])
