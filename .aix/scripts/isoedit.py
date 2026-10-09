"""Leaf: writing the isolation declaration. Each isolation is one block (`  name:` and its keys, two spaces deeper);
a change re-renders that block alone, so the rest of the file, its comments and its order stay as a person wrote
them (a comment inside a re-rendered block is not kept). Used by `--propose` (a draft, or new frontier suggestions
merged into an existing declaration) and `--review` (the statuses a person chose)."""
import re

KEYS = ("paths", "frontiers", "owner", "description")
UNSAFE = re.compile(r"""^[\s*&!|>'"%@`{\[,#?:.-]|: | #|\s$|^\.$""")


def quote(value: str) -> str:
    """A scalar as YAML that the kit's reader and any YAML reader read back as the same string."""
    v = str(value)
    return '"' + v.replace('"', '\\"') + '"' if UNSAFE.search(v) or v == "" else v


def flow(value) -> str:
    """A list or a map on one line: `[a, b]`, `{".": accepted, ports/sql: proposed}`."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{quote(k)}: {quote(v)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(quote(v) for v in value) + "]"
    return quote(value)


def render_block(name: str, spec: dict) -> list:
    """`  name:` and one line per key, in a fixed order."""
    lines = [f"  {name}:"]
    for key in KEYS:
        if key in spec and spec[key] is not None:
            lines.append(f"    {key}: {flow(spec[key])}")
    return lines


def _block_span(lines: list, name: str):
    """(first, end) line indices of an isolation's block, or None when the file has no such block."""
    head = re.compile(r"^  " + re.escape(name) + r"\s*:")
    start = next((i for i, l in enumerate(lines) if head.match(l)), None)
    if start is None:
        return None
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > 2):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1   # blank lines after a block belong to the file, not to the block
    return start, end


def replace_block(text: str, name: str, spec: dict) -> str:
    """The declaration with one isolation's block rendered from spec (appended under `isolations:` when missing)."""
    lines = text.splitlines()
    span = _block_span(lines, name)
    new = render_block(name, spec)
    if span is None:
        at = next((i + 1 for i, l in enumerate(lines) if l.startswith("isolations:")), len(lines))
        lines[at:at] = new
    else:
        lines[span[0]:span[1]] = new
    return "\n".join(lines) + "\n"


def with_frontiers(text: str, raw: dict, changes: dict) -> str:
    """Apply {(isolation, folder): status} to the declaration text: each touched isolation re-rendered once."""
    by_iso = {}
    for (name, folder), status in changes.items():
        by_iso.setdefault(name, {})[folder] = status
    for name, statuses in sorted(by_iso.items()):
        spec = dict(raw["isolations"].get(name) or {})
        frontiers = dict(spec.get("frontiers") or {})
        frontiers.update(statuses)
        spec["frontiers"] = dict(sorted(frontiers.items(), key=lambda kv: (kv[0] != ".", kv[0])))
        text = replace_block(text, name, spec)
    return text
