"""Leaf: the DEFINITION part of ABAP classes and interfaces, read from statements (abapstyle.statements): each
method's section, flags (FOR EVENT, REDEFINITION, FOR TESTING), the parameters declared TYPE REF TO, the RETURNING type,
the IMPORTING names in order; each attribute declared TYPE REF TO; the interfaces implemented; the parent class.
Shared by abapcalls (call resolution), abaphygiene (parameters, pass-through) and abapstyle, below all three."""
import re

TYPED = re.compile(r"\b(<?\w+>?)\s+TYPE\s+REF\s+TO\s+(\w+)", re.I)
RETURNING = re.compile(r"\bRETURNING\s+VALUE\(\w+\)\s+TYPE\s+REF\s+TO\s+(\w+)", re.I)
SECTIONS = re.compile(r"^(PUBLIC|PROTECTED|PRIVATE)\s+SECTION", re.I)


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


