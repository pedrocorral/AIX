"""Leaf: the isolations AIX recommends for a project, drafted from its module graph (`aix code isolations
--propose`). One isolation per code root; one part per folder below it (the first folder that holds code, so a
lone `app/` or `src/<package>/` wrapper is skipped), one more level of parts with `--depth 2`. A root's own files
(main.py, the composition root) belong to the root isolation itself.

  frontiers for each isolation "." (accepting it limits the isolation to its top level), then the deepest folders
            code outside it reaches today, each `proposed` with its evidence (the imports reaching that deep): a
            person accepts or rejects each one (`--review`)
Test files are exempt (they exercise internals). Everything the frontiers do not limit is allowed. The suggestions
also serve an existing declaration: new ones are merged in as proposed, decided ones are never touched."""
import datetime, re
from collections import defaultdict
from pathlib import PurePosixPath as P

from graphmetrics import is_test



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


def top_names(roots: list) -> dict:
    """root -> its isolation name: the folder's name, or its whole path when two roots share a name (backend/src,
    frontend/src -> backend-src, frontend-src)."""
    short = {r: name_of(P(r).name if r != "." else "project") for r in roots}
    clash = {n for n in short.values() if list(short.values()).count(n) > 1}
    return {r: (name_of(r.replace("/", "-")) if short[r] in clash else short[r]) for r in roots}


def units(roots: list, files: list, depth: int) -> dict:
    """file -> isolation name; and the paths glob of every isolation, in `paths` (returned as the second item)."""
    owner, paths, names = {}, {}, top_names(roots)
    for root in roots:
        top = names[root]
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


def _outside_reach(owner: dict, edges: set) -> dict:
    """isolation -> {folder of a file outside code reaches, relative to the file's path: import count}, per
    isolation of the file's chain (a file of a part is inside its parent too)."""
    out = defaultdict(lambda: defaultdict(int))
    for a, b in edges:
        A, B = owner.get(a), owner.get(b)
        for n in _chain(B or ""):
            if A and not (A == n or A.startswith(n + ".")):
                out[n][str(P(b).parent)] += 1
    return out


def _deepest(folders: dict, base: str) -> dict:
    """{frontier relative to base: imports}: the reached folders that are not on the way to a deeper reached one."""
    rel = {("." if f == base else f[len(base) + 1:] if base != "." else f): n for f, n in folders.items()}
    return {f: n for f, n in rel.items() if not any(o != f and (f == "." or o.startswith(f + "/")) for o in rel)}


def frontier_suggestions(owner: dict, edges: set, bases: dict) -> dict:
    """isolation -> {frontier: imports reaching that deep}. Always the top level "." (accepting it limits the isolation;
    its count is every import from outside), then the deepest folders reached below it."""
    reach = _outside_reach(owner, edges)
    out = {}
    for n, base in bases.items():
        if base is not None:
            deeper = {f: c for f, c in _deepest(reach.get(n, {}), base).items() if f != "."}
            out[n] = {".": sum(reach.get(n, {}).values()), **deeper}
    return out


def _chain(name: str) -> list:
    parts = name.split(".") if name else []
    return [".".join(parts[:i]) for i in range(len(parts), 0, -1)]


# ---- the draft --------------------------------------------------------------------------------------------------

def _specs(paths: dict, frontiers: dict) -> dict:
    """The declaration of each isolation, parents first, every frontier proposed ("." first)."""
    return {n: {"paths": paths[n], "frontiers": {f: "proposed" for f in sorted(frontiers.get(n, {".": 0}), key=lambda f: (f != ".", f))}}
            for n in sorted(paths, key=lambda x: (x.count("."), x))}


def _without_tests(roots: list, files: list, edges: set) -> tuple:
    """Roots, files and edges with tests left out: a test exercises internals and is no part of the design."""
    return ([r for r in roots if not is_test(r)], [f for f in files if not is_test(f)],
            {e for e in edges if not is_test(e[0]) and not is_test(e[1])})


def bases_of(paths: dict) -> dict:
    """isolation -> the folder its frontiers are relative to (`src/orders/**` -> `src/orders`)."""
    from isodecl import base_folder
    return {n: base_folder(globs) for n, globs in paths.items()}


def propose(roots: list, files: list, edges: set, depth: int = 1) -> tuple:
    """(declaration as a dict, the frontier evidence {isolation: {frontier: imports}})."""
    roots, code, edges = _without_tests(roots, files, edges)
    owner, paths = units(roots, code, depth)
    evidence = frontier_suggestions(owner, edges, bases_of(paths))
    return {"tests": "exempt", "isolations": _specs(paths, evidence)}, evidence


def evidence_lines(evidence: dict) -> list:
    """Comment lines: why each frontier is proposed."""
    return [f"#   {n} {f}: " + (("limit it to its top level; " if f == "." else "open down to here; ") + (f"{c} import(s) from outside" if c else "nothing outside reaches in"))
            for n, fs in sorted(evidence.items()) for f, c in sorted(fs.items(), key=lambda kv: (kv[0] != ".", kv[0]))]


def to_yaml(decl: dict, evidence: dict = None) -> str:
    """The draft as the declaration file, with the evidence behind each frontier."""
    from isoedit import render_block
    today = datetime.date.today().isoformat()
    lines = [f"# Isolations proposed by `aix code isolations --propose` on {today}, from the code as it is.",
             "# Every frontier is `proposed`: `aix code isolations --review` accepts or rejects each one. Everything the",
             "# frontiers do not limit is allowed. `--accept` records the contracts and writes the ADR a person accepts.", "",
             f"tests: {decl.get('tests', 'exempt')}", "isolations:"]
    for name, spec in decl["isolations"].items():
        lines += render_block(name, spec)
    if evidence:
        lines += ["", "# Frontiers proposed: \".\" limits the isolation to its top level, a folder opens the way down to it",
                  "# (the deepest folders code outside reaches today):", *evidence_lines(evidence)]
    return "\n".join(lines) + "\n"
