"""Leaf: what an agent needs before it edits code inside an isolation (`aix code isolations --context PATH|NAME`):
where the code sits, how deep it may reach into the other isolations and which files to read for that (only what
their frontiers let through, never their internals: less to read, nothing to copy from), its own frontiers and the
contract it keeps, and the data that may not pass through it. Everything the frontiers do not limit is allowed. Read first, edit second: the rules are not discovered by the gate
after the fact."""
import sys

from codefiles import ROOT, rel
import isogov

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


def _limited_lines(d, name: str, files: list) -> list:
    """The other isolations whose frontiers limit this code, each with the only files it may reach (and read)."""
    reachable = isogov.reachable_files(d, files)
    others = [n for n in sorted(reachable) if not d.is_within(name, n)]
    out = [f"    {n}: {_files(reachable[n])}" for n in others]
    return out or ["    none: no other isolation has an accepted frontier"]


def _family_lines(d, name: str) -> list:
    iso, out = d.isos[name], []
    if iso.parent:
        out.append(f"  inside `{iso.parent}`: its own files are yours to use")
    for child in d.children(name):
        part = d.isos[child]
        out.append(f"  part `{child}`: " + (f"reach {_reach(part)}" if part.limited else "every file is usable from here"))
    return out


def _reach(iso) -> str:
    deeper = ", ".join(f"`{f}`" for f in iso.accepted() if f != ".")
    return f"its top level and down to {deeper}" if deeper else "its top level only"


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
    lines = [f"Isolation {head}", f"  holds: {_files(iso.paths)}",
             "  limited by their frontiers (use, and read, only these files of them):", *_limited_lines(d, name, files),
             "  every other isolation is open: no frontier limits it"]
    lines += _family_lines(d, name)
    if iso.limited:
        lines.append(f"  its frontiers: outsiders reach {_reach(iso)}; the public names there are its contract (a removed or changed one is BREAKING)")
    if iso.pending():
        lines.append(f"  pending frontiers (proposed, not in force): {', '.join(iso.pending())}")
    lines += _data_lines(d, name)
    return lines


def main(arg: str, d, files: list):
    names = _target(arg, d, files)
    if not names:
        sys.exit(f"`{arg}` is no isolation and no file of one; isolations: {', '.join(sorted(d.isos))}")
    for i, name in enumerate(names):
        print(("\n" if i else "") + "\n".join(describe(d, name, files)))
    print("\nReaching deeper than a frontier fails `aix code isolations --gate`; opening a frontier is a person's decision (--review, ADR).")
