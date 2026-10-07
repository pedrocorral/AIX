"""Leaf: ABAP call edges and dead methods for `--functions` (benchmark section 24). Nodes are the units of
abapstyle (`file:method`, `file:lcl.method`, `file:zif~method`). A call is an arc only when its target is known:
`me->m(` and a bare `m(` inside a class, `super->m(`, `zcl_x=>m(`, a receiver declared TYPE REF TO a project class
(in the unit, the method's parameters or the class attributes), `NEW zcl_x( )`, a factory's RETURNING type, a
receiver typed with a project interface (every implementation), `PERFORM f`, `CALL FUNCTION 'Z'`, `CALL METHOD` in
the same shapes. A receiver of SAP type is not a project call; an unknown receiver is unresolved, never guessed by
name. Dead: a private or protected method, a FORM or a function module that no call shape names anywhere
(tests and string literals included); constructors, setup/teardown, FOR TESTING, event handlers, redefinitions and
interface implementations are never candidates; a public method nobody calls carries the public note."""
import re
from pathlib import Path

from abapstyle import UNITS, _unit_name, statements
from codefiles import rel, source_files
from pyfuncgraph import RESOLUTION

RECEIVER = re.compile(r"(?<![\w\-])(<?\w+>?)->(?:(\w+)~)?(\w+)\s*\(|\bCALL\s+METHOD\s+(<?\w+>?)->(?:(\w+)~)?(\w+)\b", re.I)
STATIC = re.compile(r"(?<![\w\-])(\w+)=>(?:(\w+)~)?(\w+)\s*\(|\bCALL\s+METHOD\s+(\w+)=>(?:(\w+)~)?(\w+)\b", re.I)
CONSTRUCTED = re.compile(r"\bNEW\s+(\w+)\s*\([^()]*\)->(?:(\w+)~)?(\w+)\s*\(", re.I)   # `NEW zcl_x( )->m( )`: a call on a fresh instance of the class
BARE = re.compile(r"(?<![\w\->~=#])\s*(\w+)\s*\(", re.I)
PERFORM = re.compile(r"\bPERFORM\s+(\w+)(?:\s+IN\s+PROGRAM\s+(\w+))?", re.I)
CALL_FUNCTION = re.compile(r"\bCALL\s+FUNCTION\s+'(\w+)'", re.I)
TYPED = re.compile(r"\b(<?\w+>?)\s+TYPE\s+REF\s+TO\s+(\w+)", re.I)
INLINE_NEW = re.compile(r"\bDATA\((\w+)\)\s*=\s*(?:NEW|CAST)\s+(\w+)\s*\(", re.I)
INLINE_FACTORY = re.compile(r"\bDATA\((\w+)\)\s*=\s*(\w+)=>(\w+)\s*\(", re.I)
RETURNING = re.compile(r"\bRETURNING\s+VALUE\(\w+\)\s+TYPE\s+REF\s+TO\s+(\w+)", re.I)
NAME_LITERAL = re.compile(r"'(\w+)'")
IMPLICIT = {"constructor", "class_constructor", "setup", "teardown", "class_setup", "class_teardown"}
SECTIONS = re.compile(r"^(PUBLIC|PROTECTED|PRIVATE)\s+SECTION", re.I)


# ---- definitions --------------------------------------------------------------------------------------------------

class _Class:
    def __init__(self, name: str, interface: bool = False):
        self.name, self.interface, self.parent, self.interfaces = name, interface, "", []
        self.methods, self.attrs = {}, {}   # method -> {section, event, redefinition, testing, params, returning}; attr -> type

    def method(self, name: str, text: str, section: str):
        up = text.upper()
        self.methods[name] = dict(section=section, event=" FOR EVENT " in up, redefinition=" REDEFINITION" in up, testing=" FOR TESTING" in up,
                                  params={m.group(1).lower(): m.group(2).lower() for m in TYPED.finditer(text)},
                                  returning=(RETURNING.search(text).group(1).lower() if RETURNING.search(text) else ""),
                                  importing=_importing(text))


def _importing(definition: str) -> list:
    """The IMPORTING parameter names of a METHODS line, in order (`m( x )` with one unnamed argument binds the first)."""
    m = re.search(r"\bIMPORTING\b(.*?)(?=\b(?:EXPORTING|CHANGING|RETURNING|RAISING|EXCEPTIONS)\b|$)", definition, re.I | re.S)
    return [n.lower() for n in re.findall(r"(?:^|\s)(?:VALUE\()?(\w+)\)?\s+(?:TYPE|LIKE)\b", m.group(1), re.I)] if m else []


def _definition_statement(cls: _Class, word: str, text: str, section: str) -> str:
    """One statement of a class or interface definition; returns the section in force after it."""
    m = SECTIONS.match(text)
    if m:
        return m.group(1).upper()
    parts = text.split()
    if word in ("METHODS", "CLASS-METHODS") and len(parts) > 1:
        cls.method(parts[1].lower(), text, section)
    elif word in ("DATA", "CLASS-DATA") and TYPED.search(text):
        cls.attrs[TYPED.search(text).group(1).lower()] = TYPED.search(text).group(2).lower()
    elif word == "INTERFACES" and len(parts) > 1:
        cls.interfaces.append(parts[1].lower())
    return section


def definitions(stmts: list) -> dict:
    """class or interface name -> _Class, from the DEFINITION blocks of a file."""
    out, current, section = {}, None, "PUBLIC"
    for word, text, _line in stmts:
        head = re.match(r"(CLASS|INTERFACE)\s+(\w+)(?:\s+DEFINITION)?\b(?!\s+IMPLEMENTATION)", text, re.I)
        if head and word in ("CLASS", "INTERFACE") and "IMPLEMENTATION" not in text.upper():
            current = out.setdefault(head.group(2).lower(), _Class(head.group(2).lower(), word == "INTERFACE"))
            m = re.search(r"INHERITING\s+FROM\s+(\w+)", text, re.I)
            current.parent, section = (m.group(1).lower() if m else ""), "PUBLIC"
        elif word in ("ENDCLASS", "ENDINTERFACE"):
            current = None
        elif current is not None:
            section = _definition_statement(current, word, text, section)
    return out


# ---- files and units ----------------------------------------------------------------------------------------------

class _File:
    def __init__(self, f: Path):
        self.f, self.rel, self.test = f, rel(f), ".testclasses." in f.name
        self.raw = f.read_text(encoding="utf-8", errors="replace").splitlines()   # the names inside strings: CALL FUNCTION 'Z', 'METHOD_NAME'
        self.stmts = statements(self.raw)
        self.classes = definitions(self.stmts)
        self.units = list(_units(self.stmts))   # (kind, name, class, head index, end index)

    def node(self, unit: tuple) -> str:
        kind, name, cls, _i, _j = unit
        return f"{self.rel}:{_unit_name(kind, name, cls, self.f)}"


def _units(stmts: list):
    cls, i = None, 0
    while i < len(stmts):
        word, head, _line = stmts[i]
        if word == "CLASS" and re.match(r"CLASS\s+\S+\s+IMPLEMENTATION", head, re.I):
            cls = head.split()[1].lower()
        if word in UNITS:
            j = next((k for k in range(i + 1, len(stmts)) if stmts[k][0] == UNITS[word]), len(stmts) - 1)
            yield word, (head.split()[1].lower() if len(head.split()) > 1 else "?"), cls, i, j
            i = j
        i += 1


class _Index:
    """Everything a call may target: classes by name, implementations by interface, method nodes by (class, name),
    forms by (file, name), function modules by name."""
    def __init__(self, files: list):
        self.classes, self.impls, self.methods, self.forms, self.functions = {}, {}, {}, {}, {}
        for fx in files:
            for name, cls in fx.classes.items():
                self.classes[name] = cls
                for iface in cls.interfaces:
                    self.impls.setdefault(iface, []).append(name)
            for unit in fx.units:
                self._add(fx, unit)

    def _add(self, fx: _File, unit: tuple):
        kind, name, cls, _i, _j = unit
        node = fx.node(unit)
        if kind == "METHOD" and cls:
            self.methods[(cls, name)] = node
        elif kind == "FORM":
            self.forms[(fx.f.name.split(".")[0].lower(), name)] = node
        elif kind == "FUNCTION":
            self.functions[name] = node

    def method(self, cls: str, name: str, hops: int = 3) -> str:
        """The node of `cls.name`, walking INHERITING FROM up to `hops` parents."""
        while cls and hops >= 0:
            if (cls, name) in self.methods:
                return self.methods[(cls, name)]
            cls, hops = self.classes[cls].parent if cls in self.classes else "", hops - 1
        return ""

    def targets(self, type_name: str, iface: str, name: str) -> list:
        """Nodes a call on a receiver of `type_name` reaches: the class's method, or every implementation of the
        interface's method; [] when the type is no project class or interface."""
        cls = self.classes.get(type_name)
        if cls is None:
            return []
        if cls.interface:
            return [t for impl in self.impls.get(type_name, []) for t in [self.methods.get((impl, f"{type_name}~{name}"))] if t]
        full = f"{iface}~{name}" if iface else name
        return [t for t in [self.method(type_name, full)] if t]


# ---- calls ------------------------------------------------------------------------------------------------------

def _local_types(body: list, idx: _Index) -> dict:
    """Receiver name -> type declared in the unit: TYPE REF TO, NEW, CAST, a factory's RETURNING type."""
    types = {}
    for _w, text, _l in body:
        types.update({m.group(1).lower(): m.group(2).lower() for m in TYPED.finditer(text)})
        types.update({m.group(1).lower(): m.group(2).lower() for m in INLINE_NEW.finditer(text)})
        for m in INLINE_FACTORY.finditer(text):
            cls = idx.classes.get(m.group(2).lower())
            types[m.group(1).lower()] = cls.methods.get(m.group(3).lower(), {}).get("returning", "") if cls else ""
    return types


def _receiver_type(name: str, types: dict, cls: _Class, method: str, idx: _Index) -> str:
    """The declared type of a receiver: the unit's own declarations, the method's parameters, the class attributes
    (own and inherited); "" when unknown."""
    if name in types:
        return types[name]
    while cls is not None:
        hit = cls.methods.get(method, {}).get("params", {}).get(name) or cls.attrs.get(name)
        if hit:
            return hit
        cls = idx.classes.get(cls.parent) if cls.parent else None
    return ""


def _call_parts(m) -> tuple:
    """(receiver or class, interface or None, method) of a RECEIVER or STATIC match, whichever alternative matched."""
    g = m.groups()
    recv, iface, method = g[:3] if g[0] else g[3:6]
    return recv, iface, method.lower()


class _Unit:
    """One unit being read for its calls."""
    def __init__(self, fx: _File, unit: tuple, idx: _Index):
        self.fx, self.idx, (self.kind, self.name, self.cls, i, j) = fx, idx, unit
        self.node, self.body = fx.node(unit), fx.stmts[i + 1:j]
        self.types = _local_types(self.body, idx)
        self.owner = idx.classes.get(self.cls)

    def _record(self, targets: list, edges: set):
        RESOLUTION["seen"] += 1
        RESOLUTION["matched"] += bool(targets)
        edges.update((self.node, t) for t in targets if t != self.node)

    def _receiver(self, recv: str, iface: str, method: str, edges: set):
        recv = recv.lower()
        if recv == "me":
            return self._record(self.idx.targets(self.cls, iface, method), edges)
        if recv == "super":
            return self._record([t for t in [self.idx.method(self.owner.parent if self.owner else "", method)] if t], edges)
        type_name = _receiver_type(recv, self.types, self.owner, self.name, self.idx)
        if type_name and type_name not in self.idx.classes:
            return   # a SAP class or interface, a dictionary type: not a project call
        self._record(self.idx.targets(type_name, iface, method) if type_name else [], edges)

    def _static(self, cls: str, iface: str, method: str, edges: set):
        if cls.lower() in self.idx.classes:
            self._record(self.idx.targets(cls.lower(), iface, method), edges)

    def _bare(self, name: str, edges: set):
        """A bare `m( )` is a call only when the class or a parent defines `m`; builtins and constructors never match."""
        target = self.idx.method(self.cls, name.lower()) if self.cls else ""
        if target:
            self._record([target], edges)

    def _statement(self, text: str, edges: set):
        for m in RECEIVER.finditer(text):
            self._receiver(*_call_parts(m), edges)
        for m in STATIC.finditer(text):
            self._static(*_call_parts(m), edges)
        for m in CONSTRUCTED.finditer(text):
            self._static(m.group(1), m.group(2), m.group(3).lower(), edges)
        for m in BARE.finditer(re.sub(r"(?:->|=>)\s*(?:\w+~)?\w+\s*\(", " ", text)):
            self._bare(m.group(1), edges)
        for m in PERFORM.finditer(text):
            program = (m.group(2) or self.fx.f.name.split(".")[0]).lower()
            self._record([t for t in [self.idx.forms.get((program, m.group(1).lower()))] if t], edges)

    def edges(self) -> set:
        edges = set()
        for _w, text, _l in self.body:
            self._statement(text, edges)
        raw = "\n".join(self.fx.raw[self.body[0][2] - 1:self.body[-1][2]]) if self.body else ""   # the function name sits in a string
        for m in CALL_FUNCTION.finditer(raw):
            self._record([t for t in [self.idx.functions.get(m.group(1).lower())] if t], edges)
        return edges


def _files(paths: list) -> list:
    return [_File(f) for f in source_files(paths) if f.suffix == ".abap"]


def function_graph(paths: list) -> tuple:
    """(nodes, edges) over the ABAP units under `paths`; RESOLUTION is added to, not reset."""
    files = _files(paths)
    idx = _Index(files)
    nodes, edges = set(), set()
    for fx in files:
        for unit in fx.units:
            nodes.add(fx.node(unit))
            edges |= _Unit(fx, unit, idx).edges()
    return nodes, edges


# ---- dead -------------------------------------------------------------------------------------------------------

def _called_names(text: str) -> set:
    """The method and form names one statement calls, by every shape."""
    names = {_call_parts(m)[2] for m in RECEIVER.finditer(text)} | {_call_parts(m)[2] for m in STATIC.finditer(text)}
    names |= {m.group(3).lower() for m in CONSTRUCTED.finditer(text)}
    return names | {m.group(1).lower() for m in BARE.finditer(text)} | {m.group(1).lower() for m in PERFORM.finditer(text)}


def _referenced(files: list) -> set:
    """Every method, form and function-module name any call shape or string literal names, in every file."""
    names = set()
    for fx in files:
        for _w, text, _l in fx.stmts:
            names |= _called_names(text)
        raw = "\n".join(fx.raw)
        names |= {m.group(1).lower() for m in CALL_FUNCTION.finditer(raw)} | {m.group(1).lower() for m in NAME_LITERAL.finditer(raw)}
    return names


def _never_a_candidate(name: str, definition: dict) -> bool:
    """Constructors, setup/teardown, interface implementations, event handlers, redefinitions, test methods."""
    return name in IMPLICIT or "~" in name or bool(definition.get("event") or definition.get("redefinition") or definition.get("testing"))


def _candidate(fx: _File, unit: tuple, referenced: set):
    """(node, line, public) when the unit is dead by the rules, else None."""
    kind, name, cls, head, _end = unit
    definition = fx.classes.get(cls, _Class(cls or "")).methods.get(name, {}) if kind == "METHOD" else {}
    if fx.test or name in referenced or _never_a_candidate(name, definition):
        return None
    public = kind == "FUNCTION" or (kind == "METHOD" and definition.get("section", "PUBLIC") == "PUBLIC")
    return fx.node(unit), fx.stmts[head][2], public


def dead_functions(paths: list) -> list:
    """[(file:unit, line, public)] for the ABAP units nothing names (see the module docstring)."""
    files = _files(paths)
    referenced = _referenced(files)
    return sorted(c for fx in files for c in [_candidate(fx, unit, referenced) for unit in fx.units] if c)
