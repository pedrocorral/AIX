#!/usr/bin/env python3
"""aix code isolations — the parts of the code (isolations), who may use whom, what each exposes, and whether the
code keeps to it. The declaration is docs/requirements/isolations.yaml (isodecl); an accepted ADR carries its
fingerprint (isogov), so a person, not an agent, decides every change to the rules.

  (no option)      check: the declaration, its governance, every import edge (FORBIDDEN, HIDDEN), files in no
                   isolation (UNDECLARED), contracts (BREAKING), data boundaries (DATA); then what to tighten
  --gate           exit 1 on any finding above (the recommendations never fail)
  --propose        the isolations AIX recommends from the code (isopropose); --depth 2 adds parts; --write saves
                   them as the declaration when there is none (--force replaces one)
  --accept         record the contracts and write the ADR (status proposed) a person accepts
  --context X      for an agent before it edits: the isolation of a path or name, what it may use and the files
                   to read for it, what it must not touch, the contract it keeps
  --codeowners     the CODEOWNERS lines of the declaration; --write puts them in the managed block
  --requirements   requirements mapped onto isolations (@implements markers): scattered and mixed ones
  --report         also write docs/tests/isolations.md"""
import sys

import isodecl, isogov, isorules
from codefiles import ROOT, default_roots
from depedges import module_graph
from graphmetrics import is_test
from guard import checked

USAGE = ("usage: aix code isolations [PATH...] [--gate] [--report] | --propose [--depth N] [--write [--force]] | --accept "
         "| --context PATH|NAME | --codeowners [--write] | --requirements")
SHOWN = 25   # findings of one kind printed before "... and N more"


class _Options:
    def __init__(self, args):
        args = list(args)
        flags = {"--gate", "--report", "--propose", "--write", "--force", "--accept", "--codeowners", "--requirements"}
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
    KINDS = ("DECLARATION", "GOVERNANCE", "FORBIDDEN", "HIDDEN", "UNDECLARED", "BREAKING", "DATA")

    def __init__(self, d, files: list, edges: set):
        self.d, self.files, self.edges = d, files, edges
        self.checked = [f for f in files if d.tests_checked or not is_test(f)]
        self.found = {k: [] for k in self.KINDS}

    def run(self):
        isodecl.check_files(self.d, self.checked)
        ok, why = isogov.governance(self.d.raw, ROOT)
        self.governance = why
        self.found["GOVERNANCE"] += [] if ok else [why]
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
    out = [f"  unused permission  `{n}` may use `{x}` and nothing does: remove it" for n, x in isorules.unused_permissions(c.d, c.edges)]
    out += [f"  unused exposure    `{n}` exposes {f} and nothing outside uses it: stop exposing it" for n, f in isorules.unused_exposes(c.d, c.edges, c.checked)]
    if c.added:
        out.append(f"  contracts          {c.added} exposed name(s) not recorded yet: `--accept` records them (an ADR)")
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
    lines += ["", "  fix an edge: move the code, invert the dependency, or go through an exposed file (skill refactor-cycle);",
              "  never widen the declaration to pass: a wider rule is a decision for a person (an ADR via --accept)."]
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
    decl, left_out = isopropose.propose([r for r in o.paths], files, edges, o.depth)
    text = isopropose.to_yaml(decl, left_out)
    target = ROOT / isodecl.DECL
    if not o.flag["--write"]:
        print(text, end="")
        print(f"\n# {len(decl['isolations'])} isolation(s), {len(left_out)} defect edge(s) left out. --write saves it as {isodecl.DECL}.")
        return
    if target.exists() and not o.flag["--force"]:
        sys.exit(f"{isodecl.DECL} exists: --force replaces it (the old rules are in git and in the accepted ADR)")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    isogov.declaration_index_row(ROOT)
    print(f"wrote {isodecl.DECL}: {len(decl['isolations'])} isolation(s), {len(left_out)} defect edge(s) left out (listed at its end)")
    print("next: prune it, then `aix code isolations --accept` (contracts + the ADR a person accepts)")


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
    modes = {"--propose": propose, "--accept": accept, "--codeowners": owners, "--requirements": requirements}
    mode = next((m for m in modes if o.flag[m]), None)
    return modes[mode](o) if mode else check(o)


if __name__ == "__main__":
    main(sys.argv[1:])
