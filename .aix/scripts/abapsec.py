"""Leaf: the ABAP security rules that need the unit around the line (benchmark section 25). Dynamic Open SQL, a
table or a clause held in a variable (`FROM (lv_table)`, `WHERE (lv_where)`, `INSERT (lv) FROM TABLE`, `DELETE (lv)`,
`MODIFY (lv)`, `SET (lv)`, `INTO (lv)`; a class constant `(zcl_x=>c_tab)` or a field `(<ls>-name)` too), unless the
variable holds a literal assigned in the same unit; `EXEC SQL`; a `CALL TRANSACTION` with no `WITH AUTHORITY-CHECK`
and no `AUTHORITY-CHECK` in the unit; an `AUTHORITY-CHECK` whose next statement does not read `sy-subrc`. The
line rules (code generation, OS command, a program or function named at run time, cross-client access, a file path
from a variable, plain HTTP) sit in securityrules.RULES under the language `abap`."""
import re
from pathlib import Path

from abapstyle import UNITS, statements
from codefiles import rel

DYNAMIC_SQL = re.compile(r"\b(?:FROM|WHERE|SET|INTO|UP TO|ORDER BY|GROUP BY|FIELDS|DELETE|INSERT|MODIFY|UPDATE)\s+\(([\w<>=\-]+)\)", re.I)   # `INSERT (iv_name) FROM TABLE` too
SQL_WORDS = ("SELECT", "UPDATE", "DELETE", "MODIFY", "INSERT", "OPEN", "WITH")
LITERAL_ASSIGN = re.compile(r"^\s*(?:CONSTANTS\s+)?(\w+)\b[^=]*?(?:=|VALUE)\s*'[^']*'\s*$", re.I)
AUTHORITY = "AUTHORITY-CHECK"
SQL_ROW = ("VUL-INJ-001", "CWE-89", "SQL built at run time: a table or a clause held in a variable",
           "a static table name and a WHERE with host variables (`WHERE f = @lv`); if the name must vary, an allowlist of table names, never a value from input")
EXEC_ROW = ("VUL-INJ-001", "CWE-89", "native SQL (EXEC SQL)", "Open SQL with host variables; native SQL takes the statement as text, every value inside it is injectable")
TRANSACTION_ROW = ("VUL-AUTHZ-001", "CWE-862", "CALL TRANSACTION without an authority check",
                   "`CALL TRANSACTION ... WITH AUTHORITY-CHECK`, or an AUTHORITY-CHECK OBJECT 'S_TCODE' before it")
SUBRC_ROW = ("VUL-AUTHZ-001", "CWE-285", "AUTHORITY-CHECK whose result is not read",
             "the statement after AUTHORITY-CHECK reads sy-subrc (`IF sy-subrc <> 0. ... ENDIF.`); the check alone grants nothing")
SNIPPET = 110


def _units_of(stmts: list):
    """(head index, end index) of every unit, and (0, len) for the code outside units."""
    i, inside = 0, []
    while i < len(stmts):
        if stmts[i][0] in UNITS:
            j = next((k for k in range(i + 1, len(stmts)) if stmts[k][0] == UNITS[stmts[i][0]]), len(stmts) - 1)
            inside.append((i, j)); i = j
        i += 1
    return inside or [(0, len(stmts) - 1)]


def _literal_names(body: list) -> set:
    """Variables the unit assigns a literal to (`lv_table = 'ZTAB'.`, `CONSTANTS lc_tab TYPE string VALUE 'ZTAB'`)."""
    return {m.group(1).lower() for _w, text, _l in body for m in [LITERAL_ASSIGN.match(text)] if m}


def _sql_findings(f: Path, raw: list, body: list) -> list:
    out, literal = [], _literal_names(body)
    for word, text, line in body:
        if word == "EXEC" and "SQL" in text.upper():
            out.append((*EXEC_ROW[:3], rel(f), line, raw[line - 1].strip()[:SNIPPET], EXEC_ROW[3], None))
        elif word in SQL_WORDS:
            names = [m.group(1).lower() for m in DYNAMIC_SQL.finditer(text)]
            if names and not all(n in literal for n in names):
                out.append((*SQL_ROW[:3], rel(f), line, raw[line - 1].strip()[:SNIPPET], SQL_ROW[3], None))
    return out


def _authority_findings(f: Path, raw: list, body: list) -> list:
    out = []
    checked = any(w == AUTHORITY for w, _t, _l in body)
    for k, (word, text, line) in enumerate(body):
        if word == "CALL" and re.match(r"CALL\s+TRANSACTION\b", text, re.I) and not checked and "AUTHORITY-CHECK" not in text.upper():
            out.append((*TRANSACTION_ROW[:3], rel(f), line, raw[line - 1].strip()[:SNIPPET], TRANSACTION_ROW[3], None))
        if word == AUTHORITY and (k + 1 >= len(body) or "SY-SUBRC" not in body[k + 1][1].upper()):
            out.append((*SUBRC_ROW[:3], rel(f), line, raw[line - 1].strip()[:SNIPPET], SUBRC_ROW[3], None))
    return out


def findings(f: Path, raw: list) -> list:
    """The unit-level ABAP findings of one file, in the register shape."""
    stmts = statements(raw)
    out = []
    for i, j in _units_of(stmts):
        body = stmts[i + 1:j] if stmts[i][0] in UNITS else stmts[i:j + 1]
        out += _sql_findings(f, raw, body) + _authority_findings(f, raw, body)
    return out
