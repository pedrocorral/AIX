"""Leaf: a tiny YAML subset with no dependency: scalars, lists, one-level maps, `key: |` blocks, and the front matter
of a Markdown file. Enough for config.yaml, profiles, policies and SKILL.md heads; not a YAML parser. `parse_tree`
reads nested maps by indentation, `- item` and `[a, b]` lists and `{k: v}` flow maps (the isolation declaration)."""
import re
from pathlib import Path


# ---- tiny YAML subset (no dependency): scalars, lists, one-level maps, `key: |` blocks --------------------------------

class _Yaml:
    """State of the tiny YAML reader: the map being built, the current key, and a `key: |` block in progress."""
    def __init__(self):
        self.out, self.key, self.block = {}, None, None

    def close_block(self):
        if self.block is not None:
            self.out[self.key] = "\n".join(self.block).rstrip() + "\n"
            self.block = None

    def block_line(self, raw: str) -> bool:
        """A line inside a `key: |` block: appended; a dedented line closes the block. Returns True when consumed."""
        if self.block is None:
            return False
        if not raw.strip() or raw.startswith(("  ", "\t")):
            self.block.append(raw[2:] if raw.startswith("  ") else raw[1:])
            return True
        self.close_block()
        return False

    def nested_line(self, raw: str) -> bool:
        """`  - item` (a list) or `  k: v` (a one-level map) under the current key."""
        if raw.startswith("  - "):
            if not isinstance(self.out.get(self.key), list):
                self.out[self.key] = []
            self.out[self.key].append(_scalar(raw[4:]))
            return True
        if raw.startswith(("  ", "\t")) and ":" in raw:
            k, v = raw.strip().split(":", 1)
            if not isinstance(self.out.get(self.key), dict):
                self.out[self.key] = {}
            self.out[self.key][k.strip()] = _scalar(v)
            return True
        return False

    def top_line(self, raw: str):
        """`key: value` at the top level: a block start, an empty value, an inline list, or a scalar."""
        key, v = raw.split(":", 1)
        self.key, v = key.strip(), _strip_comment(v)
        if v == "|":
            self.block = []
        elif v == "":
            self.out[self.key] = None
        elif v.startswith("[") and v.endswith("]"):
            self.out[self.key] = [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
        else:
            self.out[self.key] = _scalar(v)


def parse_yaml(text: str) -> dict:
    """The subset the kit uses: scalars, `[a, b]` lists, `- item` lists, one-level maps, `key: |` blocks, comments."""
    y = _Yaml()
    for raw in text.splitlines():
        if y.block_line(raw) or not raw.strip() or raw.lstrip().startswith("#") or y.nested_line(raw):
            continue
        if ":" in raw:
            y.top_line(raw)
    y.close_block()
    return y.out


def _strip_comment(v: str) -> str:
    v = v.strip()
    if v and v[0] in "\"'":
        end = v.find(v[0], 1)
        return v[:end + 1] if end > 0 else v
    return v.split("#", 1)[0].strip()


def _scalar(v: str):
    v = _strip_comment(v)
    if v and v[0] in "\"'" and v[-1] == v[0] and len(v) > 1:
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return v


def front_matter(md: Path) -> dict:
    text = md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    return parse_yaml(text[3:end]) if end > 0 else {}


# ---- nested maps by indentation (parse_tree) ---------------------------------------------------------------------

def _content_lines(text: str) -> list:
    """(indent, content, line number) of every line that carries something, comments and blanks dropped."""
    out = []
    for n, raw in enumerate(text.splitlines(), 1):
        body = _strip_line_comment(raw.rstrip())
        if body.strip():
            out.append((len(body) - len(body.lstrip(" ")), body.strip(), n))
    return out


def _strip_line_comment(line: str) -> str:
    """The line without a `# comment` that is outside quotes (`#` inside a value needs a space before it)."""
    quote = None
    for i, ch in enumerate(line):
        if ch in "\"'" and quote in (None, ch):
            quote = None if quote else ch
        elif ch == "#" and quote is None and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


FLOW_DEPTH = {"[": 1, "{": 1, "]": -1, "}": -1}


def _quote_after(ch: str, quote):
    """The quote still open after reading ch: a quote opens one, the same quote closes it."""
    if ch in "\"'" and quote in (None, ch):
        return None if quote else ch
    return quote


def _split_flow(s: str) -> list:
    """Top-level comma-separated items of a flow collection's inside, brackets and quotes respected."""
    items, depth, quote, cur = [], 0, None, ""
    for ch in s:
        quote = _quote_after(ch, quote)
        if quote is None and ch == "," and depth == 0:
            items.append(cur.strip()); cur = ""
            continue
        depth += FLOW_DEPTH.get(ch, 0) if quote is None else 0
        cur += ch
    return [x for x in items + [cur.strip()] if x]


def _flow_map(inside: str, line: int) -> dict:
    out = {}
    for item in _split_flow(inside):
        key, sep, rest = item.partition(":")
        if not sep:
            raise ValueError(f"line {line}: `{item}` in a {{...}} map has no `key: value`")
        if _tree_scalar(key) in out:
            raise ValueError(f"line {line}: `{_tree_scalar(key)}` appears twice in the same map")
        out[_tree_scalar(key)] = _flow_value(rest, line)
    return out


def _flow_value(text: str, line: int):
    """`[a, b]`, `{k: v, k2: [x]}` or a scalar."""
    text = text.strip()
    closing = {"[": "]", "{": "}"}.get(text[:1])
    if closing and not text.endswith(closing):
        raise ValueError(f"line {line}: `{text[0]}` is not closed with `{closing}` on the same line")
    if closing == "]":
        return [_flow_value(x, line) for x in _split_flow(text[1:-1])]
    if closing == "}":
        return _flow_map(text[1:-1], line)
    return _tree_scalar(text) if text else None


def _tree_scalar(v: str):
    """A scalar of parse_tree: comments were cut from the line already (a `#` needs a space before it), so a `#`
    inside a value (`team#1`) stays; quotes are removed, true/false are booleans."""
    v = v.strip()
    if len(v) > 1 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    return v == "true" if v in ("true", "false") else v


def _key_value(content: str, line: int) -> tuple:
    """`key: value` -> (key, value text); the colon must be followed by a space or the end of the line."""
    m = re.match(r"""^("[^"]*"|'[^']*'|[^:]+?)\s*:(?:\s+(.*)|$)""", content)
    if not m:
        raise ValueError(f"line {line}: expected `key: value`, found `{content}`")
    return _tree_scalar(m.group(1)), (m.group(2) or "")


def _block(lines: list, i: int, indent: int) -> tuple:
    """(value, next index) of the block whose lines start at `indent`: a list (`- x`) or a map (`k: v`)."""
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        return _list_block(lines, i, indent)
    out = {}
    while i < len(lines) and lines[i][0] == indent:
        _ind, content, n = lines[i]
        key, rest = _key_value(content, n)
        if key in out:
            raise ValueError(f"line {n}: `{key}` appears twice in the same map")
        out[key], i = _map_value(lines, i + 1, indent, rest, n)
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError(f"line {lines[i][2]}: unexpected indentation")
    return out, i


def _map_value(lines: list, i: int, indent: int, rest: str, n: int) -> tuple:
    """(value, next index) of one key: written on its line, a deeper block below it, or nothing."""
    if rest.strip():
        return _flow_value(rest, n), i
    if i < len(lines) and lines[i][0] > indent:
        return _block(lines, i, lines[i][0])
    return None, i


def _list_block(lines: list, i: int, indent: int) -> tuple:
    out = []
    while i < len(lines) and lines[i][0] == indent and (lines[i][1].startswith("- ") or lines[i][1] == "-"):
        out.append(_flow_value(lines[i][1][1:], lines[i][2]))
        i += 1
    return out, i


def parse_tree(text: str) -> dict:
    """Nested maps by indentation (spaces), `- item` and `[a, b]` lists, `{k: v}` flow maps, quoted scalars,
    comments. Raises ValueError naming the line on anything else."""
    lines = _content_lines(text)
    if not lines:
        return {}
    tabbed = next((n for n, raw in enumerate(text.splitlines(), 1) if "\t" in raw[:len(raw) - len(raw.lstrip())]), None)
    if tabbed:
        raise ValueError(f"line {tabbed}: indent with spaces, not tabs")
    value, i = _block(lines, 0, lines[0][0])
    if i < len(lines):
        raise ValueError(f"line {lines[i][2]}: unexpected indentation")
    if not isinstance(value, dict):
        raise ValueError("the file must be a map (`key: value` at the top), not a list")
    return value
