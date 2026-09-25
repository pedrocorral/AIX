"""Leaf: the managed H2 sections of AGENTS.md as text. No file, no layer, no agent: what to call a section and how to
replace, append or remove one block in a Markdown text."""

INS_HEADER = "## Scoped instructions"
MANAGED = ("## Organisation", "## Scoped instructions", "## Cycle", "## Always-on skills", "## Project notes")


def replace_section(text: str, header: str, section: str) -> str:
    """Replace (or append, or remove when empty) the managed H2 `header` block."""
    if header in text:
        head, rest = text.split(header, 1)
        tail = rest.split("\n## ", 1)
        remainder = ("## " + tail[1]) if len(tail) > 1 else ""
        return head + section + remainder
    return (text.rstrip("\n") + "\n\n" + section) if section else text
