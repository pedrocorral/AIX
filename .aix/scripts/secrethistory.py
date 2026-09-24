"""Leaf: secrets in git history. The register's secret rules run over the diffs of the last N commits."""
import re, subprocess
from pathlib import Path

from codefiles import ROOT
from codesecurity import RULES, SKIP_FILE, MARKER_LINES


# ---- secrets in git history ------------------------------------------------------------------------------------

SECRET_RULES = [r for r in RULES if r[0] == "VUL-SECRET-001"]


def has_skip_marker(path: str, commit: str, root: Path = ROOT) -> bool:
    """The file's marker at that commit (files move; the current tree is not enough)."""
    try:
        head = subprocess.run(["git", "-c", f"safe.directory={root}", "show", f"{commit}:{path}"], cwd=root, capture_output=True, text=True, errors="replace", timeout=30).stdout
    except Exception:
        return False
    return any(SKIP_FILE.search(l) for l in head.splitlines()[:MARKER_LINES])


def _git_log(commits: int, root: Path):
    try:
        return subprocess.run(["git", "-c", f"safe.directory={root}", "log", "-p", "--all", "--no-color", "--unified=0", "--diff-filter=AM", f"-n{commits}"],
                              cwd=root, capture_output=True, text=True, errors="replace", timeout=120).stdout
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
        (self.skip_paths.add if has_skip_marker(path, self.commit, self.root) else self.skip_paths.discard)(path)

    def added_line(self, code: str):
        for vul, cwe, title, _langs, rx, advice in SECRET_RULES:
            m = re.search(rx, code)
            key = (title, self.path, m.group(0)[:40]) if m else None
            if key and key not in self.seen:
                self.seen.add(key)
                self.findings.append((vul, cwe, f"{title} in history (commit {self.commit})", self.path, 0, code.strip()[:100],
                                      "rotate the secret now; history keeps it even after removal (git filter-repo to purge)", None))


def history(commits=300, root: Path = ROOT):
    """Secret findings in the last `commits` of the repository at `root`; None when there is no git history."""
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
