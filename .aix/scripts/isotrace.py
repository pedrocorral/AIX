"""Leaf: requirements mapped onto isolations through the code markers (`@implements FR-ORDERS-001`). A requirement
whose code is spread over several unrelated isolations says the boundaries cut across a behaviour; an isolation
that implements requirements of several domains says it does more than one job. Advice for whoever draws the
boundaries (`aix code isolations --requirements`), never a gate."""
import re
from collections import defaultdict

from idcheck import MARK, tokens_in

SCATTERED = 3   # a requirement implemented in this many unrelated isolations
MIXED = 3       # an isolation implementing requirements of this many domains
REQUIREMENT = re.compile(r"^(FR|NFR|API)-([A-Z0-9]+)-\d+$")


def _implemented(text: str) -> list:
    """The requirement ids the `@implements` markers of a text name."""
    marks = [m.group(2) for m in MARK.finditer(text) if m.group(1) == "implements"]
    return [t for mark in marks for t in tokens_in(mark) if REQUIREMENT.match(t)]


def implements(files: list, root) -> dict:
    """requirement id -> the files whose markers say they implement it."""
    out = defaultdict(set)
    for f in files:
        for req in _implemented((root / f).read_text(encoding="utf-8", errors="replace")):
            out[req].add(f)
    return out


def _unrelated(d, names: set) -> list:
    """The names with every one that is a parent of another dropped (a part and its parent are one place)."""
    return sorted(n for n in names if not any(o != n and d.is_within(o, n) for o in names))


def trace(d, files: list, root) -> tuple:
    """(requirement -> isolations, isolation -> requirements) through the markers."""
    req_isos, iso_reqs = {}, defaultdict(set)
    for req, where in sorted(implements(files, root).items()):
        owners = {d.owner_of(f) for f in where} - {None}
        req_isos[req] = _unrelated(d, owners)
        for n in owners:
            iso_reqs[n].add(req)
    return req_isos, dict(iso_reqs)


def advice(req_isos: dict, iso_reqs: dict) -> list:
    """Lines for the requirements that are scattered and the isolations that are mixed."""
    out = [f"SCATTERED  {req} is implemented in {len(isos)} isolations ({', '.join(isos)}): the boundaries cut across one behaviour"
           for req, isos in req_isos.items() if len(isos) >= SCATTERED]
    for n, reqs in sorted(iso_reqs.items()):
        domains = sorted({REQUIREMENT.match(r).group(2) for r in reqs})
        if len(domains) >= MIXED:
            out.append(f"MIXED      {n} implements requirements of {len(domains)} domains ({', '.join(domains)}): one isolation, several jobs")
    return out
