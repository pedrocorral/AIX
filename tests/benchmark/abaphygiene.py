"""Section 27 of docs/tests/benchmark-engines.md: ABAP hygiene, ours vs abaplint's `unused_variables` on abap2xlsx
and abapGit, line by line; the swallowed CATCH, unused parameter and pass-through counts are ours alone (abaplint's
`empty_structure` does not cover a bare CATCH). Run: `python tests/benchmark/abaphygiene.py [abap2xlsx abapGit]`."""
import json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import stylemetrics   # noqa: E402


def _env() -> dict:
    return dict(os.environ, PATH=os.pathsep.join([str(engines.BENCH / "node" / "bin"), os.environ["PATH"]]))


def abaplint_unused(project: Path) -> set:
    """(file, line) of abaplint's unused_variables."""
    base = json.loads(subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), "--default"], capture_output=True, text=True, env=_env()).stdout)
    cfg = project / "abaplint-unused.json"
    cfg.write_text(json.dumps({"global": base["global"], "syntax": base.get("syntax", {}), "rules": {"unused_variables": base["rules"]["unused_variables"]}}))
    out = subprocess.run([str(engines.BENCH / "node_modules" / ".bin" / "abaplint"), str(cfg)], cwd=project, capture_output=True, text=True, env=_env()).stdout
    cfg.unlink()
    return {(m.group(1), int(m.group(2))) for m in re.finditer(r"(\S+)\[(\d+), \d+\]\s+- .*\(unused_variables\)", out)}


def _kind(msg: str) -> str:
    return "swallowed" if msg.startswith("swallowed") else "parameter" if "parameter" in msg else "variable"


def _unit_rows(fx: dict, rel: str) -> list:
    rows = [(_kind(msg), rel, line, msg) for line, msg in fx["hygiene"]]
    if fx.get("passthrough"):
        rows.append(("passthrough", rel, fx["line"], f"pass-through to {fx['passthrough']}"))
    return rows


def ours(project: Path) -> dict:
    """{kind: [(file, line, message)]} over the non-test ABAP units, from the style records."""
    out = {"variable": [], "parameter": [], "swallowed": [], "passthrough": []}
    files = [f for f in sorted(project.rglob("*.abap")) if ".testclasses." not in f.name and ".aix" not in f.parts]
    for f in files:
        for fx in stylemetrics.functions_in(f):
            for kind, rel, line, msg in _unit_rows(fx, str(f.relative_to(project))):
                out[kind].append((rel, line, msg))
    return out


def report(project: dict) -> str:
    tmp = engines.prepare(project)
    us, ab = ours(tmp), abaplint_unused(tmp)
    ours_at = {(f, l) for f, l, _m in us["variable"]}
    both = ours_at & ab
    lines = [f"== {project['name']}: unused variables ours {len(ours_at)}, abaplint {len(ab)}, same line {len(both)}; "
             f"swallowed CATCH {len(us['swallowed'])}, unused private parameters {len(us['parameter'])}, pass-through methods {len(us['passthrough'])}"]
    lines += [f"   ours only: {f}:{l} {m}" for f, l, m in us["variable"] if (f, l) not in ab][:12]
    lines += [f"   abaplint only: {f}:{l}" for f, l in sorted(ab - ours_at)][:12]
    lines += [f"   {k}: {f}:{l} {m}" for k in ("swallowed", "parameter", "passthrough") for f, l, m in us[k][:4]]
    return "\n".join(lines)


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name]))


if __name__ == "__main__":
    main(sys.argv[1:])
