#!/usr/bin/env python3
"""Validate AIX documentation integrity. Exit 1 on errors.
Checks: front-matter presence, skill name == flat path, every folder under docs/ has INDEX.md,
every doc file is listed in its folder INDEX, referenced IDs exist, relative links resolve,
tests reference existing requirements, vulnerability register statuses are valid."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS, SKILLS = ROOT / "docs", ROOT / "skills"
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
    for md in SKILLS.rglob("SKILL.md"):
        fm, _ = frontmatter(md)
        parts = md.parent.relative_to(SKILLS).parts
        flat = "-".join(parts[1:]) if parts[0] == "extern" else "-".join(parts)
        if not fm:
            errors.append(f"{md}: missing front-matter"); continue
        if fm.get("name") != flat:
            errors.append(f"{md}: name '{fm.get('name')}' != folder path '{flat}'")
        if len(fm.get("description", "")) < 40:
            warnings.append(f"{md}: description too short to trigger reliably")


def check_indexes():
    for d in [DOCS, *[p for p in DOCS.rglob("*") if p.is_dir()]]:
        if d.name in {"pending", "going-on", "completed", "next", "backlog", "ideas"} and d.parent.name in {"road-map", "pending"}:
            pass
        idx = d / "INDEX.md"
        if not idx.exists():
            errors.append(f"{d.relative_to(ROOT)}: missing INDEX.md"); continue
        listed = idx.read_text(encoding="utf-8")
        for f in d.iterdir():
            if f.name in {"INDEX.md", ".gitkeep"} or f.name.startswith("."):
                continue
            if f.name not in listed and f.name.replace(".md", "") not in listed:
                if "road-map" in str(d):
                    continue  # task files move often; road-map INDEX lists folders, not tasks
                warnings.append(f"{idx.relative_to(ROOT)}: does not list {f.name}")


def collect_ids():
    defined = {}
    for md in DOCS.rglob("*.md"):
        fm, _ = frontmatter(md)
        if fm and "id" in fm:
            defined.setdefault(fm["id"], md)
    return defined


def check_references(defined):
    all_md = list(DOCS.rglob("*.md")) + list(SKILLS.rglob("*.md")) + [ROOT / "AGENTS.md"]
    for md in all_md:
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            if target.startswith(("http", "mailto:")):
                continue
            if not (md.parent / target).exists() and not (ROOT / target).exists():
                errors.append(f"{md.relative_to(ROOT)}: broken link {target}")
        if md.parent.name in {"functional", "non-functional"} and "tests" in md.parts:
            fm, _ = frontmatter(md)
            for rid in (fm or {}).get("covers", "").replace("[", "").replace("]", "").split(","):
                rid = rid.strip()
                if rid and rid not in defined and "EXAMPLE" not in rid:
                    errors.append(f"{md.relative_to(ROOT)}: covers unknown requirement {rid}")


def check_field_dictionary():
    dic = DOCS / "requirements" / "data-model" / "field-dictionary.md"
    if not dic.exists():
        return
    known = {l.split("|")[1].strip() for l in dic.read_text(encoding="utf-8").splitlines() if l.startswith("| ") and not l.startswith("| Field")}
    for folder in ["requirements/data-model", "requirements/api"]:
        for md in (DOCS / folder).rglob("*.md"):
            if md.name in {"INDEX.md", "field-dictionary.md"}:
                continue
            for line in md.read_text(encoding="utf-8").splitlines():
                if line.startswith("| ") and not line.startswith(("| Field", "| Code", "| Path", "|---")):
                    name = line.split("|")[1].strip().strip("`")
                    if re.fullmatch(r"[a-z][a-z0-9_]*", name) and name not in known:
                        warnings.append(f"{md.relative_to(ROOT)}: field '{name}' not in field-dictionary.md")


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


if __name__ == "__main__":
    check_status_drift()
    check_vul_evidence()
    check_skills(); check_indexes(); check_references(collect_ids()); check_field_dictionary(); check_vul_register()
    for w in warnings: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)
