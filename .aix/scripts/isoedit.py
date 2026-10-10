"""Leaf: writing the isolation declaration. Each isolation is one block (`  name:` and its keys, two spaces deeper);
a change re-renders that block alone, so the rest of the file, its comments and its order stay as a person wrote
them (a comment inside a re-rendered block is not kept). Used by `--propose` (a draft, or new frontier suggestions
merged into an existing declaration) and `--review` (the statuses a person chose)."""
import re
from typing import Optional

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


def render_block(name: str, spec: dict, indent: int = 2, step: int = 2) -> list:
    """`name:` and one line per key, in a fixed order, at the file's own indentation."""
    lines = [f"{' ' * indent}{name}:"]
    for key in KEYS:
        if key in spec and spec[key] is not None:
            lines.append(f"{' ' * (indent + step)}{key}: {flow(spec[key])}")
    return lines


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _content(line: str) -> bool:
    """A line that carries YAML (not blank, not a comment)."""
    s = line.strip()
    return bool(s) and not s.startswith("#")


def _region(lines: list) -> Optional[tuple]:
    """(first line after `isolations:`, end) of the isolations map, and the indentation of its entries."""
    head = next((i for i, l in enumerate(lines) if re.match(r"^isolations\s*:", l)), None)
    if head is None:
        return None
    end = next((j for j in range(head + 1, len(lines)) if _content(lines[j]) and _indent(lines[j]) == 0), len(lines))
    first = next((j for j in range(head + 1, end) if _content(lines[j])), None)
    return head + 1, end, (_indent(lines[first]) if first is not None else 2)


def _block_span(lines: list, name: str, region: tuple):
    """(first, end) line indices of an isolation's block inside the isolations map, or None."""
    start_at, region_end, indent = region
    head = re.compile(r"^" + " " * indent + re.escape(name) + r"\s*:")
    start = next((i for i in range(start_at, region_end) if head.match(lines[i])), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, region_end) if _content(lines[j]) and _indent(lines[j]) <= indent), region_end)
    while end > start + 1 and not _content(lines[end - 1]):
        end -= 1   # blank lines and comments after a block belong to the file, not to the block
    return start, end


def _step(lines: list, span, indent: int) -> int:
    """The extra indentation of a block's keys (2 unless the file uses another)."""
    inner = next((l for l in lines[span[0] + 1:span[1]] if _content(l)), None) if span else None
    return (_indent(inner) - indent) if inner and _indent(inner) > indent else 2


def replace_block(text: str, name: str, spec: dict) -> str:
    """The declaration with one isolation's block rendered from spec (appended to the isolations map when missing)."""
    lines = text.splitlines()
    region = _region(lines)
    if region is None:
        lines += ["isolations:", *render_block(name, spec)]
        return "\n".join(lines) + "\n"
    span = _block_span(lines, name, region)
    new = render_block(name, spec, region[2], _step(lines, span, region[2]))
    if span is None:
        at = region[1]
        while at > region[0] and not _content(lines[at - 1]):
            at -= 1
        lines[at:at] = new
    else:
        lines[span[0]:span[1]] = new
    return "\n".join(lines) + "\n"


def _normal(folder) -> str:
    return str(folder).strip().strip("/") or "."


def with_frontiers(text: str, raw: dict, changes: dict) -> str:
    """Apply {(isolation, folder): status} to the declaration text: each touched isolation re-rendered once; a frontier
    written `api/` is the same as `api`."""
    by_iso = {}
    for (name, folder), status in changes.items():
        by_iso.setdefault(name, {})[_normal(folder)] = status
    for name, statuses in sorted(by_iso.items()):
        spec = dict(raw["isolations"].get(name) or {})
        frontiers = {_normal(k): v for k, v in (spec.get("frontiers") or {}).items()}
        frontiers.update(statuses)
        spec["frontiers"] = dict(sorted(frontiers.items(), key=lambda kv: (kv[0] != ".", kv[0])))
        text = replace_block(text, name, spec)
    return text
