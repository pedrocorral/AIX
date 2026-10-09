"""Leaf: the review of proposed frontiers, one by one (`aix code isolations --review`). Each pending frontier is a
line with its evidence (how many imports from outside reach that deep today); in a terminal the checklist of
`aix code find` decides them: checked is accepted, unchecked rejected, q leaves every one pending. Without a
terminal (CI, an agent) the list is printed and nothing changes: deciding a frontier is a person's act."""
from collections import defaultdict

from graphmetrics import is_test
from isodecl import covers


def _entered(d, a: str, b: str) -> list:
    """(isolation, folder of b in it) for every isolation an edge enters from outside."""
    user = d.owner_of(a) or ""
    entered = [n for n in d.chain(d.owner_of(b) or "") if not d.is_within(user, n)]
    return [(n, d.isos[n].folder_in(b)) for n in entered if d.isos[n].folder_in(b) is not None]


def evidence(d, edges: set) -> dict:
    """(isolation, folder) -> imports from outside the isolation into that folder or below it."""
    out = defaultdict(int)
    code = [(a, b) for a, b in edges if not is_test(a) and not is_test(b)]
    for n, folder in (pair for a, b in code for pair in _entered(d, a, b)):
        for f in d.isos[n].pending():
            out[(n, f)] += covers(f, folder)
    return out


def rows(d, edges: set) -> list:
    counts = evidence(d, edges)
    return [{"name": f"{n} {f}", "iso": n, "folder": f, "on": True, "count": counts.get((n, f), 0)}
            for n in sorted(d.isos) for f in d.isos[n].pending()]


def describe(r) -> tuple:
    what = "top level" if r["folder"] == "." else "down to this folder"
    reach = f"{r['count']} import(s) reach this deep" if r["count"] else "nothing outside reaches in"
    return what, "", reach


def decisions(rows_: list, chosen) -> dict:
    """{(isolation, folder): accepted|rejected} from the checked names; {} when the review was cancelled."""
    if chosen is None:
        return {}
    return {(r["iso"], r["folder"]): ("accepted" if r["name"] in chosen else "rejected") for r in rows_}


def print_pending(rows_: list):
    print(f"Pending frontiers ({len(rows_)}): run `aix code isolations --review` in a terminal to accept or reject each")
    for r in rows_:
        what, _b, reach = describe(r)
        print(f"  {r['name']:<48} {what:<22} {reach}")
