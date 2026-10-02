"""Leaf: what a push-protection scanner refuses, found before the push. GitHub and Azure DevOps read every blob of a
push with provider patterns (Google, AWS, GitHub, Slack, Stripe, private keys, JWTs, ...) and refuse the push on a
match; they honour no marker, no test folder, no comment. This check reads every tracked file the same way: the
provider rules of the gitleaks set (the generic ones left out: a push scanner has no `password = "..."` rule) on
every line, markers and test paths ignored. A hit is a finding whatever the string opens: shape is what the
scanner sees."""
import subprocess
from pathlib import Path

from codefiles import ROOT, SKIP, rel
import secretscan

GENERIC = ("generic-api-key", "curl-auth-user", "curl-auth-header", "hashicorp-tf-password")   # not in a push scanner's set
ADVICE = ("a real credential: rotate it now and read it from the environment or a secret manager; a sample: a test needs no "
          "value of that shape, assert on the code path; either way a push scanner refuses the file as it is")


GIT_TIMEOUT = 60


def _git_files(root: Path) -> list:
    """Tracked and unignored files, as git names them; [] without git."""
    try:
        out = subprocess.run(["git", "-c", f"safe.directory={root}", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root, capture_output=True, text=True, timeout=GIT_TIMEOUT).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [root / n for n in out.split("\0") if n]


def tracked_files(root: Path = ROOT) -> list:
    """What a push would carry: git's tracked and unignored files; every file under the root when there is no git."""
    files = _git_files(root) or [f for f in root.rglob("*") if not (SKIP & set(f.relative_to(root).parts))]
    return [f for f in files if f.is_file() and not f.is_symlink()]


def _provider_hits(path: str, line: str) -> list:
    return [h for h in secretscan.find(path, line) if h[0] not in GENERIC]


def scan_file(f: Path) -> list:
    """[(vul, cwe, title, file, line, snippet, advice, None)] for one file, every line, no marker honoured."""
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []   # binary or unreadable: not a text blob a scanner reads as code
    path = rel(f)
    return [("VUL-SECRET-001", "CWE-798", f"push protection would refuse: {rid}", path, i, raw.strip()[:110], ADVICE, None)
            for i, raw in enumerate(lines, 1) for rid, _d, _s in _provider_hits(path, raw)]


def scan(root: Path = ROOT) -> list:
    return [fx for f in tracked_files(root) for fx in scan_file(f)]


def render(findings: list, n_files: int) -> str:
    lines = [f"Push protection — {n_files} tracked files read as a push scanner reads them (no marker, no test folder spared)", ""]
    for _vul, _cwe, title, path, i, snippet, _advice, _acc in findings:
        lines += [f"    {path}:{i}  {title}", f"      {snippet}"]
    lines.append(f"  {len(findings)} string(s) a push scanner would refuse" + (f"; {ADVICE}" if findings else ""))
    return "\n".join(lines)


def main(gate: bool) -> int:
    files = tracked_files()
    findings = [fx for f in files for fx in scan_file(f)]
    print(render(findings, len(files)))
    if gate and findings:
        raise SystemExit(f"GATE FAILED: {len(findings)} string(s) a push scanner would refuse")
    if gate:
        print("GATE PASSED")
    return len(findings)
