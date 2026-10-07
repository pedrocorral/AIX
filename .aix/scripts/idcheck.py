"""Leaf: is a token an id of the scheme (conventions/ids-and-traceability.md), and if not, why. Every id written
in the docs' front matter, in `covers:`/`affects:` lists, in code markers (`@implements`, `@tests`, `@mitigates`) and
in document bodies is checked against the shape of its prefix; a domain code must be one the glossary defines; a
file is named after its id; an id is defined once. Agents invent shapes (`TS-VUL-WEB-002`, `TS-AUTH-7`, `ts-auth-001`,
`TEST-AUTH-001`, `VULN-INJ-1`): each is reported with the rule it breaks and the nearest correct form."""
import re
from typing import Optional
from pathlib import Path

NFR_CATS = ("PERF", "SEC", "A11Y", "OBS", "OPS", "DATA", "UX")
VUL_CATS = ("INJ", "AUTHN", "AUTHZ", "INPUT", "SECRET", "DEP", "WEB", "DATA", "LOG", "AI", "INFRA")
SHAPES = {"FR": "FR-<DOMAIN>-NNN", "NFR": "NFR-<CAT>-NNN", "API": "API-<DOMAIN>-NNN", "DM": "DM-<Entity>", "ADR": "ADR-NNNN", "TS": "TS-<DOMAIN>-NNN",
          "VUL": "VUL-<CAT>-NNN", "TASK": "TASK-NNNN", "CONFLICT": "CONFLICT-NNNN"}
SUSPECT = ("TEST", "TC", "VULN", "REQ", "DECISION")   # prefixes agents reach for instead of the scheme's
PREFIXES = "|".join(SHAPES)
LOOKS_LIKE = re.compile(r"(?<![\w/.])(?:(?:" + PREFIXES + "|" + "|".join(SUSPECT) + r")[-_][\w*-]*|(?:" + PREFIXES.lower() + r")[-_][a-z0-9]+[-_]\d+[\w-]*)")   # a token an agent meant as an id (`TS-*` keeps its star: a placeholder)
TITLE_TAIL = re.compile(r"^((?:[A-Za-z]+-)+\d{3,4})-[a-z][\w-]*$")   # `TS-SEC-001-release-gate`: an id followed by its file title
PLACEHOLDER = re.compile(r"NNN|<|>|\bid\b|\bXXX\b|\.\.\.|\*", re.I)
MARK = re.compile(r"@(implements|tests|mitigates)\s+([^\n]*)")
GLOSSARY_ROW = re.compile(r"^\|[^|]*\|[^|]*\|\s*([A-Z][A-Z0-9]{0,7})\s*\|", re.M)


def domain_codes(root: Path) -> set:
    """The glossary's 'Domain code' column; empty when the project has no glossary table yet (shape only then)."""
    g = root / "docs" / "requirements" / "product" / "glossary.md"
    if not g.exists():
        return set()
    text = g.read_text(encoding="utf-8", errors="replace")
    return {m.group(1) for m in GLOSSARY_ROW.finditer(text)} - {"Domain"}


def reason(token: str, domains: set):
    """None when `token` is an id of the scheme, else one sentence: the rule broken and the nearest correct form."""
    if "_" in token and token.replace("_", "-").split("-")[0].upper() in SHAPES:
        return f"`{token}`: ids use hyphens, never underscores (`{token.replace('_', '-').upper()}`)"
    parts = token.split("-")
    prefix = parts[0]
    if prefix not in SHAPES:
        if prefix.upper() in SHAPES:
            return f"`{token}`: ids are uppercase (`{token.upper()}`)"
        return f"`{token}`: `{prefix}` is no prefix of the scheme ({', '.join(SHAPES)}): a test spec is `TS-<DOMAIN>-NNN`, a vulnerability `VUL-<CAT>-NNN`"
    checker = {"ADR": _numbered, "TASK": _numbered, "CONFLICT": _numbered, "DM": _entity, "NFR": _categorised, "VUL": _categorised}.get(prefix, _domained)
    return checker(token, parts, domains)


def _numbered(token: str, parts: list, _domains) -> Optional[str]:
    if len(parts) == 2 and re.fullmatch(r"\d{4}", parts[1]):
        return None
    return f"`{token}` is not `{SHAPES[parts[0]]}`: one block of exactly four digits (`{parts[0]}-{(parts[-1] if parts[-1].isdigit() else '1').zfill(4)[-4:]}`)"


def _entity(token: str, parts: list, _domains) -> Optional[str]:
    return None if len(parts) == 2 and re.fullmatch(r"[A-Z][A-Za-z0-9]*", parts[1]) else f"`{token}` is not `DM-<Entity>`: one PascalCase entity name (`DM-User`)"


def _categorised(token: str, parts: list, _domains) -> Optional[str]:
    cats = NFR_CATS if parts[0] == "NFR" else VUL_CATS
    if len(parts) == 3 and parts[1] in cats and re.fullmatch(r"\d{3}", parts[2]):
        return None
    if len(parts) == 3 and parts[1] in cats:
        return f"`{token}` is not `{SHAPES[parts[0]]}`: exactly three digits (`{parts[0]}-{parts[1]}-{parts[2].zfill(3)[-3:] if parts[2].isdigit() else '001'}`)"
    return f"`{token}` is not `{SHAPES[parts[0]]}`: CAT is one of {', '.join(cats)} and the number has three digits"


def _domained(token: str, parts: list, domains: set) -> Optional[str]:
    prefix = parts[0]
    if len(parts) != 3:
        return f"`{token}` is not `{SHAPES[prefix]}`: three parts, prefix, one domain code, three digits{_vul_hint(parts)}"
    domain, number = parts[1], parts[2]
    if not re.fullmatch(r"[A-Z][A-Z0-9]{0,7}", domain):
        return f"`{token}` is not `{SHAPES[prefix]}`: the domain code is uppercase, at most 8 characters"
    if not _known_domain(prefix, domain, domains):
        return f"`{token}`: `{domain}` is not a domain code of the glossary ({', '.join(sorted(domains))}) nor, for a TS, an NFR category ({', '.join(NFR_CATS)}); add it to the glossary or use one of them"
    if not re.fullmatch(r"\d{3}", number):
        return f"`{token}` is not `{SHAPES[prefix]}`: exactly three digits (`{prefix}-{domain}-{number.zfill(3)[-3:] if number.isdigit() else '001'}`)"
    return None


def _vul_hint(parts: list) -> str:
    """`TS-VUL-WEB-002`: a test spec for a vulnerability names the vulnerability in `covers:`."""
    if parts[0] == "TS" and len(parts) == 4 and parts[1] == "VUL":
        return f"; a test spec for a vulnerability takes the domain of what it tests and names the vulnerability in `covers: [{'-'.join(parts[1:])}]`"
    return ""


def _known_domain(prefix: str, domain: str, domains: set) -> bool:
    """No glossary table yet: any shape; else a glossary code, or an NFR category for a non-functional spec."""
    return not domains or domain in domains or (prefix == "TS" and domain in NFR_CATS)


def tokens_in(text: str, prose: bool = False) -> list:
    """Every token of a text an agent meant as an id, placeholders of the templates left out, an id's file title cut
    off. In prose (`prose=True`) only tokens that carry a number count: `VUL` or `TS-SEC` name a family, not an id."""
    out = []
    for m in LOOKS_LIKE.finditer(text):
        token = m.group(0).rstrip("-_")
        tail = TITLE_TAIL.match(token)
        token = tail.group(1) if tail else token
        if PLACEHOLDER.search(token) or (prose and not re.search(r"\d", token)):
            continue
        out.append(token)
    return out
