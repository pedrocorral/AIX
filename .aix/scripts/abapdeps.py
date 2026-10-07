"""Leaf: ABAP objects as graph nodes and what one file names of another (benchmark section 23). An object is one
abapGit name before the first dot: a class with its `.locals_def`, `.locals_imp` and `.macros` files folded in, an
interface, a program or include, a function group with its function-module and include files folded in; a
`.testclasses.abap` file stays a node of its own, a test. A reference is `zcl_x=>`, `TYPE REF TO zcl_x`, `NEW zcl_x(`,
`CREATE OBJECT ... TYPE zcl_x`, `INHERITING FROM`, `INTERFACES`, `TYPE zif_x=>ty`, `RAISE EXCEPTION TYPE zcx_x`,
`CATCH zcx_x`, `FRIENDS zcl_x`, `CALL FUNCTION 'Z_X'`, `INCLUDE zinc`, `SUBMIT zprog`, `PERFORM ... IN PROGRAM zprog`. A name that is
no object of the project (SAP standard `cl_*`, a dictionary type) is not an edge, never guessed."""
import re
from pathlib import Path

from abapstyle import statements, strip_line

NAME = r"([A-Za-z_/][\w/]*)"
REFERENCES = [re.compile(rx, re.I | re.M) for rx in (
    rf"\b{NAME}=>", rf"\bTYPE\s+REF\s+TO\s+{NAME}", rf"\bNEW\s+{NAME}\s*\(", rf"\bCREATE\s+OBJECT\s+\S+\s+TYPE\s+{NAME}",
    rf"\bINHERITING\s+FROM\s+{NAME}", rf"^\s*INTERFACES\s+{NAME}", rf"\bRAISE\s+EXCEPTION\s+TYPE\s+{NAME}", rf"^\s*INCLUDE\s+{NAME}",
    rf"\bSUBMIT\s+{NAME}", rf"\bIN\s+PROGRAM\s+{NAME}", rf"\bCATCH\s+((?:[A-Za-z_/][\w/]*\s+)+?)(?:INTO\b|$)",
    r"\bFRIENDS\s+((?:[A-Za-z_/][\w/]*\s*)+?)(?=\.|$)")]   # `GLOBAL FRIENDS zcl_injector`: the class names who may reach inside it
CALL_FUNCTION = re.compile(r"\bCALL\s+FUNCTION\s+'([^']+)'", re.I)
TEST_PART = ".testclasses."
FOLDED_PARTS = ("locals_def", "locals_imp", "macros")
ENTRY_INTERFACES = re.compile(r"^\s*INTERFACES\s+(?:if_oo_adt_classrun|if_apack_manifest)\b", re.I | re.M)
PROGRAM = re.compile(r"^\s*(?:REPORT|PROGRAM)\b", re.I | re.M)


def object_key(f: Path) -> str:
    """`zcl_x.clas` of `zcl_x.clas.locals_imp.abap`: the object a file belongs to, in lower case."""
    parts = f.name.lower().split(".")
    return ".".join(parts[:2]) if len(parts) >= 3 else parts[0]


def _main_file(members: list) -> Path:
    """The file that stands for an object: `name.kind.abap` when it exists, else the first by name."""
    plain = [m for m in members if len(m.name.split(".")) == 3]
    return plain[0] if plain else sorted(members, key=lambda m: m.name)[0]


def _group_part(m: Path) -> str:
    """`z_calc` of `zfg.fugr.z_calc.abap`: a function module or include of a function group, else ""."""
    parts = m.name.lower().split(".")[1:-1]   # kind and the part, without the object name and the suffix
    return parts[1] if len(parts) == 2 and parts[0] == "fugr" and parts[1] not in FOLDED_PARTS else ""


def _members(files) -> dict:
    """(folder, object key) -> its part files, test classes left out; the same name in two folders is two objects."""
    members = {}
    for f in files:
        if f.suffix == ".abap" and TEST_PART not in f.name:
            members.setdefault((f.parent, object_key(f)), []).append(f)
    return members


def index(files) -> dict:
    """{'node': file -> the file that stands for its object, 'objects': object name -> the files standing for it (one,
    or several when the same name sits in two folders)} over the ABAP files; a function module (`zfg.fugr.z_calc.abap`)
    is reachable by its own name too; a test class is its own node."""
    node, objects = {}, {}
    for (_folder, key), group in _members(files).items():
        main = _main_file(group)
        objects.setdefault(key.split(".")[0], []).append(main)
        for m in group:
            node[m] = main
            if _group_part(m):
                objects.setdefault(_group_part(m), []).append(main)
    node.update({f: f for f in files if f.suffix == ".abap" and TEST_PART in f.name})
    pools = {key.split(".")[0] for _folder, key in _members(files) if key.endswith(".type")}
    return {"node": node, "objects": objects, "pools": pools}


def node_of(f: Path, idx: dict) -> Path:
    return idx["node"].get(f, f)


def _code(text: str) -> tuple:
    """(code without comments and strings, the function modules called): the CALL FUNCTION name lives in a string."""
    code, state, called = [], None, set()
    for raw in text.splitlines():
        called |= {m.group(1).lower() for m in CALL_FUNCTION.finditer(raw)}
        line, state = strip_line(raw, state)
        code.append(line)
    return "\n".join(code), called


def _names(text: str, pools: set) -> set:
    """Every object name the code names, in lower case: the reference shapes, the function modules called, and a
    type pool (`seoc.type.abap`) through `TYPE-POOLS seoc` or any `seoc_...` name."""
    joined, names = _code(text)
    for rx in REFERENCES:
        for m in rx.finditer(joined):
            names |= {n.lower() for n in m.group(1).split()}
    if pools:
        names |= {m.group(1).lower() for m in re.finditer(r"\b(" + "|".join(map(re.escape, sorted(pools))) + r")_\w+", joined, re.I)}
        names |= {m.group(1).lower() for m in re.finditer(r"\bTYPE-POOLS\s+(\w+)", joined, re.I)}
    return names


def module_edges(f: Path, idx: dict) -> list:
    """The object files this file names, its own object left out."""
    own = node_of(f, idx)
    text = f.read_text(encoding="utf-8", errors="replace")
    return sorted({t for n in _names(text, idx["pools"]) for t in idx["objects"].get(n, []) if t != own}, key=str)


def is_entry(f: Path) -> bool:
    """A program (REPORT or PROGRAM statement; an include has none), a function group (called from outside), a class
    that implements `if_oo_adt_classrun` or `if_apack_manifest`. Tests are entries by the shared test rule."""
    parts = f.name.lower().split(".")
    if len(parts) >= 3 and parts[1] == "fugr":
        return True
    text = f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""
    if len(parts) >= 3 and parts[1] == "prog":
        return bool(PROGRAM.search(text))
    return bool(ENTRY_INTERFACES.search(text))


NAME_LITERAL = re.compile(r"'([A-Z][A-Z0-9_/]*)'")
BUILT_NAME = re.compile(r"'([A-Z][A-Z0-9_/]*_)'\s*&&|\bCONCATENATE\s+'([A-Z][A-Z0-9_/]*_)'", re.I)


def _literals(nodes: list, root: Path) -> tuple:
    """(object names written as a string, name prefixes built with `&&` or CONCATENATE) over the ABAP files."""
    names, prefixes = set(), set()
    for n in [n for n in nodes if n.endswith(".abap")]:
        for part in (root / n).parent.glob(Path(n).name.split(".")[0] + ".*.abap"):   # the object's own file and its folded parts
            text = part.read_text(encoding="utf-8", errors="replace")
            names |= {m.group(1).upper() for m in NAME_LITERAL.finditer(text)}
            prefixes |= {(m.group(1) or m.group(2)).upper() for m in BUILT_NAME.finditer(text)}
    return names, prefixes


def live_by_string(nodes: list, root: Path) -> set:
    """ABAP objects a string in code names: `ls_method-class = 'ZCL_X'` equals an object, `'ZCL_PLUGIN_' && lv_kind`
    or `CONCATENATE 'ZCL_PLUGIN_' lv_kind INTO lv_class` prefixes a family created by name (`CREATE OBJECT ... TYPE
    (lv_class)`). The report lists them as live by convention, the same rule as a folder named by a string."""
    names, prefixes = _literals(nodes, root)
    return {n for n in nodes if n.endswith(".abap") and _named(Path(n).name.split(".")[0].upper(), names, prefixes)}


def _named(name: str, names: set, prefixes: set) -> bool:
    return name in names or any(name.startswith(p) for p in prefixes)


# ---- clones -----------------------------------------------------------------------------------------------------

KEYWORDS = frozenset("""IF ELSEIF ELSE ENDIF CASE WHEN OTHERS ENDCASE LOOP AT ENDLOOP DO ENDDO WHILE ENDWHILE TRY CATCH CLEANUP ENDTRY
CHECK EXIT CONTINUE RETURN DATA TYPES CONSTANTS STATICS FIELD-SYMBOLS TYPE LIKE REF TO TABLE OF STANDARD SORTED HASHED LINE
WITH KEY DEFAULT UNIQUE NON-UNIQUE VALUE NEW CREATE OBJECT ASSIGN COMPONENT STRUCTURE UNASSIGN CLEAR FREE REFRESH APPEND INSERT
INTO MODIFY DELETE READ INDEX FROM WHERE SELECT SINGLE ENDSELECT UP ROWS ORDER BY GROUP INNER LEFT OUTER JOIN ON FOR ALL ENTRIES IN
AND OR NOT EQ NE LT GT LE GE CO CN CA NA CS NS CP NP IS INITIAL BOUND ASSIGNED SUPPLIED REQUESTED BETWEEN CALL FUNCTION METHOD
EXPORTING IMPORTING CHANGING RETURNING RECEIVING EXCEPTIONS RAISING RAISE EXCEPTION MESSAGE WRITE FORMAT SKIP ULINE CONCATENATE
SPLIT REPLACE FIND TRANSLATE CONDENSE SHIFT SEPARATED COND SWITCH REDUCE CORRESPONDING CONV CAST VALUE FILTER FIELD ME SUPER
METHODS CLASS-METHODS INTERFACES ALIASES EVENTS PUBLIC PROTECTED PRIVATE SECTION ENDMETHOD FORM ENDFORM PERFORM USING TABLES
SORT DESCENDING ASCENDING COLLECT SUM MOVE MOVE-CORRESPONDING ADD SUBTRACT MULTIPLY DIVIDE TIMES SY-SUBRC ABAP_TRUE ABAP_FALSE
LINES STRLEN XSTRLEN NUMOFCHAR TRUE FALSE SPACE COMMIT ROLLBACK WORK AUTHORITY-CHECK ID FIELD OPTIONAL PREFERRED PARAMETER
BEGIN END OCCURS LENGTH DECIMALS LANGUAGE EXPORT IMPORT MEMORY DATABASE SET GET PARAMETER WAIT UNTIL SECONDS""".split())
TOKEN = re.compile(r"'[^']*'|`[^`]*`|\|[^|]*\||\d+|[A-Za-z_/][\w/\-]*(?:=>|->)?|[^\sA-Za-z_0-9]")


def _token(tok: str) -> str:
    """One structure token: a keyword in upper case, else ID (with its `=>`/`->`), STR, NUM or the punctuation itself."""
    if tok[0] in "'`|":
        return "STR"
    if tok[0].isdigit():
        return "NUM"
    if not (tok[0].isalpha() or tok[0] in "_/"):
        return tok
    up = tok.upper(); base = up.rstrip(">-=")
    return up if base in KEYWORDS else "ID" + up[len(base):]


def normalise(stmts: list) -> list:
    """Structure tokens of a unit's statements: keywords kept in upper case, identifiers -> ID, strings -> STR,
    numbers -> NUM, punctuation kept, a `.` between statements."""
    out = []
    for _word, text, _line in stmts:
        out += [_token(tok) for tok in TOKEN.findall(text)] + ["."]
    return out


def clone_units(f: Path, text: str, rel: str, min_lines: int) -> list:
    """(node name, file, line, n_lines, token sequence) for every unit at least `min_lines` long."""
    from abapstyle import UNITS
    stmts, out, i = statements(text.splitlines()), [], 0
    while i < len(stmts):
        word, head, line = stmts[i]
        if word in UNITS:
            j = next((k for k in range(i + 1, len(stmts)) if stmts[k][0] == UNITS[word]), len(stmts) - 1)
            n_lines = stmts[j][2] - line + 1
            if n_lines >= min_lines:
                name = head.split()[1].lower() if len(head.split()) > 1 else "?"
                out.append((f"{rel}:{name}", rel, line, n_lines, normalise(stmts[i + 1:j])))
            i = j
        i += 1
    return out
