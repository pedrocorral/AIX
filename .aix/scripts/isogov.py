"""Leaf: who decided the isolation rules, and the contracts they promised. The declaration and the recorded contracts
are fingerprinted (isodecl.fingerprint); an accepted ADR carries that fingerprint in its front matter
(`isolations: sha256:...`). When the fingerprint of the files no longer matches the newest ADR that carries one,
the rules changed without a decision: an agent cannot widen its own rules and pass. `--accept` records the contracts
and writes a *proposed* ADR with the new fingerprint, the declaration and what changed; a person accepts it.

Contracts: the public names of every file outsiders may reach through an isolation's accepted frontiers
(isosurface), recorded per isolation in
docs/requirements/isolations.contracts.json. A recorded name removed or changed incompatibly is a BREAKING change;
a name not recorded yet is an addition, free until the next accept. CODEOWNERS: each isolation's `owner` on its
paths, and the declaration, the contracts and the decisions folder on `owners: {rules: ...}`."""
import datetime, json, re
from pathlib import Path

from codefiles import EXT, ROOT
from isodecl import CONTRACTS, DECL, fingerprint, read_contracts
from isosurface import breaking, surface

DECISIONS = "docs/requirements/decisions"
ADR_KEY = re.compile(r"^isolations:\s*(sha256:[0-9a-f]+)\s*$", re.M)
STATUS = re.compile(r"^status:\s*(\w+)", re.M)
OWNERS_BEGIN, OWNERS_END = "# aix isolations: begin (aix code isolations --codeowners --write; edit the declaration, not this block)", "# aix isolations: end"


# ---- the ADRs that carry a fingerprint ----------------------------------------------------------------------------

def adrs(root: Path = ROOT) -> list:
    """(number, file, status, fingerprint) of every ADR whose front matter carries `isolations:`, oldest first."""
    out = []
    for f in sorted((root / DECISIONS).glob("ADR-*.md")):
        head = f.read_text(encoding="utf-8", errors="replace").split("\n---", 2)[0]
        m, num = ADR_KEY.search(head), re.match(r"ADR-(\d+)", f.name)
        if m and num:
            st = STATUS.search(head)
            out.append((int(num.group(1)), f, st.group(1).lower() if st else "proposed", m.group(1)))
    return sorted(out)


def governance(raw: dict, root: Path = ROOT) -> tuple:
    """(ok, message): does the newest ADR carrying a fingerprint accept the declaration and contracts as they are?"""
    now = fingerprint(raw, read_contracts(root))
    found = adrs(root)
    accepted = [a for a in found if a[2] == "accepted"]
    pending = [a for a in found if a[3] == now and a[2] != "accepted"]
    if accepted and accepted[-1][3] == now:
        return True, f"accepted by {accepted[-1][1].name} ({now})"
    if pending:
        return False, f"{pending[-1][1].name} records these rules ({now}) but is `{pending[-1][2]}`: a person accepts it (status: accepted)"
    if accepted:
        return False, (f"the rules changed after {accepted[-1][1].name} accepted {accepted[-1][3]}; now {now}. "
                       "Record the decision: `aix code isolations --accept` writes the ADR for a person to accept")
    return False, f"no accepted ADR carries `isolations: {now}`: `aix code isolations --accept` writes one for a person to accept"


# ---- contracts ----------------------------------------------------------------------------------------------------

def reachable_files(d, files: list) -> dict:
    """isolation -> the files outsiders may reach, for the isolations an accepted frontier limits (the others have no
    contract: everything in them is reachable and nothing is promised)."""
    return {n: sorted(f for f in files if d.is_within(d.owner_of(f) or "", n) and iso.reachable(f))
            for n, iso in sorted(d.isos.items()) if iso.limited}


def snapshot(d, files: list, root: Path = ROOT) -> dict:
    """isolation -> file -> name -> signature: the contracts as the code has them now."""
    return {n: {f: surface(root / f) for f in fs} for n, fs in reachable_files(d, files).items()}


def contract_changes(d, files: list, root: Path = ROOT) -> tuple:
    """(breaking, additions): [(isolation, file, name, what)] against the recorded contracts, and how many names
    the reachable files carry that are not recorded yet."""
    recorded, now = read_contracts(root), snapshot(d, files, root)
    broken, added = [], 0
    for iso, per_file in sorted(recorded.items()):
        for f, names in sorted(per_file.items()):
            current = now.get(iso, {}).get(f, surface(root / f) if (root / f).exists() else {})
            broken += [(iso, f, name, what) for name, what in breaking(names, current, EXT.get(Path(f).suffix, ""))]
    for iso, per_file in now.items():
        added += sum(len(set(names) - set(recorded.get(iso, {}).get(f, {}))) for f, names in per_file.items())
    return broken, added


# ---- --accept: record the contracts, propose the ADR ----------------------------------------------------------------

def _next_adr_number(root: Path) -> int:
    nums = [int(m.group(1)) for f in (root / DECISIONS).glob("ADR-*.md") if (m := re.match(r"ADR-(\d+)", f.name))]
    return max(nums, default=0) + 1


def _old_isolations(text: str) -> dict:
    from yamlmini import parse_tree
    try:
        return parse_tree(text).get("isolations") or {}
    except ValueError:
        return {}


def _changes(old_text: str, new_raw: dict) -> list:
    """What changed in the declaration since the last ADR, line by line: isolations and permissions."""
    old, new = _old_isolations(old_text), new_raw.get("isolations") or {}
    lines = [f"- new isolation `{n}`" for n in sorted(set(new) - set(old))] + [f"- isolation `{n}` removed" for n in sorted(set(old) - set(new))]
    for n in sorted(set(new) & set(old)):
        before, after = old[n] or {}, new[n] or {}
        lines += [f"- `{n}` {key}: {before.get(key)} -> {after.get(key)}" for key in ("paths", "frontiers") if before.get(key) != after.get(key)]
    return lines


def _previous_declaration(root: Path) -> str:
    """The declaration text the newest accepted ADR recorded, else ''."""
    accepted = [a for a in adrs(root) if a[2] == "accepted"]
    if not accepted:
        return ""
    m = re.search(r"```yaml\n(.*?)```", accepted[-1][1].read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


def write_adr(raw: dict, broken: list, root: Path = ROOT) -> Path:
    """A proposed ADR carrying the fingerprint of the declaration and the contracts as recorded now."""
    num, today = _next_adr_number(root), datetime.date.today().isoformat()
    fid = f"ADR-{num:04d}"
    path = root / DECISIONS / f"{fid}-isolations.md"
    text = (root / DECL).read_text(encoding="utf-8")
    changes = _changes(_previous_declaration(root), raw) or ["- first declaration of the isolations"]
    breaks = [f"- `{iso}` {f}: `{name}` {what}" for iso, f, name, what in broken] or ["- none"]
    body = [
        "---", f"id: {fid}", "title: Isolation rules and contracts", "status: proposed   # a person sets accepted; an agent never does",
        f"date: {today}", "supersedes: []", f"affects: [{DECL}, {CONTRACTS}]", f"isolations: {fingerprint(raw, read_contracts(root))}", "---",
        f"# {fid} — Isolation rules and contracts", "", "## Context",
        "The isolation declaration or the recorded contracts changed. `aix code isolations --gate` fails until an accepted ADR",
        "carries their fingerprint, so a change to who may use whom is a decision, never a side effect.", "",
        "## Changes since the last accepted ADR", *changes, "", "## Breaking contract changes accepted", *breaks, "",
        "## Decision", "Accept the declaration below and the contracts recorded in "
        f"`{CONTRACTS}`.", "", "```yaml", text.rstrip("\n"), "```", "",
        "## Consequences", "- Code that uses an isolation it may not use, or a file an isolation does not expose, fails the gate.", "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    _index_row(root / DECISIONS / "INDEX.md", f"| `{path.name}` | Isolation rules and contracts ({fingerprint(raw, read_contracts(root))}) | proposed |")
    return path


def write_contracts(contracts: dict, root: Path = ROOT) -> Path:
    path = root / CONTRACTS
    path.write_text(json.dumps(contracts, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    _index_row(root / "docs" / "requirements" / "INDEX.md",
               "| `isolations.contracts.json` | The recorded contracts of the isolations (generated by `aix code isolations --accept`) | Changing a file outsiders reach |")
    return path


def _index_row(index: Path, row: str):
    """Append a row to a folder INDEX table unless the file it names is listed already."""
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    name = re.search(r"`([^`]+)`", row).group(1)
    if name not in text:
        index.write_text(text.rstrip("\n") + "\n" + row + "\n", encoding="utf-8")


def declaration_index_row(root: Path = ROOT):
    _index_row(root / "docs" / "requirements" / "INDEX.md",
               "| `isolations.yaml` | The isolations: named parts of the code and their frontiers, how deep outsiders reach (`aix code isolations`) | Before an import across parts |")


# ---- CODEOWNERS ---------------------------------------------------------------------------------------------------

def _owner_pattern(glob: str) -> str:
    """A declaration glob as a CODEOWNERS pattern (rooted): `src/orders/**` -> `/src/orders/`."""
    g = glob.strip().removeprefix("./")
    g = g[:-3] + "/" if g.endswith("/**") else g
    return "/" + g


def codeowners(d) -> list:
    """The CODEOWNERS lines of the declaration: isolations in name order (a part after its parent, so it wins)."""
    lines = []
    for n in sorted(d.isos, key=lambda x: (x.count("."), x)):
        owner = d.isos[n].owner
        lines += [f"{_owner_pattern(g)} {owner}" for g in d.isos[n].paths] if owner else []
    rules = (d.raw.get("owners") or {}).get("rules") if isinstance(d.raw.get("owners"), dict) else None
    if rules:
        lines += [f"/{DECL} {rules}", f"/{CONTRACTS} {rules}", f"/{DECISIONS}/ {rules}"]
    return lines


def write_codeowners(lines: list, root: Path = ROOT) -> Path:
    """The managed block in the project's CODEOWNERS (.github/, root or docs/, the existing one first)."""
    path = next((root / p for p in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS") if (root / p).exists()), root / ".github" / "CODEOWNERS")
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    block = "\n".join([OWNERS_BEGIN, *lines, OWNERS_END])
    pattern = re.compile(re.escape(OWNERS_BEGIN) + r".*?" + re.escape(OWNERS_END), re.S)
    new = pattern.sub(lambda _m: block, old) if pattern.search(old) else (old.rstrip("\n") + "\n\n" if old.strip() else "") + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return path
