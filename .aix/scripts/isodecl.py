"""Leaf: the isolation declaration (docs/requirements/isolations.yaml): the named parts of the code, which files
each holds, and how deep code outside each may reach into it (its frontiers). Read, checked and fingerprinted here;
judged in isorules. Everything the frontiers do not limit is allowed.

    isolations:
      persistence:         {paths: [src/persistence/**], frontiers: {".": accepted, ports/sql: proposed}}
      persistence.postgres: {paths: [src/persistence/postgres/**], frontiers: {".": accepted}}   # a part: the dot
      orders:              {paths: [src/orders/**], frontiers: {".": accepted}}
    tests: exempt                                               # exempt (default) or checked

Frontiers. A frontier is a folder of the isolation (relative to its one folder path; "." is its top level) with a
status: accepted, proposed or rejected. Accepting "." limits the isolation: code outside it calls its top level only;
each accepted folder opens the way down to it (that folder included, nothing deeper, nothing beside); a rejected
folder stays closed. An isolation with no accepted frontier limits nothing (rejecting "." keeps it open). The isolation's own files reach everything inside it, except where a part declares its
own frontiers: every isolation entered on the way to a file must let the caller through. A proposed frontier is
not in force until a person accepts it. A file belongs to the deepest isolation whose paths match it; a part uses
its parent's files freely."""
import hashlib, json, re
from pathlib import Path

from codefiles import ROOT
from guard import checked
from yamlmini import parse_tree

DECL = "docs/requirements/isolations.yaml"
CONTRACTS = "docs/requirements/isolations.contracts.json"
NAME = re.compile(r"^[a-z0-9_-]+(?:\.[a-z0-9_-]+)*$")
ISO_KEYS = {"paths", "frontiers", "owner", "description"}
GONE = {"exposes": "`exposes` became `frontiers`: how deep outsiders may reach",
        "may_use": "`may_use` is gone: everything the frontiers do not limit is allowed"}
STATUSES = ("accepted", "proposed", "rejected")
DATA_KEYS = {"fields", "stays_in", "never_to", "description"}
TOP_KEYS = {"isolations", "data", "tests", "owners"}
SINKS = ("logs", "http", "print")


class Iso:
    """One declared isolation."""
    def __init__(self, name: str, spec: dict):
        self.name, self.spec = name, spec
        self.paths = _as_list(spec.get("paths"))
        self.frontiers = _frontier_map(spec.get("frontiers"))                     # folder -> accepted|proposed|rejected
        self.base = base_folder(self.paths)                                       # the one folder frontiers are relative to
        self.owner, self.description = spec.get("owner"), spec.get("description", "")
        self.parent = name.rsplit(".", 1)[0] if "." in name else None
        self._path_rx = [glob_regex(g) for g in self.paths]

    def holds(self, rel: str) -> bool:
        return any(rx.match(rel) for rx in self._path_rx)

    @property
    def limited(self) -> bool:
        """An accepted frontier limits how deep outsiders reach; without one nothing is limited."""
        return "accepted" in self.frontiers.values()

    def accepted(self) -> list:
        return sorted(f for f, s in self.frontiers.items() if s == "accepted")

    def pending(self) -> list:
        return sorted(f for f, s in self.frontiers.items() if s == "proposed")

    def folder_in(self, rel: str):
        """The folder of a file relative to the isolation's folder ("." for its top level), else None."""
        if self.base is None or not (rel.startswith(self.base + "/") or self.base == "."):
            return None
        folder = str(Path(rel).parent)
        return "." if folder == self.base else (folder if self.base == "." else folder[len(self.base) + 1:])

    def reachable(self, rel: str) -> bool:
        """Code outside the isolation may call this file: nothing limited, the top level, or a folder on the way down
        to an accepted frontier (that frontier included, nothing deeper)."""
        folder = self.folder_in(rel)
        if not self.limited or folder is None or folder == ".":
            return True
        return any(f == folder or f.startswith(folder + "/") for f in self.accepted())


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


def _frontier_map(value) -> dict:
    """`{".": accepted, ports/sql: proposed}` as {folder: status}; a folder written with a trailing slash is the same."""
    if not isinstance(value, dict):
        return {}
    return {(str(k).strip().strip("/") or "."): str(v).strip().lower() for k, v in value.items()}


def base_folder(paths: list):
    """The one folder an isolation's paths name (`src/persistence/**`, `src/persistence/`), else None."""
    if len(paths) != 1:
        return None
    g = paths[0].strip()
    g = g[2:] if g.startswith("./") else g
    g = g[:-3] if g.endswith("/**") else g.rstrip("/")
    if g in ("**", ""):
        return "."
    return None if any(c in g for c in "*?[") or "." in Path(g).name else g


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
    """Everything that can be checked without the project's files: keys, names, parents, frontiers, data."""
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
    d.errors += [f"{where}: unknown key `{k}` (known: {', '.join(sorted(ISO_KEYS))})" + (f" ({GONE[k]})" if k in GONE else "")
                 for k in iso.spec if k not in ISO_KEYS]
    _check_frontier_shape(d, iso, where)


def _check_frontier_shape(d: Decl, iso: Iso, where: str):
    if "frontiers" in iso.spec and not isinstance(iso.spec["frontiers"], dict):
        d.errors.append(f"{where}: `frontiers` is a map of folder -> status ({{\".\": accepted, ports/sql: proposed}})")
    if iso.frontiers and iso.base is None:
        d.errors.append(f"{where}: frontiers need one folder path (`paths: [src/persistence/**]`)")
    d.errors += [f"{where}: frontier `{f}` has status `{s}` (one of {', '.join(STATUSES)})" for f, s in iso.frontiers.items() if s not in STATUSES]
    d.errors += [f"{where}: frontier `{f}` leaves the isolation's folder" for f in iso.frontiers if f.startswith("/") or ".." in f.split("/")]


def _check_data(d: Decl, name: str, spec: dict):
    where = f"data `{name}`"
    if not isinstance(spec, dict) or not _as_list(spec.get("fields")):
        d.errors.append(f"{where}: no `fields:` (the field names that carry it)")
        return
    d.errors += [f"{where}: unknown key `{k}` (known: {', '.join(sorted(DATA_KEYS))})" for k in spec if k not in DATA_KEYS]
    d.errors += [f"{where}: stays_in `{n}` is not a declared isolation" for n in _as_list(spec.get("stays_in")) if n not in d.isos]
    d.errors += [f"{where}: never_to `{s}` is not a sink ({', '.join(SINKS)})" for s in _as_list(spec.get("never_to")) if s not in SINKS]


def check_files(d: Decl, files: list):
    """Everything that needs the files: each part inside its parent, each frontier a folder of its isolation and not
    closed by a part, every file in at most one line of isolations (owner_of records that)."""
    outside = set()
    for rel in files:
        owner = d.owner_of(rel)
        if owner and owner not in outside and _outside_parents(d, rel, owner):
            outside.add(owner)
    for iso in d.isos.values():
        _check_frontiers(d, iso, files)


def _outside_parents(d: Decl, rel: str, owner: str) -> bool:
    """True (and an error recorded once per part) when a file of a part is not held by one of its parents."""
    for n in d.chain(owner)[1:]:
        if not d.isos[n].holds(rel):
            d.errors.append(f"isolation `{owner}` holds {rel}, which its parent `{n}` does not: a part lies inside its parent")
            return True
    return False


def _hiding_part(d: Decl, name: str, f: str):
    """The part of `name`, on the way down to f, whose own frontiers keep f closed (a parent cannot open what a part
    closes)."""
    inner = [c for c in d.chain(d.owner_of(f) or "") if c != name and d.is_within(c, name)]
    return next((c for c in inner if not d.isos[c].reachable(f)), None)


def covers(frontier: str, folder: str) -> bool:
    """A folder lies at or below a frontier ("." covers every folder)."""
    return frontier == "." or folder == frontier or folder.startswith(frontier + "/")


def _closed_by_part(d: Decl, iso: Iso, frontier: str, inside: list):
    """(file, part) for a file at an accepted frontier that one of the isolation's parts keeps closed, else None."""
    at = [f for f in inside if iso.folder_in(f) == frontier]
    return next(((f, part) for f in at if (part := _hiding_part(d, iso.name, f))), None)


def _check_frontiers(d: Decl, iso: Iso, files: list):
    """Each frontier names a folder holding the isolation's files, and none opens a folder one of its parts closes."""
    mine = [f for f in files if d.is_within(d.owner_of(f) or "", iso.name)]
    for frontier, status in sorted(iso.frontiers.items()):
        inside = [f for f in mine if covers(frontier, iso.folder_in(f) or "")]
        d.warnings += [] if inside else [f"isolation `{iso.name}`: frontier `{frontier}` holds none of its files"]
        d.warnings += _closed_warning(d, iso, frontier, inside) if status == "accepted" else []


def _closed_warning(d: Decl, iso: Iso, frontier: str, inside: list) -> list:
    closed = _closed_by_part(d, iso, frontier, inside)
    return [f"isolation `{iso.name}` opens `{frontier}`, but its part `{closed[1]}` keeps {closed[0]} closed"] if closed else []


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
