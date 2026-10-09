"""Leaf: the isolations AIX recommends for a project, drafted from its module graph (`aix code isolations
--propose`). One isolation per code root; one part per folder below it (the first folder that holds code, so a
lone `app/` or `src/<package>/` wrapper is skipped), one more level of parts with `--depth 2`. A root's own files
(main.py, the composition root) belong to the root isolation itself, which may use every part.

  may_use   what each part uses today, minus the edges that are defects: an edge that closes a cycle between two
            parts (the fewest cuts, ideal.cycle_cuts) or points up the layers (graphmetrics.layer_of) is left out
            and listed to fix, so the proposal is the code's own shape with its defects removed, not blessed
  exposes   the files code outside the part uses today: the smallest contract the code already keeps
Test files are exempt (they exercise internals). The draft is a starting point a person prunes: every permission
removed is a rule the code must then keep."""
import datetime, re
from collections import defaultdict
from pathlib import PurePosixPath as P

from graphmetrics import is_test, layer_of
from ideal import cycle_cuts

UNSAFE = re.compile(r"""^[\s*&!|>'"%@`{\[,#?:-]|: | #|\s$""")


# ---- the units: which folder each file belongs to -----------------------------------------------------------------

def _below(here: str, files: list) -> list:
    """The path parts below `here` of every file inside it."""
    if here == ".":
        return [P(f).parts for f in files]
    return [P(f).relative_to(here).parts for f in files if f.startswith(here + "/")]


def _wrapper(root: str, files: list) -> str:
    """The first folder below a root that holds code directly or splits into several folders that hold code."""
    here = root
    while True:
        rel = _below(here, files)
        subs = {r[0] for r in rel}
        if any(len(r) == 1 for r in rel) or len(subs) != 1:
            return here
        here = subs.pop() if here == "." else f"{here}/{subs.pop()}"


def name_of(folder: str) -> str:
    """A folder name as an isolation name segment: lower case, letters, digits, `_` and `-`."""
    return re.sub(r"[^a-z0-9_-]+", "-", folder.lower()).strip("-") or "root"


def units(roots: list, files: list, depth: int) -> dict:
    """file -> isolation name; and the paths glob of every isolation, in `paths` (returned as the second item)."""
    owner, paths = {}, {}
    for root in roots:
        top = name_of(P(root).name if root != "." else "project")
        mine = [f for f in files if root == "." or f.startswith(root + "/") or f == root]
        if not mine:
            continue
        paths[top] = [f"{root}/**" if root != "." else "**"]
        base = _wrapper(root, mine)
        for f in mine:
            owner[f] = _unit_of(f, base, top, depth, paths)
    return owner, paths


def _unit_of(f: str, base: str, top: str, depth: int, paths: dict) -> str:
    rel = P(f).relative_to(base).parts if base != "." else P(f).parts
    name, folder = top, base
    for part in rel[:-1][:depth]:
        folder = str(P(folder) / part) if folder != "." else part
        name = f"{name}.{name_of(part)}"
        paths.setdefault(name, [f"{folder}/**"])
    return name


# ---- permissions without the defects ------------------------------------------------------------------------------

def _common(a: str, b: str):
    pa, pb = a.split("."), b.split(".")
    n = next((i for i, (x, y) in enumerate(zip(pa, pb)) if x != y), min(len(pa), len(pb)))
    return ".".join(pa[:n]) or None


def _tops(a: str, b: str) -> tuple:
    """The two siblings below the nearest common isolation on the way to a and to b."""
    c = _common(a, b)
    depth = c.count(".") + 1 if c else 0
    return ".".join(a.split(".")[:depth + 1]), ".".join(b.split(".")[:depth + 1])


def unit_edges(owner: dict, edges: set) -> tuple:
    """((sibling, sibling) -> the file edges behind it, isolation -> the sibling pairs its files use). Pairs are taken
    below the nearest common isolation; every isolation from the user up to its sibling records the pair, because
    a part that declares may_use lists everything it uses. A parent's own files using its parts, and a part using
    its parent, need no permission."""
    pairs, users = defaultdict(list), defaultdict(set)
    for a, b in edges:
        A, B = owner.get(a), owner.get(b)
        if not A or not B or A == B or B.startswith(A + ".") or A.startswith(B + "."):
            continue
        pair = _tops(A, B)
        pairs[pair].append((a, b))
        for n in _chain(A)[:_chain(A).index(pair[0]) + 1]:
            users[n].add(pair)
    return pairs, users


def defects(paths: dict, uedges: dict) -> dict:
    """(part, part) -> why it is left out of the proposal: closes a cycle, or points up the layers."""
    out = {}
    for arc, members in cycle_cuts(set(n for e in uedges for n in e), set(uedges)).items():
        out[arc] = f"closes a cycle among {', '.join(sorted(members))}"
    for a, b in uedges:
        la, lb = layer_of(paths[a][0].rstrip("/*")), layer_of(paths[b][0].rstrip("/*"))
        if la is not None and lb is not None and la < lb:
            out.setdefault((a, b), f"points up the layers ({a}: layer {la}, {b}: layer {lb})")
    return out


def exposes(owner: dict, edges: set, paths: dict) -> dict:
    """isolation -> the files code outside it uses today."""
    out = {n: set() for n in paths}
    for a, b in edges:
        A, B = owner.get(a), owner.get(b)
        for n in _chain(B or ""):
            if A and not (A == n or A.startswith(n + ".")):
                out[n].add(b)
    return out


def _chain(name: str) -> list:
    parts = name.split(".") if name else []
    return [".".join(parts[:i]) for i in range(len(parts), 0, -1)]


# ---- the draft --------------------------------------------------------------------------------------------------

def _permitted(users: dict, cut: dict) -> dict:
    """isolation -> the siblings it may use: what its files use, the defect pairs left out."""
    return {n: {pair[1] for pair in used if pair not in cut} for n, used in users.items()}


def _specs(paths: dict, shown: dict, may_use: dict) -> dict:
    """The declaration of each isolation, parents first. A part always declares may_use (an empty list too)."""
    isos = {}
    for n in sorted(paths, key=lambda x: (x.count("."), x)):
        spec = {"paths": paths[n], "exposes": sorted(shown[n])}
        if n.count(".") or may_use.get(n):
            spec["may_use"] = sorted(may_use.get(n, ()))
        isos[n] = spec
    return isos


def _without_tests(roots: list, files: list, edges: set) -> tuple:
    """Roots, files and edges with tests left out: a test exercises internals and is no part of the design."""
    return ([r for r in roots if not is_test(r)], [f for f in files if not is_test(f)],
            {e for e in edges if not is_test(e[0]) and not is_test(e[1])})


def propose(roots: list, files: list, edges: set, depth: int = 1) -> tuple:
    """(declaration as a dict, the defects left out as [(from, to, why, example edge)])."""
    roots, code, edges = _without_tests(roots, files, edges)
    owner, paths = units(roots, code, depth)
    uedges, users = unit_edges(owner, edges)
    cut = defects(paths, uedges)
    kept = edges - {e for pair in cut for e in uedges[pair]}   # a file reached only by a defect is not part of a contract
    isos = _specs(paths, exposes(owner, kept, paths), _permitted(users, cut))
    left_out = [(a, b, why, sorted(uedges[(a, b)])[0]) for (a, b), why in sorted(cut.items())]
    return {"tests": "exempt", "isolations": isos}, left_out


def _q(v: str) -> str:
    return '"' + v.replace('"', '\\"') + '"' if UNSAFE.search(v) else v


def _flow(values: list) -> str:
    return "[" + ", ".join(_q(str(v)) for v in values) + "]"


def to_yaml(decl: dict, left_out: list) -> str:
    """The draft as the declaration file, with the defects it left out as comments."""
    today = datetime.date.today().isoformat()
    lines = [f"# Isolations proposed by `aix code isolations --propose` on {today}, from the code as it is.",
             "# Prune it: every may_use entry or exposed file you remove is a rule the code must then keep.",
             "# `aix code isolations --accept` records the contracts and writes the ADR a person accepts.", "",
             f"tests: {decl.get('tests', 'exempt')}", "isolations:"]
    for name, spec in decl["isolations"].items():
        lines.append(f"  {name}:")
        lines += [f"    {key}: {_flow(spec[key])}" for key in ("paths", "exposes", "may_use") if key in spec]
    if left_out:
        lines += ["", "# Left out (defects to fix, not permissions):"]
        lines += [f"#   {a} -> {b}: {why} (e.g. {ea} -> {eb})" for a, b, why, (ea, eb) in left_out]
    return "\n".join(lines) + "\n"
