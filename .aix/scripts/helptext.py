"""Leaf: the texts of the CLI, read from .aix/meta-docs/help/ (a layer's copy of a file wins, as for the guide):
usage.md is the one-screen usage, about.md is `aix about`, and one <topic>.md per `aix help <topic>` (spaces in a
topic become dashes: `aix help code graph` reads code-graph.md)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALIASES = {'validate': 'docs validate', 'coverage': 'docs coverage', 'security': 'docs security', 'code complexity': 'code graph', 'code dead': 'code graph', 'code clones': 'code graph', 'graph': 'code graph', 'complexity': 'code graph', 'self-update': 'self-install', 'self-test': 'self-install', 'rules': 'instructions'}  # old names and sub-commands documented with their parent


def help_file(name: str):
    """The highest layer's meta-docs/help/<name>.md, else the kit's, else None."""
    import layers
    found = None
    for layer, root in layers.layer_roots(ROOT):
        base = (root / "meta-docs" / "help") if layer != "kit" else (ROOT / ".aix" / "meta-docs" / "help")
        if (base / f"{name}.md").is_file():
            found = base / f"{name}.md"
    return found


def text(name: str) -> str:
    """usage.md, about.md: the kit always has them."""
    return help_file(name).read_text(encoding="utf-8")


def topic(name: str):
    """The help page of a command or `None` when there is none; `aix help code graph` and `aix help graph` both work."""
    f = help_file(ALIASES.get(name, name).replace(" ", "-"))
    return f.read_text(encoding="utf-8") if f else None


def topics() -> list:
    """Every topic the kit and the layers document, for the 'no help for' message."""
    import layers
    names = set()
    for layer, root in layers.layer_roots(ROOT):
        base = (root / "meta-docs" / "help") if layer != "kit" else (ROOT / ".aix" / "meta-docs" / "help")
        names |= {f.stem.replace("code-", "code ").replace("docs-", "docs ") for f in base.glob("*.md")} if base.is_dir() else set()
    return sorted(names - {"usage", "about"})
