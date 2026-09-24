#!/usr/bin/env python3
"""Validate AIX documentation integrity. Exit 1 on errors.
Checks: front-matter presence, skill name == flat path, every folder under docs/ has INDEX.md,
every doc file is listed in its folder INDEX, referenced IDs exist, relative links resolve,
tests reference existing requirements, vulnerability register statuses are valid."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS, SKILLS, META = ROOT / "docs", ROOT / ".aix" / "skills", ROOT / ".aix" / "meta-docs"
ID_RE = re.compile(r"\b(FR|NFR|API|DM|ADR|TS|VUL|TASK|CONFLICT)-[A-Z0-9]+(?:-\d{3,4})?\b")
LINK_RE = re.compile(r"\]\(([^)#\s]+)")
VALID_VUL = {"expected", "unverified", "confirmed", "mitigated", "addressed", "accepted", "not-applicable"}
errors, warnings = [], []


def frontmatter(p: Path):
    t = p.read_text(encoding="utf-8", errors="replace")
    if not t.startswith("---"):
        return None, t
    end = t.find("\n---", 3)
    fm = t[3:end]
    out = {}
    for m in re.finditer(r"^([a-zA-Z_]+):[ \t]*(.*)$", fm, re.M):
        key, value = m.group(1), m.group(2).strip()
        if value in (">", "|", ">-", "|-"):  # YAML block scalar: join the indented lines that follow
            block = []
            for line in fm[m.end():].splitlines()[1:]:
                if line.startswith((" ", "\t")):
                    block.append(line.strip())
                else:
                    break
            value = " ".join(block)
        out[key] = value
    return out, t


def check_skills():
    trees = [SKILLS, ROOT / ".aix" / "custom" / "skills", ROOT / ".aix" / "org" / "skills"]
    for base in [b for b in trees if b.is_dir()]:
        for md in base.rglob("SKILL.md"):
            _check_skill(md, base)


def _check_skill(md, base):
        fm, _ = frontmatter(md)
        parts = md.parent.relative_to(base).parts
        flat = "-".join(parts[1:]) if parts[0] == "extern" else "-".join(parts)
        if not fm:
            errors.append(f"{md}: missing front-matter"); return
        cls = fm.get("class", "").strip('"')
        if cls:
            flat = "-".join(cls.split("/")[1:]) if cls.startswith("extern/") else cls.replace("/", "-")
        if fm.get("name") != flat:
            errors.append(f"{md}: name '{fm.get('name')}' must equal the class flat name '{flat}' (the runtimes link by it); put the implementation's own name in `id:`")
        if len(fm.get("description", "")) < 40:
            warnings.append(f"{md}: description too short to trigger reliably")


INSTRUCTION_TREES = (ROOT / ".aix" / "instructions", ROOT / ".aix" / "custom" / "instructions", ROOT / ".aix" / "org" / "instructions")


def _check_instruction(md):
    fm, _ = frontmatter(md)
    if not fm or not fm.get("id"):
        errors.append(f"{md.relative_to(ROOT)}: instruction needs front-matter with `id:`"); return
    if fm.get("block") == "true":
        if not fm.get("section") and fm.get("order", "0") != "0":
            errors.append(f"{md.relative_to(ROOT)}: a block needs `section:` (its H2 title) unless it is the header (order 0)")
        return  # blocks are AGENTS.md text; the description is for people, no trigger length needed
    if len(fm.get("description", "")) < 40:
        warnings.append(f"{md.relative_to(ROOT)}: description too short for the runtimes to pick it")


def check_instructions():
    for base in INSTRUCTION_TREES:
        for md in (base.rglob("*.md") if base.is_dir() else []):
            _check_instruction(md)


def _unlisted(d, listed: str):
    for f in d.iterdir():
        if f.name in {"INDEX.md", ".gitkeep"} or f.name.startswith("."):
            continue
        if f.name not in listed and f.name.replace(".md", "") not in listed:
            yield f


def check_indexes():
    folders = [DOCS, META, *[p for p in DOCS.rglob("*") if p.is_dir()], *[p for p in META.rglob("*") if p.is_dir()]]
    for d in folders:
        idx = d / "INDEX.md"
        if not idx.exists():
            errors.append(f"{d.relative_to(ROOT)}: missing INDEX.md"); continue
        if "road-map" in str(d):
            continue  # task files move often; road-map INDEX lists folders, not tasks
        for f in _unlisted(d, idx.read_text(encoding="utf-8")):
            warnings.append(f"{idx.relative_to(ROOT)}: does not list {f.name}")


def collect_ids():
    defined = {}
    for md in DOCS.rglob("*.md"):
        fm, _ = frontmatter(md)
        if fm and "id" in fm:
            defined.setdefault(fm["id"], md)
    return defined


def _check_links(md, text: str):
    for m in LINK_RE.finditer(text):
        target = m.group(1)
        if target.startswith(("http", "mailto:")):
            continue
        if not (md.parent / target).exists() and not (ROOT / target).exists():
            errors.append(f"{md.relative_to(ROOT)}: broken link {target}")


def _check_covers(md, defined):
    fm, _ = frontmatter(md)
    for rid in (fm or {}).get("covers", "").replace("[", "").replace("]", "").split(","):
        rid = rid.strip()
        if rid and rid not in defined and "EXAMPLE" not in rid:
            errors.append(f"{md.relative_to(ROOT)}: covers unknown requirement {rid}")


def check_references(defined):
    all_md = list(DOCS.rglob("*.md")) + list(META.rglob("*.md")) + list(SKILLS.rglob("*.md")) + [ROOT / "AGENTS.md"]
    for md in all_md:
        _check_links(md, md.read_text(encoding="utf-8", errors="replace"))
        if md.parent.name in {"functional", "non-functional"} and "tests" in md.parts:
            _check_covers(md, defined)


def _table_fields(md):
    """The first-column names of every data row in a document's tables."""
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ") and not line.startswith(("| Field", "| Code", "| Path", "|---")):
            yield line.split("|")[1].strip().strip("`")


def _known_fields(dic: Path) -> set:
    rows = (l for l in dic.read_text(encoding="utf-8").splitlines() if l.startswith("| ") and not l.startswith("| Field"))
    return {l.split("|")[1].strip() for l in rows}


def _check_fields_of(md: Path, known: set):
    for name in _table_fields(md):
        if re.fullmatch(r"[a-z][a-z0-9_]*", name) and name not in known:
            warnings.append(f"{md.relative_to(ROOT)}: field '{name}' not in field-dictionary.md")


def check_field_dictionary():
    dic = DOCS / "requirements" / "data-model" / "field-dictionary.md"
    if not dic.exists():
        return
    known = _known_fields(dic)
    for folder in ["requirements/data-model", "requirements/api"]:
        for md in (DOCS / folder).rglob("*.md"):
            if md.name not in {"INDEX.md", "field-dictionary.md"}:
                _check_fields_of(md, known)


def check_status_drift():
    """A doc may not claim implemented/automated/mitigated unless code carries the marker (the coverage matrix's 'catch')."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import coverage_matrix
    errors.extend(coverage_matrix.status_drift())


def check_vul_evidence():
    """Status beyond `expected` needs an audit report mentioning the VUL; `accepted` needs an ADR too."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import security
    if security.REGISTER.exists():
        errors.extend(security.problems())


def check_vul_register():
    reg = DOCS / "security" / "vulnerability-register.md"
    if not reg.exists():
        return
    for line in reg.read_text(encoding="utf-8").splitlines():
        if line.startswith("| VUL-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 4 and cells[3] not in VALID_VUL:
                errors.append(f"vulnerability-register: {cells[0]} has invalid status '{cells[3]}'")


def check_orphans():
    """A layer file that overrides nothing: a near-miss of a kit name is an error (a typo), a genuine addition a warning."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import layers
    typos, additions = layers.orphan_report(ROOT)
    for kind, name, layer, shown, near in typos:
        errors.append(f"{shown}: {kind} {name} ({layer} layer) overrides nothing; did you mean {near}? (names must match character by character)")
    for (kind, layer), names in sorted(additions.items()):
        warnings.append(layers.additions_line(kind, layer, names))


if __name__ == "__main__":
    check_orphans()
    check_instructions()
    check_status_drift()
    check_vul_evidence()
    check_skills(); check_indexes(); check_references(collect_ids()); check_field_dictionary(); check_vul_register()
    for w in warnings: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)
