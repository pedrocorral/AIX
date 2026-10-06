"""Leaf: how a finding is listed. A test or documentation file, a file git ignores and does not track (a secret
there never entered the repository), an accepted marker; those three are listed and not gated."""
import subprocess
from pathlib import Path

from codefiles import ROOT


def is_test(p: Path) -> bool:
    parts = p.parts
    return any(part in ("tests", "test", "__tests__", "fixtures") for part in parts) or ("src", "it") in zip(parts, parts[1:]) \
        or p.name.startswith("test_") or ".test." in p.name or ".spec." in p.name


def is_docs(p: Path) -> bool:
    """Documentation: an example key in a manual is listed, not gated (a real one there is still a leak: read it)."""
    return "docs" in p.parts or p.suffix in (".md", ".rst", ".adoc")


_IGNORED = None


def git_ignored() -> set:
    """The files git ignores and does not track (relative paths), once per run; empty outside a git checkout. A
    secret in such a file never entered the repository: listed as `untracked`, not gated."""
    global _IGNORED
    if _IGNORED is None:
        try:
            r = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, timeout=30)
            _IGNORED = set(r.stdout.split("\n")) - {""} if r.returncode == 0 else set()
        except (OSError, subprocess.SubprocessError):
            _IGNORED = set()
    return _IGNORED


def is_untracked(file: str) -> bool:
    return file in git_ignored()


def _tag(fx) -> str:
    """How a finding is listed: accepted with its reason, test, docs, untracked (git-ignored), or REVIEW."""
    if fx[7]:
        return "accepted: " + fx[7]
    return "test" if is_test(ROOT / fx[3]) else "docs" if is_docs(ROOT / fx[3]) else "untracked, git-ignored" if is_untracked(fx[3]) else "REVIEW"


def _not_gated(fx) -> bool:
    """Tests, documentation and git-ignored untracked files are listed, not gated."""
    return is_test(ROOT / fx[3]) or is_docs(ROOT / fx[3]) or is_untracked(fx[3])
