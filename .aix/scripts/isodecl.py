"""Leaf: the isolation declaration (docs/requirements/isolations.yaml): the named parts of the code, which files
each holds, what each exposes, and which others each may use. Read, checked and fingerprinted here; judged in
isorules. An allow-list: anything not declared is forbidden.

    isolations:
      orders:              {paths: [src/orders/**], exposes: [src/orders/api.py], may_use: [billing, shared]}
      orders.pricing:      {paths: [src/orders/pricing/**]}     # nested by the dot: a part of orders
    data:
      card: {fields: [card_number, cvv], stays_in: [payments]}
    tests: exempt                                               # exempt (default) or checked

A file belongs to the deepest isolation whose paths match it. `may_use` absent inherits the parent's list (a top
isolation without one may use nothing); a nested list may only narrow its parent's, never widen it, and it lists
everything the part may use outside itself. Children use their parent's own files; the parent's own files use its
children; siblings are free until one declares `may_use`. From outside, every isolation entered on the way to a
file must expose it."""
import hashlib, json, re
from pathlib import Path

from codefiles import ROOT
from guard import checked
from yamlmini import parse_tree

DECL = "docs/requirements/isolations.yaml"
CONTRACTS = "docs/requirements/isolations.contracts.json"
NAME = re.compile(r"^[a-z0-9_-]+(?:\.[a-z0-9_-]+)*$")
ISO_KEYS = {"paths", "exposes", "may_use", "owner", "description"}
DATA_KEYS = {"fields", "stays_in", "never_to", "description"}
TOP_KEYS = {"isolations", "data", "tests", "owners"}
SINKS = ("logs", "http", "print")


class Iso:
    """One declared isolation."""
    def __init__(self, name: str, spec: dict):
        self.name, self.spec = name, spec
        self.paths = _as_list(spec.get("paths"))
        self.exposes = _as_list(spec["exposes"]) if "exposes" in spec else None     # None: everything visible
        self.may_use = _as_list(spec["may_use"]) if "may_use" in spec else None     # None: inherit the parent's
        self.owner, self.description = spec.get("owner"), spec.get("description", "")
        self.parent = name.rsplit(".", 1)[0] if "." in name else None
        self._path_rx = [glob_regex(g) for g in self.paths]
        self._expose_rx = [glob_regex(g) for g in self.exposes or []]

    def holds(self, rel: str) -> bool:
        return any(rx.match(rel) for rx in self._path_rx)

    def exposes_file(self, rel: str) -> bool:
        return self.exposes is None or any(rx.match(rel) for rx in self._expose_rx)


class Decl:
    """The parsed declaration, its problems, and the membership of files."""
    def __init__(self, raw: dict, source: str = DECL):
        self.raw, self.source, self.errors, self.warnings = raw, source, [], []
        self.isos = {n: Iso(n, s or {}) for n, s in (raw.get("isolations") or {}).items() if isinstance(s, (dict, type(None)))}
        self.data = {n: (s or {}) for n, s in (raw.get("data") or {}).items()} if isinstance(raw.get("data"), dict) else {}
        self.tests_checked = str(raw.get("tests", "exempt")).lower() == "checked"
        self._owner = {}

    # ---- the tree of names ----------------------------------------------------------------------------------------
    def chain(self, name: str) -> list:
        """name, its parent, ... up to the top isolation."""
        out = []
        while name:
            out.append(name)
            name = self.isos[name].parent if name in self.isos else None
        return out

    def is_within(self, inner: str, outer: str) -> bool:
        """inner is outer or nested somewhere below it."""
        return inner == outer or inner.startswith(outer + ".")

    def children(self, name: str) -> list:
        return sorted(n for n in self.isos if self.isos[n].parent == name)

    def effective_may_use(self, name: str):
        """The list in force for an isolation: its own, else the nearest ancestor's; [] at the top."""
        for n in self.chain(name):
            if self.isos[n].may_use is not None:
                return self.isos[n].may_use
        return []

    # ---- files ----------------------------------------------------------------------------------------------------
    def owner_of(self, rel: str):
        """The deepest isolation holding a file, or None. Two unrelated isolations holding it is a declaration error."""
        if rel not in self._owner:
            hits = sorted((n for n, iso in self.isos.items() if iso.holds(rel)), key=lambda n: n.count("."))
            deepest = hits[-1] if hits else None
            if deepest and any(not self.is_within(deepest, h) for h in hits):
                self.errors.append(f"{rel} is held by unrelated isolations {', '.join(hits)}: a file belongs to one part (or to a part and its parents)")
            self._owner[rel] = deepest
        return self._owner[rel]


def _as_list(v) -> list:
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


GLOB_TOKENS = re.compile(r"\*\*/|\*\*|\*|\?|[^*?]+")
GLOB_PARTS = {"**/": "(?:.*/)?", "**": ".*", "*": "[^/]*", "?": "[^/]"}


def _normal_glob(glob: str) -> str:
    g = glob.strip()
    g = g[2:] if g.startswith("./") else g
    return g + "**" if g.endswith("/") else g


def glob_regex(glob: str):
    """`src/orders/**` and `src/orders/` (everything below), `*.py` (one segment), `a/**/b.py` (any depth); a plain
    folder name means everything below it, a plain file name that file."""
    g = _normal_glob(glob)
    body = "".join(GLOB_PARTS.get(t) or re.escape(t) for t in GLOB_TOKENS.findall(g))
    tail = "(?:/.*)?$" if "*" not in g and "." not in Path(g).name else "$"
    return re.compile("^" + body + tail)


# ---- reading and checking -------------------------------------------------------------------------------------------

def load(root: Path = ROOT):
    """The declaration of a project, or None when it has none. A file that does not parse is a Decl with the error."""
    f = root / DECL
    if not f.exists():
        return None
    try:
        raw = parse_tree(f.read_text(encoding="utf-8"))
    except ValueError as e:
        d = Decl({}); d.errors.append(f"{DECL}: {e}")
        return d
    d = Decl(raw)
    check_shape(d)
    return d


def check_shape(d: Decl):
    """Everything that can be checked without the project's files: keys, names, parents, may_use, data."""
    if not isinstance(d.raw.get("isolations"), dict) or not d.raw["isolations"]:
        d.errors.append(f"{DECL}: no `isolations:` map")
        return
    d.errors += [f"{DECL}: unknown top-level key `{k}` (known: {', '.join(sorted(TOP_KEYS))})" for k in d.raw if k not in TOP_KEYS]
    for name in sorted(d.isos):
        _check_iso(d, d.isos[name])
    for name, spec in sorted(d.data.items()):
        _check_data(d, name, spec)


def _check_iso(d: Decl, iso: Iso):
    where = f"isolation `{iso.name}`"
    if not NAME.match(iso.name):
        d.errors.append(f"{where}: a name is lower-case words joined by dots (orders, orders.pricing)")
    if iso.parent and iso.parent not in d.isos:
        d.errors.append(f"{where}: its parent `{iso.parent}` is not declared")
    if not iso.paths:
        d.errors.append(f"{where}: no `paths:`")
    d.errors += [f"{where}: unknown key `{k}` (known: {', '.join(sorted(ISO_KEYS))})" for k in iso.spec if k not in ISO_KEYS]
    for target in iso.may_use or []:
        _check_permission(d, iso, target)


def _check_permission(d: Decl, iso: Iso, target: str):
    """A may_use entry names a declared isolation, not the isolation itself or one of its ancestors, and never widens
    what the parent may use."""
    where = f"isolation `{iso.name}` may_use `{target}`"
    if target not in d.isos:
        d.errors.append(f"{where}: no such isolation")
    elif d.is_within(iso.name, target):
        d.warnings.append(f"{where}: it is itself or its own parent; a part always reaches its parent's exposed files")
    elif d.is_within(target, iso.name):
        d.warnings.append(f"{where}: it is a part of `{iso.name}`; a part's own files always reach their children")
    elif iso.parent and not d.is_within(target, iso.parent) and not _covered(d, iso.parent, target):
        d.errors.append(f"{where}: widens the parent: `{iso.parent}` may not use `{target}`, so no part of it may")


def _covered(d: Decl, parent: str, target: str) -> bool:
    """The parent's list in force names target or an isolation target is part of."""
    return any(d.is_within(target, allowed) for allowed in d.effective_may_use(parent))


def _check_data(d: Decl, name: str, spec: dict):
    where = f"data `{name}`"
    if not isinstance(spec, dict) or not _as_list(spec.get("fields")):
        d.errors.append(f"{where}: no `fields:` (the field names that carry it)")
        return
    d.errors += [f"{where}: unknown key `{k}` (known: {', '.join(sorted(DATA_KEYS))})" for k in spec if k not in DATA_KEYS]
    d.errors += [f"{where}: stays_in `{n}` is not a declared isolation" for n in _as_list(spec.get("stays_in")) if n not in d.isos]
    d.errors += [f"{where}: never_to `{s}` is not a sink ({', '.join(SINKS)})" for s in _as_list(spec.get("never_to")) if s not in SINKS]


def check_files(d: Decl, files: list):
    """Everything that needs the files: each part inside its parent, each exposed glob inside its isolation and
    not hidden by a part, every file in at most one line of isolations (owner_of records that)."""
    outside = set()
    for rel in files:
        owner = d.owner_of(rel)
        if owner and owner not in outside and _outside_parents(d, rel, owner):
            outside.add(owner)
    for iso in d.isos.values():
        _check_exposes(d, iso, files)


def _outside_parents(d: Decl, rel: str, owner: str) -> bool:
    """True (and an error recorded once per part) when a file of a part is not held by one of its parents."""
    for n in d.chain(owner)[1:]:
        if not d.isos[n].holds(rel):
            d.errors.append(f"isolation `{owner}` holds {rel}, which its parent `{n}` does not: a part lies inside its parent")
            return True
    return False


def _hiding_part(d: Decl, name: str, f: str):
    """The part of `name`, on the way down to f, that does not expose f (a parent cannot expose what a part hides)."""
    inner = [c for c in d.chain(d.owner_of(f) or "") if c != name and d.is_within(c, name)]
    return next((c for c in inner if not d.isos[c].exposes_file(f)), None)


def _check_exposes(d: Decl, iso: Iso, files: list):
    if not iso.exposes:
        return
    exposed = [f for f in files if iso.exposes_file(f)]
    if not exposed:
        d.warnings.append(f"isolation `{iso.name}`: `exposes` matches no file")
        return
    _check_exposed_files(d, iso.name, exposed)


def _check_exposed_files(d: Decl, name: str, exposed: list):
    """Every exposed file is the isolation's own, and no part of it hides one."""
    outside = [f for f in exposed if not d.is_within(d.owner_of(f) or "", name)]
    if outside:
        d.errors.append(f"isolation `{name}` exposes {outside[0]}, which is not one of its files")
    hidden = [(f, _hiding_part(d, name, f)) for f in exposed]
    d.errors += [f"isolation `{name}` exposes {f}, which its part `{part}` does not expose" for f, part in hidden if part]


# ---- the fingerprint ------------------------------------------------------------------------------------------------

def fingerprint(raw: dict, contracts: dict) -> str:
    """sha256 over the declaration and the recorded contracts, both in canonical JSON: what an ADR accepts."""
    blob = json.dumps({"declaration": raw, "contracts": contracts}, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


@checked
def _contracts(data: dict) -> dict:
    """The recorded contracts are a map (isolation -> file -> name -> signature); anything else is refused here."""
    return data


def read_contracts(root: Path = ROOT) -> dict:
    """The contracts --accept recorded, or {} when there are none (or the file is not a JSON map)."""
    f = root / CONTRACTS
    if not f.exists():
        return {}
    try:
        return _contracts(json.loads(f.read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return {}
