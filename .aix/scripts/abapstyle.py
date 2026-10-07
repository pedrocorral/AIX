"""Leaf: ABAP units and their style metrics for `aix code style` (benchmark section 22, abaplint as the reference).
A unit is a METHOD, FORM, FUNCTION or MODULE up to its END word; statements end with a period and a colon chains
them (`DATA: a, b.` is two); `*` in column 1 and `"` to the end of a line are comments; keywords are
case-insensitive. The metrics are the ones of the other languages: lines (head to END word), McCabe cyclomatic
(`1 +` IF, ELSEIF, each WHEN but OTHERS, LOOP, DO, WHILE, SELECT loop, AT, CATCH, CHECK, each AND/OR), Campbell
cognitive (a block and a CHECK cost 1 plus their nesting, ELSE/ELSEIF cost 1, CATCH 1 plus the nesting outside the
TRY, one per run of like boolean operators in a condition, TRY is not a level), nesting depth, parameters read from the definition."""
import re
from pathlib import Path

from codefiles import rel

UNITS = {"METHOD": "ENDMETHOD", "FORM": "ENDFORM", "FUNCTION": "ENDFUNCTION", "MODULE": "ENDMODULE"}
BLOCKS = {"IF": "ENDIF", "LOOP": "ENDLOOP", "DO": "ENDDO", "WHILE": "ENDWHILE", "CASE": "ENDCASE", "TRY": "ENDTRY", "AT": "ENDAT", "SELECT": "ENDSELECT"}
CLOSERS = set(BLOCKS.values())
SIMPLE = ("ELSEIF", "ELSE", "CHECK")
AT_BLOCK = re.compile(r"^AT\s+(?:NEW|END\s+OF|FIRST|LAST)\b")
BOOL = re.compile(r"\b(AND|OR)\b")
SECTION = re.compile(r"\b(PUBLIC|PROTECTED|PRIVATE)\s+SECTION\b")
PARAM_SECTIONS = ("IMPORTING", "EXPORTING", "CHANGING", "RETURNING", "RAISING", "EXCEPTIONS")
FORM_SKIP = {"TYPE", "LIKE", "STRUCTURE", "DEFAULT"}
FUNCTION_PARAM = re.compile(r'^\*"\s+(?:(?:VALUE|REFERENCE)\((\w+)\)|(\w+)\s+(?:TYPE|LIKE|STRUCTURE)\b)', re.I)
LOOP_VARS = {"i", "j", "k", "n", "x", "y", "z", "_", "e", "f", "p", "m", "t"}


# ---- statements -------------------------------------------------------------------------------------------------

class _Stripper:
    """Comments and strings out of one line, keeping the code inside a template's `{ }` (an embedded expression
    such as `|...{ get_x( ) }...|` is code: calls, conditions, names)."""
    def __init__(self, quote: str = None):
        self.out, self.quote, self.braces, self.inner = [], quote, 0, None   # inner: a string inside an embedded expression

    def feed(self, ch: str):
        """One character, by state: inside a string of an embedded expression, inside the expression, inside a
        string or template, or in code."""
        if self.inner:
            self.inner = None if ch == self.inner else self.inner
            self.out.append("'S'") if not self.inner else None
        elif self.quote == "|" and self.braces:
            self._embedded(ch)
        elif self.quote:
            self._in_string(ch)
        elif ch in "'`|":
            self.quote = ch
        else:
            self.out.append(ch)

    def _in_string(self, ch: str):
        if ch == self.quote:
            self.out.append("'S'"); self.quote = None
        elif ch == "{":
            self.braces = 1; self.out.append(" ")

    def _embedded(self, ch: str):
        if ch in "'`":
            self.inner = ch
        elif ch == "{":
            self.braces += 1
        elif ch == "}":
            self.braces -= 1; self.out.append(" ")
        else:
            self.out.append(ch)


def strip_line(line: str, quote: str = None) -> tuple:
    """(code, open template) of one line: a `*` comment line is empty, a `"` comment is cut, a string literal becomes
    `'S'` so its periods, commas and words do not count, the code inside a template's `{ }` stays. A `'` or a backtick
    string ends with the line; a template `|...{ }...|` may continue on the next line, so its state is handed on."""
    if line.startswith("*"):
        return "", quote
    st = _Stripper(quote)
    for ch in line:
        if ch == '"' and not st.quote and not st.inner:
            break
        st.feed(ch)
    if st.quote and st.quote != "|":
        st.out.append("'S'"); st.quote = None
    return "".join(st.out), st.quote


class _Splitter:
    """Statements out of stripped lines: (first word in upper case, text, line); a chain (`DATA: a, b.`) yields one
    statement per item, each starting with the chain's head."""
    def __init__(self, first_line: int):
        self.out, self.buf, self.line, self.depth, self.chain, self.next_line = [], [], None, 0, None, first_line

    def feed(self, code: str):
        for ch in code:
            self._char(ch)
        self.buf.append(" "); self.next_line += 1

    def _char(self, ch: str):
        """A colon starts a chain (`DATA: a, b.`, or `obj->m( : a = 1 ), a = 2 ).` where the head's open parenthesis
        is closed by every item); a comma at the item's own depth ends an item; a period ends the statement."""
        if self.line is None and not ch.isspace():
            self.line = self.next_line
        self.depth += (ch == "(") - (ch == ")")
        if ch == ":" and self.chain is None:
            self.chain = "".join(self.buf).strip(); self.buf, self.depth = [], 0
        elif ch == "," and self.depth <= 0 and self.chain is not None:
            self._emit(); self.depth = 0
        elif ch == ".":
            self._emit(); self.chain, self.depth = None, 0
        else:
            self.buf.append(ch)

    def _emit(self):
        text = (self.chain + " " if self.chain else "") + "".join(self.buf).strip()
        if text.strip():
            self.out.append((text.split()[0].upper(), text, self.line))
        self.buf, self.line = [], None


def statements(lines: list, first_line: int = 1) -> list:
    sp, quote = _Splitter(first_line), None
    for raw in lines:
        code, quote = strip_line(raw, quote)
        sp.feed(code)
    return sp.out


# ---- metrics ----------------------------------------------------------------------------------------------------

def _select_loops(stmts: list) -> set:
    """Indices of the SELECT statements that an ENDSELECT closes: those are loops, the others fetch one result."""
    loops, open_selects = set(), []
    for i, (word, _text, _line) in enumerate(stmts):
        if word == "SELECT":
            open_selects.append(i)
        elif word == "ENDSELECT" and open_selects:
            loops.add(open_selects.pop())
    return loops


class _Walk:
    """Cyclomatic, cognitive (with its items), nesting depth and the deepest line over a unit's statements."""
    def __init__(self, start_line: int):
        self.cyc, self.cog, self.items, self.depth, self.deepest_line = 1, 0, [], 0, start_line
        self.nest, self.stack = 0, []   # stack of [closer, nests]: a TRY frame starts flat and nests from its first CATCH

    def feed(self, word: str, text: str, line: int):
        up = text.upper()
        if word in CLOSERS:
            self._close()
        elif word in BLOCKS and (word != "AT" or AT_BLOCK.match(up)):
            self._block(word, line)
        elif word == "CATCH":
            self._catch(line)
        elif word in SIMPLE:
            self._simple(word, line)
        self.cyc += len(re.findall(r"\bWHEN\b(?!\s+OTHERS\b)", up))
        self._booleans(up, line, cognitive=word != "WHEN")   # `WHEN 'A' OR 'B'` is two case labels: paths, not a condition to read

    def _simple(self, word: str, line: int):
        """ELSEIF and ELSE cost 1; CHECK is a hidden if (`IF NOT x. RETURN. ENDIF.`): a path and 1 plus the nesting."""
        inc = 1 + self.nest if word == "CHECK" else 1
        self.cyc += word != "ELSE"; self.cog += inc
        self.items.append((line, inc, f"{word.lower()} (+1, nesting +{self.nest})" if inc > 1 else f"{word.lower()} (+1)"))

    def _open(self, closer: str, line: int, nests: bool):
        self.stack.append([closer, nests]); self.nest += nests
        if len(self.stack) > self.depth:
            self.depth, self.deepest_line = len(self.stack), line

    def _close(self):
        if self.stack:
            self.nest -= self.stack.pop()[1]

    def _block(self, word: str, line: int):
        """A block costs a path (CASE: its WHENs do) and 1 plus the nesting; TRY costs nothing and is not a level."""
        if word == "TRY":
            return self._open("ENDTRY", line, nests=False)
        self.cyc += word != "CASE"
        inc = 1 + self.nest; self.cog += inc
        self.items.append((line, inc, f"{word.lower()} (+1, nesting +{self.nest})" if self.nest else f"{word.lower()} (+1)"))
        self._open(BLOCKS[word], line, nests=True)

    def _catch(self, line: int):
        self.cyc += 1
        frame = self.stack[-1] if self.stack and self.stack[-1][0] == "ENDTRY" else None
        outside = self.nest - (1 if frame and frame[1] else 0)
        self.cog += 1 + outside
        self.items.append((line, 1 + outside, f"catch (+1, nesting +{outside})" if outside else "catch (+1)"))
        if frame and not frame[1]:
            frame[1] = True; self.nest += 1

    def _booleans(self, up: str, line: int, cognitive: bool = True):
        ops = BOOL.findall(up)
        self.cyc += len(ops)
        runs = sum(1 for i, op in enumerate(ops) if i == 0 or op != ops[i - 1]) if cognitive else 0
        self.cog += runs
        self.items += [(line, 1, "boolean operator (+1)")] * runs


def metrics(stmts: list, start_line: int) -> dict:
    loops = _select_loops(stmts)
    walk = _Walk(start_line)
    for i, (word, text, line) in enumerate(stmts):
        walk.feed(word if word != "SELECT" or i in loops else "SELECT-ONE", text, line)
    return dict(cyclomatic=walk.cyc, cognitive=walk.cog, cognitive_items=walk.items, nesting=walk.depth, deepest=(walk.deepest_line, walk.deepest_line))


# ---- the definition: parameters, visibility, abapdoc ------------------------------------------------------------

def _method_definition(stmts: list, name: str):
    """The `METHODS name ...` statement of a method (`zif~name` looks for `name`) and its section, or (None, None)."""
    plain = name.split("~")[-1].upper()
    section = "PUBLIC"
    for word, text, _line in stmts:
        up = text.upper()
        m = SECTION.search(up)
        if m:
            section = m.group(1)
        if word in ("METHODS", "CLASS-METHODS") and re.match(rf"(?:CLASS-)?METHODS\s+{re.escape(plain)}\b", up):
            return text, section
    return None, None


def _method_params(definition: str) -> int:
    """Every parameter under IMPORTING, EXPORTING and CHANGING carries TYPE or LIKE; RETURNING is the result."""
    up, count = definition.upper(), 0
    for section in ("IMPORTING", "EXPORTING", "CHANGING"):
        m = re.search(rf"\b{section}\b(.*?)(?=\b(?:{'|'.join(s for s in PARAM_SECTIONS if s != section)})\b|$)", up, re.S)
        if m:
            count += len(re.findall(r"\b(?:TYPE|LIKE)\b", m.group(1)))
    return count


def _form_params(head: str) -> int:
    """`FORM f USING a b TYPE t CHANGING c TABLES d`: the names under USING, CHANGING and TABLES."""
    count, inside, skip = 0, False, False
    for tok in [t.upper() for t in head.replace("(", " (").split()[2:]]:
        if tok in ("USING", "CHANGING", "TABLES", "RAISING"):
            inside = tok != "RAISING"
            continue
        counted = inside and not skip and tok not in FORM_SKIP and tok != "OPTIONAL"
        skip = tok in FORM_SKIP   # the type or default value after TYPE, LIKE, STRUCTURE, DEFAULT is not a parameter
        count += counted
    return count


def _function_params(raw_lines: list, head_index: int) -> int:
    """abapGit writes a function module's interface as `*"` comment lines under its head."""
    count = 0
    for line in raw_lines[head_index + 1:]:
        if not line.startswith('*"'):
            break
        count += bool(FUNCTION_PARAM.match(line))
    return count


def _abapdoc_above(raw_lines: list, index: int) -> bool:
    """A comment directly above a line (abapdoc `"!`, `*` or `"`), blank lines allowed in between for abapdoc."""
    i = index - 1
    while i >= 0 and not raw_lines[i].strip():
        i -= 1
    return i >= 0 and raw_lines[i].lstrip().startswith(('"', "*")) and not raw_lines[i].startswith('*"')


# ---- units ------------------------------------------------------------------------------------------------------

def _advice(stmts: list, plain: set) -> tuple:
    """(magic numbers, single-letter names) with their lines; offsets and lengths (`v+1(2)`, `LENGTH 10`) are not magic."""
    magic, short = set(), set()
    for word, text, line in stmts:
        code = re.sub(r"(?<=\w)\+\d+(?:\(\d+\))?|(?<=\w)\(\d+\)|\b(?:LENGTH|DECIMALS|OCCURS)\s+\d+", " ", text, flags=re.I)
        magic |= {(line, float(m)) for m in re.findall(r"(?<![\w.'-])\d+(?![\w.])", code) if float(m) not in plain}
        if word in ("DATA", "STATICS", "FIELD-SYMBOLS"):
            m = re.match(r"\S+\s+<?([A-Za-z])>?\b", text)
            if m and m.group(1) not in LOOP_VARS:
                short.add((line, m.group(1)))
    return sorted(magic), sorted(short)


class _Source:
    """One ABAP file as the unit reader sees it: its raw lines, its statements and the plain-number set."""
    def __init__(self, file: Path, text: str, plain: set):
        self.file, self.raw, self.plain = file, text.splitlines(), plain
        self.stmts = statements(self.raw)


def _definition_facts(src: _Source, kind: str, name: str, head: str, head_index: int) -> tuple:
    """(parameters, public, documented) of a unit from its definition or its head."""
    documented = _abapdoc_above(src.raw, head_index)
    if kind == "METHOD":
        definition, section = _method_definition(src.stmts, name)
        if definition is not None:
            def_line = next(line for _w, text, line in src.stmts if text is definition)
            documented = documented or _abapdoc_above(src.raw, def_line - 1)
        return (_method_params(definition) if definition else 0), ("~" in name or section in (None, "PUBLIC")), documented
    if kind == "FORM":
        return _form_params(head), True, documented
    return (_function_params(src.raw, head_index) if kind == "FUNCTION" else 0), True, documented


def _unit_name(kind: str, name: str, cls: str, file: Path) -> str:
    own = cls and cls.lower() == file.name.split(".")[0].lower()
    return name.lower() if kind != "METHOD" or not cls or own else f"{cls.lower()}.{name.lower()}"


def _record(src: _Source, unit: tuple) -> dict:
    """The function record of one unit; `unit` is (kind, name, class, head index, end index) over the statements."""
    kind, name, cls, i, j = unit
    head_line, end_line = src.stmts[i][2], src.stmts[j][2]
    body = src.stmts[i + 1:j]
    params, public, documented = _definition_facts(src, kind, name, src.stmts[i][1], head_line - 1)
    magic, short = _advice(body, src.plain)
    fname = name.lower()
    fx = dict(name=_unit_name(kind, name, cls, src.file), file=rel(src.file), line=head_line, head_line=head_line, lang="abap", lines=end_line - head_line + 1, params=params,
              docstring=documented, public=public, short_names=short, magic=magic, fname=fname, src="\n".join(src.raw[head_line - 1:end_line]), own="",
              test=".testclasses." in src.file.name or fname.startswith("test"), decorated=False, passthrough=None, jsx=False, hygiene=[], cls=cls, src_head=src.stmts[i][1])
    fx.update(metrics(body, head_line))
    return fx


def functions(file: Path, text: str, plain: set) -> list:
    """Every unit of an ABAP file as a function record of `aix code style`."""
    src = _Source(file, text, plain)
    out, cls, i = [], None, 0
    while i < len(src.stmts):
        word, head, _line = src.stmts[i]
        if word == "CLASS" and re.match(r"CLASS\s+(\S+)\s+IMPLEMENTATION", head, re.I):
            cls = re.match(r"CLASS\s+(\S+)", head, re.I).group(1)
        if word in UNITS:
            name = head.split()[1] if len(head.split()) > 1 else "?"
            j = next((k for k in range(i + 1, len(src.stmts)) if src.stmts[k][0] == UNITS[word]), len(src.stmts) - 1)
            out.append(_record(src, (word, name, cls, i, j)))
            i = j
        i += 1
    return out
