"""Leaf: the ABAP taint walk for `aix code vulnerabilities --taint` (benchmark section 26). Statement by statement
over the units of abapstyle: a value from a source (a `PARAMETERS` or `SELECT-OPTIONS` field of the program,
`sy-ucomm`, the IMPORTING parameters of a remote-enabled function module, a request field read through
`get_form_field`/`get_header_field`/`get_cdata`, abapGit's `ii_event->form_data( )`/`query( )`/`mv_action`) flows
through `=`, `MOVE`, `&&`, a template `|{ v }|`, CONCATENATE, SPLIT, a structure field, and into a called method,
form or function module through the argument it is bound to (the resolution of abapcalls, two calls deep, across
files). A sanitiser (`cl_abap_dyn_prg=>check_*`, `escape( val = ... )`, `cl_http_utility=>escape_url`) or an
allowlist (`CASE v`, `IF v IN`) ends the flow. A sink reached with a tainted value is a finding: a dynamic Open SQL
token, GENERATE SUBROUTINE POOL, INSERT REPORT, `CALL 'SYSTEM'`, `cl_gui_frontend_services=>execute`, `SUBMIT (v)`,
`CALL FUNCTION v`, `CALL TRANSACTION v`, OPEN DATASET, gui_upload/gui_download, and HTML written through
`html->add( )` without `escape( )`. Evidence to review, not proof."""
import re
from pathlib import Path

import abapcalls
from abapstyle import UNITS
from codefiles import ROOT, rel
from securityrules import ADVICE

SOURCE_READS = re.compile(r"->(?:get_form_fields?|get_header_field|get_cdata|get_form_data|form_data|query)\s*\(|->mv_action\b|\bsy-ucomm\b", re.I)
DECLARED_SOURCE = re.compile(r"^(?:PARAMETERS?|SELECT-OPTIONS)\s+(\w+)", re.I)
SANITISER = re.compile(r"\bcl_abap_dyn_prg=>\w+\s*\(|\bescape\s*\(|\bcl_http_utility=>escape_url\s*\(|\bcl_abap_syst=>\w+\(", re.I)
ALLOWLIST = re.compile(r"^(?:CASE|CHECK|IF)\s+(\w+)(?:\s+IN\b|\s*\.|$)", re.I)
ASSIGN = re.compile(r"^(?:DATA\()?([\w\-<>]+)\)?\s*(?:\?=|=)\s*(.+)$", re.I)
CONCATENATE = re.compile(r"^CONCATENATE\s+(.+?)\s+INTO\s+([\w\-]+)", re.I)
SPLIT = re.compile(r"^SPLIT\s+([\w\-]+)\s+AT\s+.+?\s+INTO\s+(.+)$", re.I)
MOVE = re.compile(r"^MOVE\s+([\w\-]+)\s+TO\s+([\w\-]+)", re.I)
NAMED_ARGS = re.compile(r"(\w+)\s*=\s*([^\s=()]+(?:\([^()]*\))?)")
SINKS = [  # (regex over the statement; group 1 is the dangerous expression), VUL row, CWE, kind
    (re.compile(r"\b(?:FROM|WHERE|SET|INTO|DELETE|INSERT|MODIFY|UPDATE)\s+\(([\w<>=\-]+)\)", re.I), "VUL-INJ-001", "CWE-89", "dynamic SQL"),
    (re.compile(r"^GENERATE\s+SUBROUTINE\s+POOL\s+([\w\-]+)", re.I), "VUL-INJ-002", "CWE-94", "generated code"),
    (re.compile(r"^INSERT\s+REPORT\s+[\w\-]+\s+FROM\s+([\w\-]+)", re.I), "VUL-INJ-002", "CWE-94", "generated code"),
    (re.compile(r"\bCALL\s+'S'.*?\bFIELD\s+([\w\-]+)", re.I), "VUL-INJ-002", "CWE-78", "OS command"),   # the statement reader blanks the literal; the raw line must say SYSTEM
    (re.compile(r"cl_gui_frontend_services=>execute\s*\((.*)\)", re.I | re.S), "VUL-INJ-002", "CWE-78", "OS command"),
    (re.compile(r"^SUBMIT\s+\(([\w\-]+)\)", re.I), "VUL-INJ-002", "CWE-470", "program chosen at run time"),
    (re.compile(r"\bCALL\s+(?:FUNCTION|TRANSACTION)\s+\(?([a-z_][\w\-]*)\)?", re.I), "VUL-INJ-002", "CWE-470", "function or transaction chosen at run time"),
    (re.compile(r"^OPEN\s+DATASET\s+([\w\-]+)", re.I), "VUL-INJ-002", "CWE-22", "file path"),
    (re.compile(r"gui_(?:upload|download)\s*\((.*)\)", re.I | re.S), "VUL-INJ-002", "CWE-22", "file path"),
    (re.compile(r"\w*html\w*->add\s*\((.*)\)", re.I | re.S), "VUL-WEB-001", "CWE-79", "HTML output"),
]
HOPS = 2   # calls followed from a unit; a report's top-level code gets one more, the PERFORM into its form is free
SNIPPET = 60
NOT_ASSIGNMENTS = ("IF", "ELSEIF", "WHILE", "CHECK", "WHEN", "SELECT", "LOOP", "DELETE", "READ", "MODIFY", "UPDATE", "INSERT", "ASSERT")


def _names(expr: str) -> set:
    """The variable names an expression reads, structures by their base (`ls_row-name` reads `ls_row`)."""
    return {n.split("-")[0].lower() for n in re.findall(r"(?<![\w'])(?!\d)([A-Za-z_][\w\-]*)", expr)}


def _rfc_modules(folder: Path) -> set:
    """Function modules a `.fugr.xml` next to the code marks remote-enabled."""
    out = set()
    for xml in folder.glob("*.fugr.xml"):
        text = xml.read_text(encoding="utf-8", errors="replace")
        out |= {m.group(1).lower() for m in re.finditer(r"<FUNCNAME>(\w+)</FUNCNAME>(?:(?!</item>).)*?<REMOTE_CALL>R</REMOTE_CALL>", text, re.S)}
    return out


class _Project:
    """Every ABAP file, the call index of abapcalls, the units by node, the program-level sources per file."""
    def __init__(self, paths: list):
        self.files = abapcalls._files(paths)
        self.idx = abapcalls._Index(self.files)
        self.units = {fx.node(unit): (fx, unit) for fx in self.files for unit in fx.units}
        self.rfc = {name for fx in self.files for name in _rfc_modules(fx.f.parent)}

    def program_sources(self, fx) -> dict:
        """`PARAMETERS p_x` and `SELECT-OPTIONS s_x`: input fields of the whole program."""
        return {m.group(1).lower(): f"{m.group(1).lower()}: {w} (line {line})" for w, text, line in fx.stmts for m in [DECLARED_SOURCE.match(text)] if m}


class _Scope:
    """What a walk carries along: the calls it may still follow, the findings list, the callees on the way."""
    def __init__(self, hops: int, findings: list, stack: tuple):
        self.hops, self.findings, self.stack = hops, findings, stack

    def into(self, target: str):
        return _Scope(self.hops - 1, self.findings, self.stack + (target,))


class _Walk:
    """One unit (or a program's top-level code) with its tainted names; sinks hit and calls followed as it goes."""
    def __init__(self, project: _Project, fx, unit: tuple, tainted: dict, scope: _Scope):
        self.p, self.fx, self.unit, self.tainted, self.scope = project, fx, unit, dict(tainted), scope
        kind, name, cls, i, j = unit
        self.body = fx.stmts[i + 1:j] if kind in UNITS else _top_level(fx)
        self.cls, self.name = cls, name
        self.types = abapcalls._local_types(self.body, project.idx)
        self.owner = project.idx.classes.get(cls)

    def run(self):
        for word, text, line in self.body:
            listed = ALLOWLIST.match(text)
            if listed and listed.group(1).lower() in self.tainted:
                self.tainted.pop(listed.group(1).lower())   # checked against a list: trusted from here on
            self._sinks(text, line)
            self._propagate(word, text)
            if self.scope.hops > 0:
                self._follow(text, line)

    def taint_of(self, expr: str):
        """The source a value carries, or None: a sanitiser call around it cleans it, a request read taints it."""
        if SANITISER.search(expr):
            return None
        hit = next((self.tainted[n] for n in _names(expr) if n in self.tainted), None)
        if hit is None and SOURCE_READS.search(expr):
            return f"request field read in {self.name}"
        return hit

    def _propagate(self, word: str, text: str):
        for rx, targets_group, values_group in ((CONCATENATE, 2, 1), (SPLIT, 2, 1), (MOVE, 2, 1)):
            m = rx.match(text)
            if m:
                return self._mark(m.group(targets_group), self.taint_of(m.group(values_group)))
        m = ASSIGN.match(text)
        if m and word not in NOT_ASSIGNMENTS:
            self._mark(m.group(1), self.taint_of(m.group(2)))

    def _mark(self, targets: str, source):
        for t in re.findall(r"[\w\-<>]+", targets):
            base = t.split("-")[0].lower()
            if source:
                self.tainted[base] = source
            else:
                self.tainted.pop(base, None)   # overwritten with a clean value

    def _sinks(self, text: str, line: int):
        raw = self.fx.raw[line - 1].strip()
        for rx, vul, cwe, kind in SINKS:
            m = rx.search(text)
            if m and self.taint_of(m.group(1)) and (cwe != "CWE-78" or "SYSTEM" in raw.upper() or "EXECUTE" in raw.upper()):
                self.scope.findings.append((vul, cwe, f"input reaches {kind}", rel(self.fx.f), line, f"{raw[:SNIPPET]} <- {self.taint_of(m.group(1))}", ADVICE[cwe], None))

    def _follow(self, text: str, line: int):
        """A call with a tainted argument: walk the callee with that parameter tainted, one hop less."""
        for target, bound in _calls_with_args(text, self):
            if target in self.p.units and target not in self.scope.stack:
                fx, unit = self.p.units[target]
                params = {p: f"{p}: {src} via {self.name} (line {line})" for p, src in bound.items()}
                _Walk(self.p, fx, unit, params, self.scope.into(target)).run()


def _top_level(fx) -> list:
    """The statements of a file outside every unit: a report's events (START-OF-SELECTION) and declarations."""
    inside, out, i = set(), [], 0
    while i < len(fx.stmts):
        if fx.stmts[i][0] in UNITS:
            j = next((k for k in range(i + 1, len(fx.stmts)) if fx.stmts[k][0] == UNITS[fx.stmts[i][0]]), len(fx.stmts) - 1)
            inside.update(range(i, j + 1)); i = j
        i += 1
    return [st for k, st in enumerate(fx.stmts) if k not in inside]


def _bound_params(call_args: str, importing: list, walk: _Walk) -> dict:
    """parameter name -> source for the arguments that carry taint: `p = v` pairs, or one unnamed value to the first
    IMPORTING parameter."""
    bound = {}
    pairs = NAMED_ARGS.findall(call_args)
    for name, value in pairs:
        src = walk.taint_of(value)
        if src:
            bound[name.lower()] = src
    if not pairs and importing and walk.taint_of(call_args):
        bound[importing[0]] = walk.taint_of(call_args)
    return bound


def _calls_with_args(text: str, walk: _Walk):
    """(target node, {param: source}) for every call in the statement whose target abapcalls resolves."""
    for m in abapcalls.RECEIVER.finditer(text):
        yield from _targets_for(walk, abapcalls._call_parts(m), _args_after(text, m.end()))
    for m in abapcalls.STATIC.finditer(text):
        if abapcalls._call_parts(m)[0].lower() in walk.p.idx.classes:
            yield from _targets_for(walk, abapcalls._call_parts(m), _args_after(text, m.end()), static=True)
    for m in abapcalls.CONSTRUCTED.finditer(text):
        yield from _targets_for(walk, (m.group(1), m.group(2), m.group(3).lower()), _args_after(text, m.end()), static=True)
    yield from _plain_calls(text, walk)


def _plain_calls(text: str, walk: _Walk):
    """A bare `fetch( iv_name = lv )` of this class, and `PERFORM f USING a b` of this program."""
    for m in abapcalls.BARE.finditer(re.sub(r"(?:->|=>)\s*(?:\w+~)?\w+\s*\(", " ", text)):
        if walk.cls and walk.p.idx.method(walk.cls, m.group(1).lower()):
            yield from _targets_for(walk, (walk.cls, None, m.group(1).lower()), _args_after(text, m.end()), static=True)
    for m in re.finditer(r"\bPERFORM\s+(\w+)(?:\s+USING\s+(.+?))?(?:\s+CHANGING|$)", text, re.I):
        target = walk.p.idx.forms.get((walk.fx.f.name.split(".")[0].lower(), m.group(1).lower()))
        if target and m.group(2):
            yield target, _form_binding(target, m.group(2), walk)


def _args_after(text: str, pos: int) -> str:
    """The text inside the parentheses that open at `pos - 1` (the match ends on the `(`), or the EXPORTING list."""
    depth, i = 1, pos
    while i < len(text) and depth:
        depth += (text[i] == "(") - (text[i] == ")"); i += 1
    inner = text[pos:i - 1] if depth == 0 else text[pos:]
    return inner.replace("EXPORTING", " ").replace("CHANGING", " ")


def _targets_for(walk: _Walk, call: tuple, args: str, static: bool = False):
    """(target node, {param: source}) for the units a call reaches: a static call on a class, `me->`, or a receiver
    whose declared type abapcalls knows."""
    recv, iface, method = call
    idx = walk.p.idx
    if static:
        targets = idx.targets(recv.lower(), iface, method)
    elif recv.lower() == "me":
        targets = idx.targets(walk.cls, iface, method)
    else:
        declared = abapcalls._receiver_type(recv.lower(), walk.types, walk.owner, walk.name, idx)
        targets = idx.targets(declared, iface, method) if declared else []
    for target in targets:
        fx, unit = walk.p.units[target]
        definition = fx.classes.get(unit[2], abapcalls._Class("")).methods.get(unit[1], {})
        bound = _bound_params(args, definition.get("importing", []), walk)
        if bound:
            yield target, bound


def _form_binding(target: str, using: str, walk: _Walk) -> dict:
    """FORM parameters by position: `PERFORM f USING a b` binds the form's USING names in order."""
    fx, unit = walk.p.units[target]
    head = fx.stmts[unit[3]][1]
    names = [n.lower() for n in re.findall(r"(?:USING|CHANGING|TABLES)\s+((?:\w+\s*)+?)(?=TYPE|LIKE|STRUCTURE|USING|CHANGING|TABLES|RAISING|$)", head, re.I) for n in n.split()]
    values = [v for v in using.split() if v.upper() not in ("CHANGING", "TABLES")]
    return {p: walk.taint_of(v) for p, v in zip(names, values) if walk.taint_of(v)}


def _initial(project: _Project, fx, unit: tuple) -> dict:
    """What is tainted when a unit starts on its own: the program's input fields, a remote function module's parameters."""
    kind, name, _cls, i, _j = unit
    tainted = project.program_sources(fx)
    if kind == "FUNCTION" and name in project.rfc:
        for p in re.findall(r'^\*"\s+(?:VALUE|REFERENCE)\((\w+)\)', "\n".join(fx.raw[fx.stmts[i][2]:]), re.I | re.M):
            tainted[p.lower()] = f"{p.lower()}: parameter of the remote-enabled function module {name}"
    return tainted


def taint(paths) -> list:
    """Findings for every ABAP unit under `paths`, and for each report's top-level code; deduplicated by (row, file, line)."""
    project = _Project([str(p) if Path(p).is_absolute() else str(ROOT / p) for p in paths])
    findings = []
    for fx in project.files:
        if fx.test:
            continue
        for unit in fx.units:
            _Walk(project, fx, unit, _initial(project, fx, unit), _Scope(HOPS, findings, (fx.node(unit),))).run()
        if ".prog." in fx.f.name:
            _Walk(project, fx, ("PROGRAM", fx.f.name.split(".")[0], None, 0, 0), project.program_sources(fx), _Scope(HOPS + 1, findings, ())).run()
    seen, out = set(), []
    for fx in findings:
        if (fx[0], fx[3], fx[4]) not in seen:
            seen.add((fx[0], fx[3], fx[4])); out.append(fx)
    return out
