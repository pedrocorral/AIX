"""`aix guide`: the user guide, chapter by chapter, through a pager when there is a terminal."""
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def guide_chapters():
    """[(key, title, path)] of the guide, the kit's .aix/meta-docs/guide/NN-key.md overlaid by a layer's copy of the same file."""
    import layers
    files = {}
    for layer, root in layers.layer_roots(ROOT):
        base = (root / "meta-docs" / "guide") if layer != "kit" else (ROOT / ".aix" / "meta-docs" / "guide")
        for f in (sorted(base.glob("[0-9][0-9]-*.md")) if base.is_dir() else []):
            files[f.name] = f
    out = []
    for name in sorted(files):
        text = files[name].read_text(encoding="utf-8")
        m = re.search(r"^title:\s*(.+)$", text, re.M)
        out.append((name[3:-3], m.group(1).strip() if m else name, files[name]))
    return out


def _guide_toc(chapters):
    print("The AIX guide — `aix guide <chapter>` opens one, `aix guide --all` prints everything\n")
    for i, (key, title, _) in enumerate(chapters, 1):
        print(f"  {i:2d}  {key:14s} {title}")
    print("\nOther help: `aix help <command>` for one command, `aix doctor` for what is wrong here.")


def _chapter_body(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    body = body[body.find("\n---", 3) + 4:].lstrip("\n") if body.startswith("---") else body
    return body.rstrip("\n") + "\n"


def _chapter_lookup(chapters, word: str):
    keys = {k: c for c in chapters for k in (c[0], )}
    keys.update({str(i): c for i, c in enumerate(chapters, 1)})
    return keys.get(word.lower().lstrip("0")) or keys.get(word.lower())


def run_guide(args):
    """aix guide [CHAPTER] [--all]: the user guide. No argument: the table of contents; a chapter key or number: that chapter."""
    chapters = guide_chapters()
    if not chapters:
        sys.exit("aix guide: no guide found under .aix/meta-docs/guide/")
    want = [k for k, _, _ in chapters] if "--all" in args else [a for a in args if not a.startswith("-")]
    if not want:
        return _guide_toc(chapters)
    texts = []
    for w in want:
        c = _chapter_lookup(chapters, w)
        if not c:
            sys.exit(f"aix guide: no chapter '{w}'. Chapters: " + ", ".join(k for k, _, _ in chapters))
        texts.append(_chapter_body(c[2]))
    page("\n\n".join(texts))


def page(text: str):
    """Print through a pager when there is a terminal and the text is longer than it; plain print otherwise."""
    import shutil as _sh, subprocess as _sp
    rows = _sh.get_terminal_size((80, 24)).lines
    pager = os.environ.get("PAGER") or ("less" if _sh.which("less") else None)
    if sys.stdout.isatty() and pager and text.count("\n") > rows - 2 and not os.environ.get("CI"):
        try:
            _sp.run([pager, "-R", "-F", "-X"] if pager == "less" else [pager], input=text, text=True)
            return
        except OSError:
            pass   # no usable pager: fall through to a plain print
    print(text, end="")
