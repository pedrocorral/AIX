#!/usr/bin/env python3
"""aix code isolations — the parts of the code (isolations), how deep code outside each may reach into it (its
frontiers), and whether the code keeps to it. The declaration is docs/requirements/isolations.yaml (isodecl); an accepted ADR carries its
fingerprint (isogov), so a person, not an agent, decides every change to the rules.

  (no option)      check: the declaration, its governance, frontiers waiting for a decision (PENDING), every
                   import edge deeper than a frontier allows (HIDDEN), files in no isolation (UNDECLARED), contracts
                   (BREAKING), data boundaries (DATA); then what to tighten. Everything the frontiers do not limit is
                   allowed.
  --gate           exit 1 on any finding above (the recommendations never fail)
  --propose        the isolations AIX recommends from the code (isopropose), every frontier proposed; --depth 2
                   adds parts; --write saves them as the declaration when there is none (--force replaces one), or
                   merges new frontier suggestions into the existing one (decided frontiers are never touched)
  --review         accept or reject each proposed frontier, one by one (a terminal checklist; a person's act)
  --accept         record the contracts and write the ADR (status proposed) a person accepts
  --context X      for an agent before it edits: the isolation of a path or name, how deep it may reach into the
                   others and the only files of them to read, its frontiers and the contract it keeps
  --codeowners     the CODEOWNERS lines of the declaration; --write puts them in the managed block
  --requirements   requirements mapped onto isolations (@implements markers): scattered and mixed ones
  --report         also write docs/tests/isolations.md"""
import sys

import isodecl, isogov, isorules
from codefiles import ROOT, default_roots
from depedges import module_graph
from graphmetrics import is_test
from guard import checked

USAGE = ("usage: aix code isolations [PATH...] [--gate] [--report] | --propose [--depth N] [--write [--force]] | --review | --accept "
         "| --context PATH|NAME | --codeowners [--write] | --requirements")
SHOWN = 25   # findings of one kind printed before "... and N more"


class _Options:
    def __init__(self, args):
        args = list(args)
        flags = {"--gate", "--report", "--propose", "--write", "--force", "--review", "--accept", "--codeowners", "--requirements"}
        self.flag = {f: f in args for f in flags}
        self.depth = int(_take(args, "--depth", 1))
        self.context = _take(args, "--context", None)
        self.paths = [a for a in args if not a.startswith("--")] or default_roots()


def _take(args: list, flag: str, default):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1] if i + 1 < len(args) else default
        del args[i:i + 2]
        return value
    return default


def _graph(paths: list) -> tuple:
    """(files, edges): the module graph without Rust's `mod x;` declarations (declaring a module is not using it)."""
    nodes, edges = module_graph(paths, ownership=False)
    return sorted(nodes), edges


def _load_or_exit():
    d = isodecl.load(ROOT)
    if d is None:
        sys.exit(f"no {isodecl.DECL}: `aix code isolations --propose` drafts one from the code (--write saves it)")
    return d


# ---- check ----------------------------------------------------------------------------------------------------------

class _Check:
    """Every finding of one run, by kind."""
    KINDS = ("DECLARATION", "GOVERNANCE", "PENDING", "HIDDEN", "UNDECLARED", "BREAKING", "DATA")

    def __init__(self, d, files: list, edges: set):
        self.d, self.files, self.edges = d, files, edges
        self.checked = [f for f in files if d.tests_checked or not is_test(f)]
        self.found = {k: [] for k in self.KINDS}

    def run(self):
        isodecl.check_files(self.d, self.checked)
        ok, why = isogov.governance(self.d.raw, ROOT)
        self.governance = why
        self.found["GOVERNANCE"] += [] if ok else [why]
        self.found["PENDING"] = [f"`{n}` frontier `{f}` is proposed, not in force: `--review` accepts or rejects it" for n, f in isorules.pending_frontiers(self.d)]
        self._edges()
        self.found["UNDECLARED"] = [f"{f} is in no isolation" for f in self.checked if self.d.owner_of(f) is None]
        self.broken, self.added = isogov.contract_changes(self.d, self.checked, ROOT)
        self.found["BREAKING"] = [f"`{iso}` {f}: `{name}` {what} (callers break; --accept with an ADR if intended)" for iso, f, name, what in self.broken]
        import isodata
        data = isodata.outside(self.d, self.checked, ROOT) + isodata.sinks(self.d, self.checked, ROOT)
        self.found["DATA"] = [f"{f}:{line}  {msg}" for f, line, msg in sorted(data)]
        self.found["DECLARATION"] = list(dict.fromkeys(self.d.errors))
        return self

    def _edges(self):
        for a, b in sorted(self.edges):
            if not self.d.tests_checked and (is_test(a) or is_test(b)):
                continue
            v = isorules.judge(self.d, a, b)
            if v:
                self.found[v.kind].append(f"{a} -> {b}  ({v.owner_a} -> {v.owner_b}): {v.message}")

    def failures(self) -> int:
        return sum(len(v) for v in self.found.values())


def _recommendations(c: _Check) -> list:
    out = [f"  unused frontier    `{n}` opens `{f}` and nothing outside reaches that deep: a shallower frontier is stronger" for n, f in isorules.unused_frontiers(c.d, c.edges)]
    if c.added:
        out.append(f"  contracts          {c.added} reachable name(s) not recorded yet: `--accept` records them (an ADR)")
    out += [f"  warning            {w}" for w in dict.fromkeys(c.d.warnings)]
    return out


def render(c: _Check) -> str:
    d = c.d
    lines = [f"Isolations — {isodecl.DECL}: {len(d.isos)} isolation(s), {len(c.checked)} file(s), {len(c.edges)} import edge(s)", ""]
    lines.append(f"  governance: {c.governance}")
    for kind in _Check.KINDS:
        items = c.found[kind] if kind != "GOVERNANCE" else []
        lines += [f"  {kind:<12} {x}" for x in items[:SHOWN]] + ([f"  {kind:<12} ... and {len(items) - SHOWN} more"] if len(items) > SHOWN else [])
    counts = ", ".join(f"{k.lower()} {len(c.found[k])}" for k in _Check.KINDS)
    lines += ["", f"  findings: {counts}"]
    rec = _recommendations(c)
    if rec:
        lines += ["", "  TIGHTEN (never fails; each line makes the rules stricter):", *rec]
    lines += ["", "  fix an edge: move the code, invert the dependency, or go through a file the frontiers let through (skill refactor-cycle);",
              "  never open a frontier to pass: a wider rule is a person's decision (--review, then the ADR via --accept)."]
    return "\n".join(lines)


def check(o: _Options):
    d = isodecl.load(ROOT)
    if d is None:
        print(f"no isolations declared ({isodecl.DECL}): nothing to check. `aix code isolations --propose` drafts them from the code.")
        if o.flag["--gate"]:
            print("GATE PASSED (nothing declared)")
        return
    files, edges = _graph(o.paths)
    c = _Check(d, files, edges).run()
    text = render(c)
    print(text)
    if o.flag["--report"]:
        out = ROOT / "docs" / "tests" / "isolations.md"
        out.write_text("# Isolations (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if o.flag["--gate"]:
        if c.failures():
            sys.exit(f"GATE FAILED: {c.failures()} finding(s)")
        print("GATE PASSED")


# ---- propose, accept, codeowners, requirements ------------------------------------------------------------------

def propose(o: _Options):
    import isopropose
    files, edges = _graph(o.paths)
    target = ROOT / isodecl.DECL
    if target.exists() and o.flag["--write"] and not o.flag["--force"]:
        return _merge_suggestions(files, edges)
    decl, evidence = isopropose.propose([r for r in o.paths], files, edges, o.depth)
    text = isopropose.to_yaml(decl, evidence)
    if not o.flag["--write"]:
        print(text, end="")
        print(f"\n# {len(decl['isolations'])} isolation(s). --write saves it as {isodecl.DECL}.")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    isogov.declaration_index_row(ROOT)
    print(f"wrote {isodecl.DECL}: {len(decl['isolations'])} isolation(s), every frontier proposed")
    print("next: `aix code isolations --review` (accept or reject each frontier), then `--accept` (contracts + the ADR)")


def _merge_suggestions(files: list, edges: set):
    """An existing declaration: add the frontiers the code suggests today as proposed; decided ones stay as they are."""
    import isoedit
    d = _load_or_exit()
    new = _new_suggestions(d, files, edges)
    if not new:
        return print("no new frontier to suggest: every one the code suggests is declared already")
    target = ROOT / isodecl.DECL
    target.write_text(isoedit.with_frontiers(target.read_text(encoding="utf-8"), d.raw, new), encoding="utf-8")
    print(f"added {len(new)} proposed frontier(s) to {isodecl.DECL}: " + ", ".join(f"{n} {f}" for n, f in sorted(new)))
    print("next: `aix code isolations --review`")


def _new_suggestions(d, files: list, edges: set) -> dict:
    """{(isolation, frontier): "proposed"} for what the code suggests today and the declaration does not name yet."""
    import isopropose
    code = {e for e in edges if not is_test(e[0]) and not is_test(e[1])}
    suggested = isopropose.frontier_suggestions({f: d.owner_of(f) for f in files}, code, {n: iso.base for n, iso in d.isos.items()})
    return {(n, f): "proposed" for n, fs in suggested.items() for f in fs if f not in d.isos[n].frontiers}


def review(o: _Options):
    """Accept or reject each proposed frontier in a terminal; without one, print them and change nothing."""
    import codefind, isoedit, isoreview
    d = _load_or_exit()
    files, edges = _graph(o.paths)
    rows = isoreview.rows(d, edges)
    if not rows:
        return print("no proposed frontier: nothing to review")
    if not codefind._interactive():
        return isoreview.print_pending(rows)
    chosen = codefind.checklist(rows, "Frontiers: checked = accepted, unchecked = rejected", isoreview.describe, footer=isodecl.DECL)
    changes = isoreview.decisions(rows, chosen)
    if not changes:
        return print("cancelled: every frontier stays proposed")
    target = ROOT / isodecl.DECL
    target.write_text(isoedit.with_frontiers(target.read_text(encoding="utf-8"), d.raw, changes), encoding="utf-8")
    accepted = sum(s == "accepted" for s in changes.values())
    print(f"{accepted} frontier(s) accepted, {len(changes) - accepted} rejected in {isodecl.DECL}")
    print("the rules changed: `aix code isolations --accept` records them in the ADR a person accepts")


def accept(o: _Options):
    d = _load_or_exit()
    files, _edges = _graph(o.paths)
    checked = [f for f in files if d.tests_checked or not is_test(f)]
    isodecl.check_files(d, checked)
    if d.errors:
        sys.exit("the declaration has errors; fix them first:\n  " + "\n  ".join(dict.fromkeys(d.errors)))
    broken, _added = isogov.contract_changes(d, checked, ROOT)
    contracts = isogov.snapshot(d, checked, ROOT)
    same = [a for a in isogov.adrs(ROOT) if a[3] == isodecl.fingerprint(d.raw, contracts)]
    if same:
        state = "already carries" if same[-1][2] == "accepted" else f"carries, `{same[-1][2]}`, waiting for a person to accept,"
        print(f"nothing to accept: {same[-1][1].name} {state} these rules and contracts")
        return
    isogov.write_contracts(contracts, ROOT)
    adr = isogov.write_adr(d.raw, broken, ROOT)
    print(f"recorded the contracts in {isodecl.CONTRACTS}; wrote {adr.relative_to(ROOT)} (status: proposed)")
    print(f"fingerprint {isodecl.fingerprint(d.raw, contracts)}; a person reviews the ADR and sets `status: accepted` (an agent never does)")


def owners(o: _Options):
    d = _load_or_exit()
    lines = isogov.codeowners(d)
    if not lines:
        sys.exit("no isolation names an `owner:` (and no `owners: {rules: ...}`): nothing to write")
    if o.flag["--write"]:
        print(f"wrote the managed block of {isogov.write_codeowners(lines, ROOT).relative_to(ROOT)} ({len(lines)} line(s))")
    else:
        print("\n".join(lines))


def requirements(o: _Options):
    import isotrace
    d = _load_or_exit()
    files, _edges = _graph(o.paths)
    req_isos, iso_reqs = isotrace.trace(d, files, ROOT)
    print(f"Requirements by isolation (@implements markers): {len(req_isos)} requirement(s)")
    for req, isos in req_isos.items():
        print(f"  {req:<18} {', '.join(isos) or '(code in no isolation)'}")
    advice = isotrace.advice(req_isos, iso_reqs)
    print("\n" + ("\n".join("  " + a for a in advice) if advice else "  no requirement is scattered and no isolation mixes domains"))


@checked
def main(args: list):
    o = _Options(args)
    if o.context:
        import isocontext
        return isocontext.main(o.context, _load_or_exit(), _graph(o.paths)[0])
    modes = {"--propose": propose, "--review": review, "--accept": accept, "--codeowners": owners, "--requirements": requirements}
    mode = next((m for m in modes if o.flag[m]), None)
    return modes[mode](o) if mode else check(o)


if __name__ == "__main__":
    main(sys.argv[1:])
