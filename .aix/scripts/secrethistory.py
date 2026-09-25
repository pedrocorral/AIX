"""Leaf: secrets in git history. The register's secret rules and the gitleaks rule set run over the added lines of
every commit on every branch (or the last N with --commits N)."""
import re, subprocess
from pathlib import Path

from codefiles import ROOT
from codesecurity import RULES, SKIP_FILE, MARKER_LINES
import secretscan


# ---- secrets in git history ------------------------------------------------------------------------------------

SECRET_RULES = [r for r in RULES if r[0] == "VUL-SECRET-001"]


def has_skip_marker(path: str, commit: str, root: Path = ROOT) -> bool:
    """The file's marker at that commit (files move; the current tree is not enough)."""
    try:
        head = subprocess.run(["git", "-c", f"safe.directory={root}", "show", f"{commit}:{path}"], cwd=root, capture_output=True, text=True, errors="replace", timeout=30).stdout
    except Exception:
        return False
    return any(SKIP_FILE.search(l) for l in head.splitlines()[:MARKER_LINES])


def _git_log(commits, root: Path):
    limit = [f"-n{commits}"] if commits else []
    try:
        return subprocess.run(["git", "-c", f"safe.directory={root}", "log", "-p", "--all", "--no-color", "--unified=0", "--diff-filter=AM", *limit],
                              cwd=root, capture_output=True, text=True, errors="replace", timeout=600).stdout
    except Exception:
        return None


class _History:
    """Walks a `git log -p`: tracks the commit, the file, the files skipped by marker, and the secrets already seen."""
    def __init__(self, root: Path):
        self.root, self.findings, self.commit, self.path = root, [], "", ""
        self.seen, self.skip_paths, self.checked = set(), set(), set()

    def file_header(self, path: str):
        self.path = path
        if (self.commit, path) in self.checked:
            return
        self.checked.add((self.commit, path))
        skip = path.startswith(".aix/") or has_skip_marker(path, self.commit, self.root)   # the kit's manifest is hashes keyed by file
        (self.skip_paths.add if skip else self.skip_paths.discard)(path)

    def _record(self, title: str, secret: str, code: str):
        key = (title, self.path, secret[:40])
        if key not in self.seen:
            self.seen.add(key)
            self.findings.append(("VUL-SECRET-001", "CWE-798", f"{title} in history (commit {self.commit})", self.path, 0, code.strip()[:100],
                                  "rotate the secret now; history keeps it even after removal (git filter-repo to purge)", None))

    def added_line(self, code: str):
        """The register's own secret rules first; the gitleaks rules on a line they did not already report."""
        hit = False
        for _vul, _cwe, title, _langs, rx, _advice in SECRET_RULES:
            m = re.search(rx, code)
            if m:
                hit = True
                self._record(title, m.group(0), code)
        if not hit and not secretscan.path_allowed(self.path):
            for rid, _description, secret in secretscan.find(self.path, code):
                self._record(f"secret pattern: {rid}", secret, code)


def history(commits=None, root: Path = ROOT):
    """Secret findings in the history of the repository at `root` (all commits, or the last `commits`); None when
    there is no git history."""
    if not (root / ".git").exists():
        return None
    log = _git_log(commits, root)
    if log is None:
        return None
    h = _History(root)
    for line in log.splitlines():
        if line.startswith("commit "):
            h.commit = line[7:14]
        elif line.startswith("+++ b/"):
            h.file_header(line[6:])
        elif line.startswith("+") and not line.startswith("+++") and h.path not in h.skip_paths:
            h.added_line(line[1:])
    return h.findings
