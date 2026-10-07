"""Section 26 of docs/tests/benchmark-engines.md: the ABAP taint walk on abap2xlsx and abapGit. No engine walks
taint through ABAP to compare against, so the numbers are ours: the paths `aix code vulnerabilities --taint` finds,
and for every ABAP finding of `aix code security` (section 25) whether a path from an input lands on its line. The
two projects are the negative controls; the planted tests are the positive cases."""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engines

KIT = Path(__file__).resolve().parents[2]
PATH_LINE = re.compile(r"^\s+(\S+\.abap):(\d+)\s+input reaches (.*?) \((CWE-\d+)\)", re.M)
SOURCE = re.compile(r"<- (.*)$", re.M)
SECURITY_LINE = re.compile(r"^\s+(\S+\.abap):(\d+)\s+(.*?) \((CWE-\d+)\)", re.M)


def tool(copy: Path, *args) -> str:
    return subprocess.run([str(copy / ".aix" / "bin" / "aix"), "code", *args], cwd=copy, env=engines.env(), capture_output=True, text=True).stdout


def report(project: dict) -> str:
    tmp = engines.prepare(project)
    taint = tool(tmp, "vulnerabilities", "--taint")
    paths = [(m.group(1), int(m.group(2)), m.group(3), m.group(4)) for m in PATH_LINE.finditer(taint)]
    security = [(m.group(1), int(m.group(2)), m.group(3)) for m in SECURITY_LINE.finditer(tool(tmp, "security"))]
    reached = {(f, l) for f, l, _k, _c in paths}
    lines = [f"== {project['name']}: taint paths through ABAP {len(paths)}; step-3 findings {len(security)}, of which a path from an input lands on {sum(1 for f, l, _t in security if (f, l) in reached)}"]
    lines += [f"   path: {f}:{l} {k} ({c})" for f, l, k, c in paths][:20]
    lines += [f"     {s}" for s in SOURCE.findall(taint)][:20]
    return "\n".join(lines)


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or ["abap2xlsx", "abapGit"]
    projects = {p["name"]: p for p in json.loads((KIT / "tests" / "extended" / "projects.json").read_text())}
    for name in names:
        print(report(projects[name]))


if __name__ == "__main__":
    main(sys.argv[1:])
