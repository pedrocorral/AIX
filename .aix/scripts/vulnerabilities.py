#!/usr/bin/env python3
"""aix code vulnerabilities — the deep security layer: taint paths, known CVEs, secrets in git history.

  --taint     Python, per file through the parser: input sources (route/handler parameters, request objects, argv,
              environment, stdin) followed through assignments, f-strings, concatenation and calls into functions of
              the same file, to dangerous sinks (shell, eval, SQL, file paths, redirects, template strings,
              deserialisation, outbound requests). Sanitisers (int/float, shlex.quote, escape, secure_filename,
              uuid, parameterised execute, Path.resolve with is_relative_to) clear the taint.
              Result: "input reaches sink" with the path. Static, one call deep across functions, one file at a time.
  --cve       pinned dependencies (requirements, uv/poetry locks, package-lock, pnpm-lock, Cargo.lock) checked in one
              batch against the OSV database (api.osv.dev). Needs the network; stops cleanly and says so otherwise.
  --history   `git log -p` through the secret rules: keys, tokens and hard-coded passwords in past commits (a rotated
              key in history is still a leak). Bounded by --commits N (default 300).
Every finding names the VUL row and CWE it feeds; --audit writes the audit report with the evidence table.
aix: skip-security-scan this file describes sources and sinks and holds the self-test snippets"""
import ast, json, re, subprocess, sys, urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ROOT, CODE_ROOTS, SKIP, rel, source_files, iter_functions
from codesecurity import RULES, SKIP_FILE, MARKER_LINES, is_test, register_rows

REQUEST_ATTRS = {"args", "form", "json", "values", "data", "files", "GET", "POST", "query_params", "path_params",
                 "headers", "cookies", "body", "get_json", "get_data", "stream"}
SOURCE_CALLS = {"input", "os.getenv", "os.environ.get", "sys.stdin.read", "sys.stdin.readline"}
SANITISERS = {"int", "float", "bool", "len", "shlex.quote", "escape", "html.escape", "markupsafe.escape", "bleach.clean",
              "secure_filename", "uuid.UUID", "abs", "round", "re.fullmatch", "ipaddress.ip_address"}
SINKS = {  # dotted call name (suffix match) -> (VUL row, CWE, kind, which args are dangerous)
    "subprocess.run": ("VUL-INJ-002", "CWE-78", "shell command", "shell"), "subprocess.call": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "subprocess.check_output": ("VUL-INJ-002", "CWE-78", "shell command", "shell"), "subprocess.check_call": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "subprocess.Popen": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "os.system": ("VUL-INJ-002", "CWE-78", "shell command", "any"), "os.popen": ("VUL-INJ-002", "CWE-78", "shell command", "any"),
    "eval": ("VUL-INJ-002", "CWE-95", "eval", "any"), "exec": ("VUL-INJ-002", "CWE-95", "exec", "any"),
    ".execute": ("VUL-INJ-001", "CWE-89", "SQL statement", "first"), ".executemany": ("VUL-INJ-001", "CWE-89", "SQL statement", "first"),
    ".raw": ("VUL-INJ-001", "CWE-89", "raw SQL", "first"),
    "open": ("VUL-INJ-002", "CWE-22", "file path", "first"), "send_file": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "send_from_directory": ("VUL-INJ-002", "CWE-22", "file path", "any"), "os.remove": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "os.unlink": ("VUL-INJ-002", "CWE-22", "file path", "first"), "shutil.rmtree": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "shutil.copy": ("VUL-INJ-002", "CWE-22", "file path", "any"), "Path": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "redirect": ("VUL-WEB-003", "CWE-601", "redirect target", "first"), "RedirectResponse": ("VUL-WEB-003", "CWE-601", "redirect target", "first"),
    "render_template_string": ("VUL-INJ-002", "CWE-1336", "template string", "first"), "Template": ("VUL-INJ-002", "CWE-1336", "template string", "first"),
    "yaml.load": ("VUL-INPUT-002", "CWE-502", "yaml.load", "first"), "pickle.loads": ("VUL-INPUT-002", "CWE-502", "pickle", "first"),
    "pickle.load": ("VUL-INPUT-002", "CWE-502", "pickle", "first"), "marshal.loads": ("VUL-INPUT-002", "CWE-502", "marshal", "first"),
    "requests.get": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"), "requests.post": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),
    "urllib.request.urlopen": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"), "httpx.get": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),
}
ADVICE = {"CWE-78": "argument list without a shell; validate each argument", "CWE-95": "never eval input; a dispatch table or ast.literal_eval",
          "CWE-89": "parameterised query: execute(sql, params)", "CWE-22": "resolve against a base directory and reject anything outside it",
          "CWE-601": "allow-list targets or relative paths only", "CWE-1336": "render a file template with a context",
          "CWE-502": "json / yaml.safe_load; never deserialise input", "CWE-918": "allow-list hosts; block private ranges and redirects"}


# ---- taint: Python, per file --------------------------------------------------------------------------------------

def dotted(node):
    """'a.b.c' for Name/Attribute chains, '' otherwise."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return dotted(node.func) + "()"
    return ""


def call_name(call: ast.Call) -> str:
    return dotted(call.func)


def is_source(node, tainted) -> str:
    """A description if `node` is an input source or carries taint, else ''."""
    if isinstance(node, ast.Name):
        return tainted.get(node.id, "")
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        if base.split(".")[-1] == "request" and node.attr in REQUEST_ATTRS or base in ("sys.argv", "os.environ"):
            return f"{base}.{node.attr}"
        return is_source(node.value, tainted)
    if isinstance(node, ast.Subscript):
        b = dotted(node.value)
        if b in ("sys.argv", "os.environ") or b.endswith(".args") or b.endswith(".form") or b.endswith(".GET") or b.endswith(".POST") or b.endswith(".json"):
            return b + "[...]"
        return is_source(node.value, tainted) or is_source(node.slice, tainted)
    if isinstance(node, ast.Call):
        name = call_name(node)
        if name in SANITISERS or name.split(".")[-1] in {s.split(".")[-1] for s in SANITISERS} or name.endswith(".resolve") and False:
            return ""
        if name in SOURCE_CALLS or name.endswith(".get_json") or name.endswith(".get_data") or name.endswith(".json") and "request" in name:
            return name + "()"
        if name.endswith((".args.get", ".form.get", ".GET.get", ".POST.get", ".headers.get", ".cookies.get", ".query_params.get", ".environ.get")):
            return name + "()"
        for a in list(node.args) + [k.value for k in node.keywords]:
            s = is_source(a, tainted)
            if s:
                return s
        return is_source(node.func, tainted) if isinstance(node.func, ast.Attribute) else ""
    if isinstance(node, (ast.JoinedStr, ast.BinOp, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.IfExp, ast.Await, ast.FormattedValue, ast.BoolOp, ast.Compare)):
        for child in ast.iter_child_nodes(node):
            s = is_source(child, tainted)
            if s:
                return s
    return ""


def decorated_params(fn):
    """Parameters of a decorated function (route handler, command, task) are input, except DI defaults."""
    if not fn.decorator_list:
        return []
    di = {kw.arg for d in fn.decorator_list for kw in getattr(d, "keywords", [])}
    out = []
    for a, default in zip(fn.args.args[::-1], (fn.args.defaults[::-1] + [None] * len(fn.args.args))):
        if a.arg in ("self", "cls"):
            continue
        if isinstance(default, ast.Call) and call_name(default) in ("Depends", "Security", "Body", "Header", "Cookie", "Query", "Path", "Form"):
            if call_name(default) in ("Depends", "Security"):
                continue
        out.append(a.arg)
    return out


def sink_hits(call, tainted, fn_name):
    name = call_name(call)
    for sink, (vul, cwe, kind, which) in SINKS.items():
        if not (name == sink or (sink.startswith(".") and name.endswith(sink)) or name.endswith("." + sink)):
            continue
        if kind == "SQL statement" and len(call.args) > 1:
            continue  # parameterised: execute(sql, params)
        args = call.args if which != "first" else call.args[:1]
        if which == "shell":
            shell = any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in call.keywords)
            if not shell:
                continue
        for a in args + [k.value for k in call.keywords if which == "any"]:
            src = is_source(a, tainted)
            if src:
                return (vul, cwe, kind, src)
    return None


def taint_function(fn, file, funcs, findings, params_tainted=None, depth=0, seen=None):
    """Walk statements in order, propagate taint through assignments, report sinks, follow local calls one level."""
    seen = seen or set()
    tainted = dict(params_tainted or {})
    for p in decorated_params(fn):
        tainted[p] = f"parameter {p} of {fn.name}"
    guard_resolve = any(isinstance(n, ast.Call) and call_name(n).endswith("is_relative_to") for n in ast.walk(fn))
    for node in ast.walk(fn):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            value = node.value
            if value is None:
                continue
            src = is_source(value, tainted)
            if isinstance(value, ast.Call) and call_name(value).endswith(".resolve") and guard_resolve:
                src = ""
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        if src:
                            tainted[n.id] = f"{n.id} = ... from {src} (line {node.lineno})"
                        else:
                            tainted.pop(n.id, None)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            src = is_source(node.iter, tainted)
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name) and src:
                    tainted[n.id] = f"{n.id} iterates {src} (line {node.lineno})"
        elif isinstance(node, ast.Call):
            hit = sink_hits(node, tainted, fn.name)
            if hit:
                vul, cwe, kind, src = hit
                findings.append((vul, cwe, f"input reaches {kind}", rel(file), node.lineno, f"{call_name(node)}(...) <- {src}", ADVICE[cwe], None))
            name = call_name(node)
            if depth < 1 and name in funcs and name not in seen:
                callee = funcs[name]
                pt = {}
                for i, a in enumerate(node.args):
                    s = is_source(a, tainted)
                    if s and i < len(callee.args.args):
                        pt[callee.args.args[i].arg] = f"argument from {fn.name} line {node.lineno}: {s}"
                for k in node.keywords:
                    s = is_source(k.value, tainted)
                    if s and k.arg:
                        pt[k.arg] = f"argument from {fn.name} line {node.lineno}: {s}"
                if pt:
                    taint_function(callee, file, funcs, findings, pt, depth + 1, seen | {name})


def taint_file(file: Path, findings):
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    if any(SKIP_FILE.search(l) for l in file.read_text(encoding="utf-8", errors="replace").splitlines()[:MARKER_LINES]):
        return
    funcs = {fn.name: fn for cls, fn in iter_functions(tree) if not cls}
    for cls, fn in iter_functions(tree):
        taint_function(fn, file, funcs, findings)


def taint(paths):
    findings = []
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix == ".py":
                taint_file(f, findings)
    seen, out = set(), []
    for fx in findings:
        key = (fx[0], fx[3], fx[4])
        if key not in seen:
            seen.add(key); out.append(fx)
    return out


# ---- known CVEs via OSV ----------------------------------------------------------------------------------------

def dependencies(root: Path):
    """[(ecosystem, name, version, manifest)] from pinned manifests and lockfiles."""
    deps = []

    def files(pattern):
        return [f for f in root.rglob(pattern) if not any(s in f.relative_to(root).parts for s in SKIP)]
    for f in files("requirements*.txt"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([0-9][^\s;#]*)", line)
            if m:
                deps.append(("PyPI", m.group(1).lower(), m.group(2), rel(f)))
    for name in ("uv.lock", "poetry.lock", "pdm.lock", "Cargo.lock"):
        for f in files(name):
            eco = "crates.io" if name == "Cargo.lock" else "PyPI"
            for m in re.finditer(r'\[\[package\]\]\s*\nname\s*=\s*"([^"]+)"\s*\nversion\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8", errors="replace")):
                deps.append((eco, m.group(1), m.group(2), rel(f)))
    for f in files("package-lock.json"):
        try:
            pk = json.loads(f.read_text(encoding="utf-8", errors="replace")).get("packages", {})
        except json.JSONDecodeError:
            continue
        for path, info in pk.items():
            if path.startswith("node_modules/") and "version" in info:
                deps.append(("npm", path.split("node_modules/")[-1], info["version"], rel(f)))
    for f in files("pnpm-lock.yaml"):
        for m in re.finditer(r"^\s{2}['\"]?/?(@?[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)?)@(\d[0-9A-Za-z.\-+]*)", f.read_text(encoding="utf-8", errors="replace"), re.M):
            deps.append(("npm", m.group(1), m.group(2), rel(f)))
    seen, out = set(), []
    for d in deps:
        if d[:3] not in seen:
            seen.add(d[:3]); out.append(d)
    return out


def osv_query(deps, timeout=25):
    """One querybatch call; returns {(eco, name, version): [vuln ids]} or None when unreachable."""
    if not deps:
        return {}
    body = json.dumps({"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v, _ in deps]}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/querybatch", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            results = json.loads(r.read().decode()).get("results", [])
    except Exception:
        return None
    out = {}
    for d, res in zip(deps, results):
        ids = [v["id"] for v in res.get("vulns", [])]
        if ids:
            out[d[:3]] = ids
    return out


def osv_detail(vid, name, timeout=15):
    """Summary and the first fixed version FOR THIS PACKAGE (an advisory may cover several packages)."""
    try:
        with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vid}", timeout=timeout) as r:
            v = json.loads(r.read().decode())
    except Exception:
        return "", ""
    mine = [a for a in v.get("affected", []) if a.get("package", {}).get("name", "").lower() == name.lower()] or v.get("affected", [])
    fixed = sorted({e["fixed"] for a in mine for rg in a.get("ranges", []) for e in rg.get("events", []) if "fixed" in e},
                   key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"[.\-]", s)])
    return v.get("summary", "")[:70], fixed[0] if fixed else ""


def cve(paths):
    deps = dependencies(ROOT)
    hits = osv_query(deps)
    if hits is None:
        return None, len(deps)
    findings = []
    for (eco, name, version), ids in hits.items():
        manifest = next(d[3] for d in deps if d[:3] == (eco, name, version))
        for vid in ids[:3]:
            summary, fixed = osv_detail(vid, name)
            findings.append(("VUL-DEP-001", "CWE-1395", f"known vulnerability {vid}", manifest, 0,
                             f"{name} {version} ({eco}): {summary}" + (f" — fixed in {fixed}" if fixed else ""),
                             f"upgrade {name} to {fixed or 'a fixed version'} and re-run", None))
    return findings, len(deps)


# ---- secrets in git history ------------------------------------------------------------------------------------

SECRET_RULES = [r for r in RULES if r[0] == "VUL-SECRET-001"]


def has_skip_marker(path: str, commit: str) -> bool:
    """The file's marker at that commit (files move; the current tree is not enough)."""
    try:
        head = subprocess.run(["git", "-c", f"safe.directory={ROOT}", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=30).stdout
    except Exception:
        return False
    return any(SKIP_FILE.search(l) for l in head.splitlines()[:MARKER_LINES])


def history(commits=300):
    if not (ROOT / ".git").exists():
        return None
    try:
        log = subprocess.run(["git", "-c", f"safe.directory={ROOT}", "log", "-p", "--all", "--no-color", "--unified=0", "--diff-filter=AM", f"-n{commits}"],
                             cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=120).stdout
    except Exception:
        return None
    findings, commit, path, seen = [], "", "", set()
    skip_paths, checked = set(), set()
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line[7:14]
        elif line.startswith("+++ b/"):
            path = line[6:]
            if (commit, path) not in checked:
                checked.add((commit, path))
                if has_skip_marker(path, commit):
                    skip_paths.add(path)
                else:
                    skip_paths.discard(path)
        elif line.startswith("+") and not line.startswith("+++") and path not in skip_paths:
            code = line[1:]
            for vul, cwe, title, langs, rx, advice in SECRET_RULES:
                m = re.search(rx, code)
                if m and (title, path, m.group(0)[:40]) not in seen:
                    seen.add((title, path, m.group(0)[:40]))
                    findings.append((vul, cwe, f"{title} in history (commit {commit})", path, 0, code.strip()[:100],
                                     "rotate the secret now; history keeps it even after removal (git filter-repo to purge)", None))
    return findings


# ---- report -------------------------------------------------------------------------------------------------------

def render(sections, paths, strict):
    rows = register_rows()
    lines = [f"Code vulnerabilities — {', '.join(paths)}", ""]
    total_live = 0
    for title, findings, note in sections:
        if findings is None:
            lines += [f"  {title}: {note}", ""]
            continue
        live = [f for f in findings if strict or not is_test(ROOT / f[3])]
        total_live += len(live)
        lines.append(f"  {title}: {len(findings)} finding(s)" + (f"  ({note})" if note else ""))
        by_vul = defaultdict(list)
        for f in findings:
            by_vul[f[0]].append(f)
        for vul in sorted(by_vul):
            desc, status = rows.get(vul, ("", "?"))
            lines.append(f"    {vul}  {desc[:60]}  [register: {status}]")
            for _, cwe, what, file, ln, snippet, advice, _ in by_vul[vul][:20]:
                where = f"{file}:{ln}" if ln else file
                tag = "test" if is_test(ROOT / file) else "REVIEW"
                lines.append(f"      {where}  {what} ({cwe})  [{tag}]\n        {snippet}\n        -> {advice}")
        lines.append("")
    lines.append("  A taint path is static evidence that input can reach a sink, not a proof of exploitability in production;")
    lines.append("  a CVE applies to the version, not necessarily to how you use it; a history leak is real until the secret is rotated.")
    lines.append("  Fix: taint -> the code (see advice) ; CVE -> upgrade ; history -> rotate now.  `--audit` writes the evidence report.")
    return "\n".join(lines), total_live


def write_audit(all_findings, paths, unreachable):
    rows = register_rows()
    today = date.today().isoformat()
    out = ROOT / "docs" / "security" / "audits" / f"AUDIT-{today}-vulnerabilities.md"
    body = [f"---\nid: AUDIT-{today}-vulnerabilities\nskill: aix code vulnerabilities (taint, CVE, history)\ndate: {today}\nscope: [{', '.join(paths)}]\nresult: {'findings' if all_findings else 'pass'}\n---",
            f"# Audit — deep code checks — {today}", "", "## Method (what was checked, tools run)",
            "`aix code vulnerabilities`: Python taint analysis (input sources to dangerous sinks, one call deep, per file), pinned dependencies against the OSV database"
            + (" (unreachable in this run)" if unreachable else "") + ", secrets in git history. Findings are evidence to review; a quiet check is not proof of absence.", "",
            "## Findings", "| VUL id | Asset / threat | Impact | Likelihood rationale | Control | Verification method | Evidence | Status before → after | Residual risk |", "|---|---|---|---|---|---|---|---|---|"]
    for vul, cwe, what, file, ln, snippet, advice, _ in sorted(all_findings, key=lambda f: (f[0], f[3], f[4])):
        desc, status = rows.get(vul, ("", "?"))
        ev = f"`{file}{':' + str(ln) if ln else ''}` {what} ({cwe}): {snippet[:60]}"
        body.append(f"| {vul} | {desc[:50]} | | {'data flow' if 'reaches' in what else 'known CVE' if 'vulnerability' in what else 'history'} | {advice[:60]} | code review / upgrade / rotation | {ev} | {status} → confirmed? review | |")
    body += ["", "## New vulnerabilities discovered (added to register)", "- none by this scan", "", "## Follow-ups (tasks created)", "- review every row; fix, upgrade or rotate; re-run", ""]
    out.write_text("\n".join(body), encoding="utf-8")
    idx = out.parent / "INDEX.md"
    if idx.exists() and out.name not in idx.read_text(encoding="utf-8"):
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(f"| `{out.name}` | Deep code checks (`aix code vulnerabilities`), {len(all_findings)} findings | Verifying VUL statuses; release |\n")
    return out


# ---- self-test ---------------------------------------------------------------------------------------------------------

SELFTEST_APP = '''
import subprocess, os, shlex
from flask import request, redirect
BASE = "/srv"
def helper(cmd):
    return subprocess.run(cmd, shell=True)
def run_argv():
    return subprocess.run(["ls", request.args.get("d")])
@app.route("/x")
def handler():
    name = request.args.get("name")
    helper("ls " + name)
    n = int(request.args.get("n"))
    subprocess.run("x" + str(n), shell=True)
    safe = shlex.quote(name)
    subprocess.run("ls " + safe, shell=True)
    path = os.path.join(BASE, request.args["f"])
    return open(path).read()
@app.route("/r")
def go(target: str):
    return redirect(target)
def sql(cur, uid):
    cur.execute("SELECT 1 WHERE id = ?", (uid,))
'''


def selftest():
    import tempfile
    global ROOT
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        (base / "app.py").write_text(SELFTEST_APP, encoding="utf-8")
        (base / "requirements.txt").write_text("requests==2.19.0\nflask\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=base); subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init"], cwd=base)
        (base / "cfg.py").write_text('password = "hunter2xyz"\n', encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=base); subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "leak"], cwd=base)
        saved, ROOT = ROOT, base
        try:
            t = taint([str(base)])
            deps = dependencies(base)
            h = history(50)
        finally:
            ROOT = saved
    kinds = sorted(f[2] + "@" + str(f[4]) for f in t)
    checks = [("taint: helper() shell via argument", "input reaches shell command@6" in kinds),
              ("taint: open(path) from request", "input reaches file path@18" in kinds),
              ("taint: redirect(target) from route param", "input reaches redirect target@21" in kinds),
              ("taint: int() sanitises", "input reaches shell command@13" not in kinds),
              ("taint: shlex.quote sanitises", "input reaches shell command@15" not in kinds),
              ("taint: argument list, no shell", "input reaches shell command@8" not in kinds),
              ("taint: parameterised SQL not flagged", not any("SQL" in k for k in kinds)),
              ("deps: pinned requests parsed, unpinned flask ignored", [(e, n, v) for e, n, v, _ in deps] == [("PyPI", "requests", "2.19.0")]),
              ("history: hard-coded password in a past commit", h is not None and len(h) == 1 and "cfg.py" in h[0][3])]
    failed = 0
    for name, ok in checks:
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print("  taint kinds seen:", kinds)
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code vulnerabilities [PATH...] [--taint] [--cve] [--history] [--commits N] [--strict] [--gate] [--audit] [--report] [--selftest]"


def main(args):
    if "--selftest" in args:
        return selftest()
    modes = {m for m in ("--taint", "--cve", "--history") if m in args} or {"--taint", "--cve", "--history"}
    commits = 300
    if "--commits" in args:
        i = args.index("--commits"); commits = int(args[i + 1]); del args[i:i + 2]
    strict, gate, audit, report = "--strict" in args, "--gate" in args, "--audit" in args, "--report" in args
    paths = [a for a in args if not a.startswith("--")] or [r for r in CODE_ROOTS if (ROOT / r).exists()] or ["."]
    sections, unreachable = [], False
    if "--taint" in modes:
        sections.append(("taint paths (Python)", taint(paths), "input sources followed to sinks, one call deep, per file"))
    if "--cve" in modes:
        found, n = cve(paths)
        if found is None:
            unreachable = True
            sections.append(("known CVEs (OSV)", None, f"OSV unreachable (network); {n} pinned dependencies not checked"))
        else:
            sections.append(("known CVEs (OSV)", found, f"{n} pinned dependencies queried"))
    if "--history" in modes:
        h = history(commits)
        sections.append(("secrets in git history", h, f"last {commits} commits, all branches" if h is not None else "no git repository"))
    text, n_live = render(sections, paths, strict)
    print(text)
    all_findings = [f for _, fs, _ in sections if fs for f in fs]
    if report:
        out = ROOT / "docs" / "tests" / "code-vulnerabilities.md"
        out.write_text("# Code vulnerabilities (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if audit:
        print(f"\n  wrote {write_audit(all_findings, paths, unreachable).relative_to(ROOT)}  (complete the Status column after review)")
    if gate and n_live:
        sys.exit(f"GATE FAILED: {n_live} finding(s) to review")
    if gate:
        print("GATE PASSED" + ("  (CVE check skipped: OSV unreachable)" if unreachable else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
