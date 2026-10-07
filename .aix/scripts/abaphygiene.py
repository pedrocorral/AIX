"""Leaf: the hygiene findings of one ABAP unit for `aix code style` (benchmark section 27, abaplint's
`unused_variables` as the reference). A swallowed exception: a CATCH whose block holds no statement and no comment.
An unused variable: a DATA, STATICS, FIELD-SYMBOLS or CONSTANTS of the unit, or an inline DATA( ), that no statement
but its declaration names (abaplint's definition; the components of a BEGIN OF ... END OF belong to their structure). An unused parameter: an IMPORTING parameter of a private or
protected method never named in its body; public methods, interface implementations, redefinitions and event handlers
keep theirs by contract. A pass-through: a method whose only statement forwards its parameters, unchanged and all of
them, to one call."""
import re

DECL = re.compile(r"^(?:DATA|STATICS|FIELD-SYMBOLS|CONSTANTS)\s+<?(\w+)>?", re.I)
INLINE = re.compile(r"\b(?:DATA|FIELD-SYMBOL)\((<?\w+>?)\)", re.I)
STRUCTURE = re.compile(r"^(?:DATA|STATICS|CONSTANTS|TYPES)\s+(BEGIN|END)\s+OF\b", re.I)
TOKEN = re.compile(r"<\w+>|[A-Za-z_]\w*|\?=|\+=|-=|=|\S")
PASS_CALL = re.compile(r"^(?:\w+\s*=\s*)?([\w=>\-]+(?:->|=>)?\w*)\s*\((.*)\)\s*$", re.S)


# ---- never referenced ---------------------------------------------------------------------------------------------

def _names_in(text: str) -> set:
    """Every variable-looking token of a statement, structures by their base (`ls_row-a` names `ls_row`)."""
    return {tok.strip("<>").split("-")[0].lower() for tok in TOKEN.findall(text) if re.match(r"<?[A-Za-z_]\w*>?$", tok)}


def _declared_in(text: str) -> list:
    """The variable names one statement declares: a DATA/STATICS/FIELD-SYMBOLS/CONSTANTS head, inline DATA( )s."""
    m = DECL.match(text)
    return ([m.group(1).strip("<>").lower()] if m else []) + [x.group(1).strip("<>").lower() for x in INLINE.finditer(text)]


def _structure_depth(text: str, depth: int) -> int:
    m = STRUCTURE.match(text)
    return depth + (1 if m and m.group(1).upper() == "BEGIN" else -1 if m else 0)


def unused_variables(body: list, unit_name: str) -> list:
    """(line, message) for every variable of the unit that no statement but its declaration names (abaplint's
    `unused_variables`, the definition section 27 is measured against)."""
    declared, referenced, depth = {}, set(), 0
    for _w, text, line in body:
        new_depth = _structure_depth(text, depth)
        if new_depth != depth or depth:
            depth = new_depth; continue   # a structure's components are not variables
        names = _declared_in(text)
        for name in names:
            declared.setdefault(name, line)
        referenced |= _names_in(text) - set(names)
    return [(line, f"leftover: variable `{name}` in `{unit_name}` is declared and never used") for name, line in declared.items() if name not in referenced]


# ---- the other three ---------------------------------------------------------------------------------------------

def swallowed(body: list, raw: list) -> list:
    """A CATCH followed by ENDTRY, CATCH or CLEANUP with nothing but blank lines in between; a comment is intent."""
    out = []
    for k, (word, _text, line) in enumerate(body[:-1]):
        if word != "CATCH" or body[k + 1][0] not in ("ENDTRY", "CATCH", "CLEANUP"):
            continue
        between = raw[line - 1:body[k + 1][2] - 1]
        if not any('"' in l or l.startswith("*") for l in between):
            out.append((line, "swallowed: this CATCH does nothing and says nothing"))
    return out


def unused_parameters(body: list, name: str, definition: dict, head_line: int) -> list:
    """IMPORTING parameters of a private or protected method that its body never names."""
    if "~" in name or definition.get("section", "PUBLIC") == "PUBLIC" or definition.get("redefinition") or definition.get("event"):
        return []
    text = " ".join(t for _w, t, _l in body)
    return [(head_line, f"leftover: parameter `{p}` of `{name}` is never read") for p in definition.get("importing", [])
            if not re.search(rf"(?<![\w\-]){re.escape(p)}(?![\w])", text, re.I)]


def _forwarding_call(statement: str):
    """The callee of a single call statement, unless it constructs, calls the parent, or names a class."""
    m = PASS_CALL.match(statement.strip())
    if not m or m.group(1).upper().startswith(("NEW ", "SUPER->")):
        return None
    last = m.group(1).split("=>")[-1].split("->")[-1]
    return None if last[:1].isupper() else m


def passthrough(body: list, name: str, definition: dict):
    """The callee when the body is one call forwarding every IMPORTING parameter unchanged, else None."""
    importing = definition.get("importing", [])
    if len(body) != 1 or not importing or "~" in name or definition.get("redefinition"):
        return None
    m = _forwarding_call(body[0][1])
    if m is None:
        return None
    values = [v.lower() for v in re.findall(r"=\s*(\w+)", m.group(2))] or [v.lower() for v in m.group(2).split()]
    return m.group(1) if sorted(values) == sorted(importing) else None


def findings(body: list, raw: list, unit: tuple, definition: dict, test: bool) -> tuple:
    """(hygiene list, pass-through callee) of one unit; a test may catch to assert nothing more happens."""
    kind, name, head_line = unit
    out = unused_variables(body, name) + ([] if test else swallowed(body, raw))
    if kind == "METHOD":
        out += unused_parameters(body, name, definition, head_line)
    return sorted(out), (passthrough(body, name, definition) if kind == "METHOD" else None)
