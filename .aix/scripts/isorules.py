"""Leaf: one edge of the module graph judged against the isolation declaration (isodecl), and the declaration judged
against the edges (permissions and exposed files nothing uses).

An edge a -> b, with A and B the deepest isolations holding a and b:
  same isolation                      allowed
  B is a part of A (a parent's file)  allowed; b must be exposed by every part entered below A
  A is a part of B (a child)          allowed: a family's own files are inside its boundary
  otherwise, below their nearest common isolation L, A sits in A' and B in B':
    the nearest isolation from A up to A' that declares `may_use` decides: it must name B' or a part of B' that
    holds b (naming a part enters it directly). None declares one: siblings inside L are free; at the top
    (no L) nothing is allowed.
    then every isolation entered from there down to B must expose b.
A FORBIDDEN edge has no permission; a HIDDEN one reaches a file the isolation keeps to itself."""
from collections import namedtuple

Verdict = namedtuple("Verdict", "kind a b owner_a owner_b message")


def _below(d, top: str, name: str) -> list:
    """The isolations from top down to name (both included); top must hold name."""
    return list(reversed(d.chain(name)[:d.chain(name).index(top) + 1]))


def _common(d, x: str, y: str):
    """The nearest isolation holding both, or None (they meet only at the top)."""
    ys = set(d.chain(y))
    return next((n for n in d.chain(x) if n in ys), None)


def _child_toward(d, top, name: str) -> str:
    """The part of `top` (or the top isolation, when top is None) on the way down to name."""
    chain = d.chain(name)
    return chain[-1] if top is None else chain[chain.index(top) - 1]


def _hidden_in(d, entry: str, b_owner: str, b: str):
    """The first isolation from entry down to b's own that does not expose b, else None."""
    return next((n for n in _below(d, entry, b_owner) if not d.isos[n].exposes_file(b)), None)


def _deciding(d, a_owner: str, a_top: str):
    """(the isolation whose may_use decides, its list) from a's own up to a_top, or (None, None)."""
    for n in _below(d, a_top, a_owner)[::-1]:
        if d.isos[n].may_use is not None:
            return n, d.isos[n].may_use
    return None, None


def _entry(d, allowed: list, b_top: str, b_owner: str):
    """The isolation a permission enters on the way to b: an entry of `allowed` that is b_top or a part of it
    holding b; the deepest such entry wins. None when nothing in the list reaches b."""
    hits = [x for x in allowed if d.is_within(x, b_top) and d.is_within(b_owner, x)]
    return max(hits, key=lambda x: x.count(".")) if hits else None


def judge(d, a: str, b: str):
    """None when the edge is allowed, else a Verdict (FORBIDDEN or HIDDEN)."""
    A, B = d.owner_of(a), d.owner_of(b)
    if A is None or B is None or A == B:
        return None
    if d.is_within(B, A):
        hidden = _hidden_in(d, _child_toward(d, A, B), B, b)
        return _hidden(a, b, A, B, hidden)
    if d.is_within(A, B):
        return None
    L = _common(d, A, B)
    a_top, b_top = _child_toward(d, L, A), _child_toward(d, L, B)
    who, allowed = _deciding(d, A, a_top)
    if who is None:
        if L is None:
            return Verdict("FORBIDDEN", a, b, A, B, f"`{a_top}` declares no `may_use`: a top isolation may use nothing it does not name")
        return _hidden(a, b, A, B, _hidden_in(d, b_top, B, b))
    entry = _entry(d, allowed, b_top, B)
    if entry is None:
        names = ", ".join(allowed) or "nothing"
        return Verdict("FORBIDDEN", a, b, A, B, f"`{who}` may use {names}; not `{b_top}`")
    return _hidden(a, b, A, B, _hidden_in(d, entry, B, b))


def _hidden(a: str, b: str, A: str, B: str, hidden_by):
    if hidden_by is None:
        return None
    return Verdict("HIDDEN", a, b, A, B, f"`{hidden_by}` does not expose {b}")


def forbidden_targets(d, name: str) -> list:
    """The isolations `name` may not use at all: the siblings, at every level of its chain, that no permission
    reaches (a top isolation's siblings when it names none of them)."""
    out = []
    for other in sorted(d.isos):
        if d.is_within(other, name) or d.is_within(name, other):
            continue
        L = _common(d, name, other)
        a_top, b_top = _child_toward(d, L, name), _child_toward(d, L, other)
        if b_top != other:
            continue   # name the sibling, not each of its parts
        who, allowed = _deciding(d, name, a_top)
        if (who is None and L is None) or (who is not None and not any(d.is_within(x, other) for x in allowed)):
            out.append(other)
    return out


# ---- the declaration against the code: what it allows and nothing uses ------------------------------------------

def _between_families(d, a: str, b: str):
    """(A, B) when an edge crosses from one isolation to another that is neither its part nor its parent, else None."""
    A, B = d.owner_of(a), d.owner_of(b)
    if not A or not B or A == B or d.is_within(B, A) or d.is_within(A, B):
        return None
    return A, B


def unused_permissions(d, edges: set) -> list:
    """(isolation, entry) for every may_use entry no allowed edge goes through: removing it tightens the rules."""
    used = set()
    for a, b in edges:
        pair = _between_families(d, a, b)
        used |= _permissions_used(d, *pair) if pair else set()
    declared = [(n, x) for n in sorted(d.isos) for x in d.isos[n].may_use or []]
    return [(n, x) for n, x in declared if (n, x) not in used and x in d.isos]


def _permissions_used(d, A: str, B: str) -> set:
    """(isolation, entry) for every declaring isolation from A up to A' whose list lets the edge through: a parent's
    entry is used when its parts' edges need it to stay within the parent's list."""
    L = _common(d, A, B)
    a_top, b_top = _child_toward(d, L, A), _child_toward(d, L, B)
    out = set()
    for n in _below(d, a_top, A):
        entry = _entry(d, d.isos[n].may_use or [], b_top, B)
        if entry:
            out.add((n, entry))
    return out


def _inbound(d, edges: set) -> dict:
    """isolation -> its files that code outside it uses."""
    out = {}
    for a, b in edges:
        user = d.owner_of(a) or ""
        for n in d.chain(d.owner_of(b) or ""):
            if not d.is_within(user, n):
                out.setdefault(n, set()).add(b)
    return out


def _exposed_of(d, name: str, files: list) -> list:
    iso = d.isos[name]
    if not iso.exposes:
        return []
    return [f for f in files if d.is_within(d.owner_of(f) or "", name) and iso.exposes_file(f)]


def unused_exposes(d, edges: set, files: list) -> list:
    """(isolation, file) for every exposed file nothing outside the isolation uses: a smaller contract is a
    stronger one. Only isolations that declare `exposes`."""
    inbound = _inbound(d, edges)
    return [(n, f) for n in sorted(d.isos) for f in _exposed_of(d, n, files) if f not in inbound.get(n, set())]
