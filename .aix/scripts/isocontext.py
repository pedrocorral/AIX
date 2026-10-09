"""Leaf: what an agent needs before it edits code inside an isolation (`aix code isolations --context PATH|NAME`):
where the code sits, what it may use and which files to read for that (only the exposed files of the isolations
it may use, never their internals: less to read, nothing to copy from), what it must not touch, the contract it
keeps, and the data that may not pass through it. Read first, edit second: the rules are not discovered by the gate
after the fact."""
import sys

from codefiles import ROOT, rel
import isogov, isorules

LIST = 12   # files listed per isolation before "... N more"


def _target(arg: str, d, files: list) -> list:
    """The isolations an argument names: an isolation name, a file, or a folder (every isolation holding a file in it)."""
    if arg in d.isos:
        return [arg]
    path = (ROOT / arg).resolve()
    if path.is_file():
        owner = d.owner_of(rel(path))
        return [owner] if owner else []
    inside = rel(path).rstrip("/") + "/"
    return sorted({d.owner_of(f) for f in files if f.startswith(inside)} - {None})


def _files(names: list) -> str:
    shown = names[:LIST]
    return ", ".join(shown) + (f" ... and {len(names) - LIST} more" if len(names) > LIST else "")


def _may_use_lines(d, name: str, files: list) -> list:
    exposed = isogov.exposed_files(d, files)
    out = []
    for target in d.effective_may_use(name):
        if target not in d.isos:
            continue
        what = _files(exposed[target]) if target in exposed else "every file (it declares no `exposes`)"
        out.append(f"    {target}: {what}")
    return out or ["    nothing outside itself"]


def _family_lines(d, name: str) -> list:
    iso, out = d.isos[name], []
    if iso.parent:
        out.append(f"  inside `{iso.parent}`: its own files are yours to use; siblings "
                   + ("are free (no part declares may_use)" if all(d.isos[s].may_use is None for s in d.children(iso.parent)) else "follow each part's may_use"))
    for child in d.children(name):
        exp = d.isos[child].exposes
        out.append(f"  part `{child}`: " + ("every file is usable from here" if exp is None else f"use only {_files(exp) or 'nothing'}"))
    return out


def _data_lines(d, name: str) -> list:
    import isodata
    out = []
    for kind, fields, stays, sinks in isodata.rules(d):
        if stays and not any(d.is_within(name, s) for s in stays):
            out.append(f"  data: {kind} ({', '.join(fields)}) must not appear here: it stays in {', '.join(stays)}")
        out.append(f"  data: {kind} fields never reach {', '.join(sinks)}")
    return out


def describe(d, name: str, files: list) -> list:
    iso = d.isos[name]
    head = f"`{name}`" + (f" — {iso.description}" if iso.description else "") + (f"  (owner {iso.owner})" if iso.owner else "")
    lines = [f"Isolation {head}", f"  holds: {_files(iso.paths)}", "  may use (read only these files of them):", *_may_use_lines(d, name, files)]
    lines += _family_lines(d, name)
    forbidden = isorules.forbidden_targets(d, name)
    lines.append("  must not use: " + (", ".join(forbidden) if forbidden else "nothing else is declared"))
    if iso.exposes is not None:
        lines.append(f"  its contract (callers depend on it; a removed or changed name is BREAKING): {_files(iso.exposes) or 'nothing exposed'}")
    lines += _data_lines(d, name)
    return lines


def main(arg: str, d, files: list):
    names = _target(arg, d, files)
    if not names:
        sys.exit(f"`{arg}` is no isolation and no file of one; isolations: {', '.join(sorted(d.isos))}")
    for i, name in enumerate(names):
        print(("\n" if i else "") + "\n".join(describe(d, name, files)))
    print("\nA new use of something outside this list fails `aix code isolations --gate`; widening the list is a person's decision (ADR).")
