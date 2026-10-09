"""Leaf: one edge of the module graph judged against the isolation frontiers (isodecl), and the declaration judged
against the edges (frontiers nothing reaches as deep). Everything the frontiers do not limit is allowed.

An edge a -> b, with A and B the deepest isolations holding a and b: the edge enters every isolation of B's line
(B, its parent, ...) that does not hold a. Each of them must let b through: b lies on its top level or on the way
down to one of its accepted frontiers (one with no accepted frontier lets everything through). A file of a part
using its parent's files enters nothing; a parent's file using its part enters the part. A HIDDEN edge reaches
deeper than a frontier allows."""
from collections import namedtuple

Verdict = namedtuple("Verdict", "kind a b owner_a owner_b message")


def _entered(d, a_owner: str, b_owner: str) -> list:
    """The isolations of b's line the edge enters, outermost first (none when a's isolation holds b's)."""
    return [n for n in reversed(d.chain(b_owner)) if not d.is_within(a_owner, n)]


def _hidden_in(d, entered: list, b: str):
    """The first isolation entered whose frontiers keep b closed, else None."""
    return next((n for n in entered if not d.isos[n].reachable(b)), None)


def judge(d, a: str, b: str):
    """None when the edge is allowed, else a HIDDEN Verdict."""
    A, B = d.owner_of(a), d.owner_of(b)
    if A is None or B is None or A == B:
        return None
    hidden_by = _hidden_in(d, _entered(d, A, B), b)
    if hidden_by is None:
        return None
    frontiers = ", ".join(f"`{f}`" for f in d.isos[hidden_by].accepted() if f != ".") or "its top level only"
    return Verdict("HIDDEN", a, b, A, B, f"{b} lies deeper than the frontiers of `{hidden_by}` (outsiders reach {frontiers})")


# ---- the declaration against the code: what it allows and nothing uses ------------------------------------------

def unused_frontiers(d, edges: set) -> list:
    """(isolation, frontier) for every accepted frontier below the top level that no code outside reaches as deep:
    a shallower frontier is a stronger one."""
    reached = set()
    for a, b in edges:
        user = d.owner_of(a) or ""
        for n in d.chain(d.owner_of(b) or ""):
            if not d.is_within(user, n):
                reached.add((n, d.isos[n].folder_in(b)))
    return [(n, f) for n in sorted(d.isos) for f in d.isos[n].accepted() if f != "." and (n, f) not in reached]


def pending_frontiers(d) -> list:
    """(isolation, frontier) for every frontier still proposed: a decision waiting for a person."""
    return [(n, f) for n in sorted(d.isos) for f in d.isos[n].pending()]
