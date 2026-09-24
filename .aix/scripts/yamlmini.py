"""Leaf: a tiny YAML subset with no dependency: scalars, lists, one-level maps, `key: |` blocks, and the front matter
of a Markdown file. Enough for config.yaml, profiles, policies and SKILL.md heads; not a YAML parser."""
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
