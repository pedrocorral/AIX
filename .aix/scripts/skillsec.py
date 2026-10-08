"""Leaf: the dangerous shapes of a skill or an instruction file, for `aix skills security` (benchmark section 29,
NVIDIA SkillSpector the referee). Shape-based, not a word list: a hidden character (zero-width or a bidi control), an
HTML or link comment that carries an instruction to the agent (a comment that is plain prose is not), a long base64
blob in prose (an image data URI is not), fetch-and-run in a skill script or a fenced block (a prose line that warns
against it is not), a script that reads a secret place and also sends data to an external host (reading `.env` alone,
or posting to a relative path alone, is not), and the four override phrases that have no honest use. The text an agent
reads as instructions is SKILL.md and the scripts beside it, plus AGENTS.md, CLAUDE.md and the other instruction
files. Findings to review, never proof."""
import re
from pathlib import Path

ROW = "VUL-AI-003"
CWE_INJECT, CWE_FETCH, CWE_EXFIL, CWE_HIDDEN = "CWE-77", "CWE-829", "CWE-200", "CWE-506"
SNIPPET = 110

HIDDEN = re.compile("[​-‍⁠﻿‪-‮⁦-⁩]")
COMMENT = re.compile(r"<!--(.*?)-->|^\[//\]:\s*#\s*\((.*?)\)", re.S | re.M)
B64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")
FENCE = re.compile(r"^[ \t]*(?:```|~~~)")
# fetch a remote thing and run it, or run inline code the file carries
_SH = r"(?:ba|z|da)?sh"
FETCH = re.compile(
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?" + _SH + r"\b"
    r"|\bwget\b[^\n]*\s-\w*O-"
    r"|\bbase64\b[^\n]*(?:-d|--decode)[^\n|]*\|\s*" + _SH + r"\b"
    r"|\bnode\s+-e\b|\bdeno\s+eval\b"
    r"|\bpython3?\s+-c\b[^\n]*(?:urlopen|urlretrieve|requests\.get)"
    r"|DownloadString|\biex\b|Invoke-Expression"
    r"|eval\s*[\"']?\$\(\s*(?:curl|wget)", re.I)
# a secret place the file reaches into
SECRET = re.compile(
    r"~?/?\.ssh/|/\.ssh\b|id_(?:rsa|ed25519|ecdsa)"
    r"|~?/?\.aws/|\.aws/credentials|~?/?\.npmrc\b|~?/?\.netrc\b|\.git-credentials"
    r"|\bprintenv\b|(?:^|[|;&]\s*)env\b\s*(?:\||>)"
    r"|\bcat\b[^\n]*\.env\b", re.I | re.M)
# an outbound send to an external host (a relative path is the skill's own app, not exfiltration)
SEND = re.compile(
    r"\bcurl\b[^\n]*\s(?:-d|--data(?:-\w+)?|-F|--form|-T|--upload-file)\b[^\n]*https?://"
    r"|\b(?:requests|httpx)\.(?:post|put)\(\s*[\"']https?://"
    r"|\bfetch\(\s*[\"']https?://[^\n]*(?:POST|PUT)"
    r"|\bwget\b[^\n]*--post-\w+[^\n]*https?://"
    r"|\bnc\b\s+\S+\s+\d+", re.I)
# an external host inside a carried instruction (comment), without the body being a send itself
URL = re.compile(r"https?://", re.I)
# the four phrases a legitimate skill never writes; "without asking" and "always" are ordinary autonomy and are not here
PHRASES = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?"
    r"|disregard\s+(?:all\s+)?(?:previous|prior|above|the\s+system)\b"
    r"|do\s*n[o']?t\s+(?:tell|show|reveal|mention|inform|notify|display)\b[^.\n]{0,40}\buser\b"
    r"|(?:hide|conceal)\s+(?:this|it|the\s+\w+)\s+from\s+the\s+user"
    r"|without\s+(?:telling|informing|notifying)\s+the\s+user", re.I)

ADVICE = {
    "hidden": "a skill is plain text; a zero-width or direction-control character hides instructions from the reader: delete it and read the line",
    "comment": "an HTML or link comment that tells the agent what to do is a hidden instruction; delete it, the visible text is the whole skill",
    "b64": "a skill carries no encoded blob; decode it to see what it is, then delete it",
    "fetch": "a skill must not fetch and run code from the network or run an inline one-liner; replace it with a reviewed, pinned step",
    "exfil": "this reads a secret place and sends to an outside host: the exfiltration shape; delete it and rotate anything it could read",
    "phrase": "a skill that tells the agent to ignore its instructions or to hide its actions from the user is an injection; delete the skill",
}
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md")
TEXT_SUFFIX = {".md", ".markdown", ".mdc", ".txt", ".rst", ".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".ps1", ".rb", ".pl"}
MARKDOWN_SUFFIX = {".md", ".markdown", ".mdc", ".rst", ".txt"}


def _finding(cwe: str, title: str, where: tuple, snippet: str, advice: str) -> tuple:
    """`where` is (rel, line)."""
    return (ROW, cwe, title, where[0], where[1], snippet.strip()[:SNIPPET], ADVICE[advice], None)


def _carries_instruction(body: str) -> bool:
    """A comment body that tells the agent to do something: an override phrase, a fetch-and-run, or an external URL."""
    return bool(PHRASES.search(body) or FETCH.search(body) or URL.search(body)
                or re.search(r"\b(?:system\s+prompt|your\s+(?:instructions?|rules?|system)|exfiltrat\w*)\b", body, re.I))


def _code_regions(text: str, is_markdown: bool) -> list:
    """(start_line, lines) blocks to read as code: a whole script, or each fenced block of a markdown file."""
    lines = text.splitlines()
    if not is_markdown:
        return [(1, lines)]
    out, inside, start, buf = [], False, 0, []
    for i, l in enumerate(lines, 1):
        if FENCE.match(l):
            if inside:
                out.append((start, buf)); buf = []
            inside = not inside; start = i + 1
            continue
        if inside:
            buf.append(l)
    return out


# ---- the shapes of one file ---------------------------------------------------------------------------------------

def _line_finding(rel: str, i: int, l: str):
    """The hidden-character, override-phrase or base64 shape of one line, or None."""
    if HIDDEN.search(l):
        return _finding(CWE_HIDDEN, "a hidden character in a skill", (rel, i), l, "hidden")
    if PHRASES.search(l):
        return _finding(CWE_INJECT, "a phrase that tells the agent to ignore or hide", (rel, i), l, "phrase")
    b = B64.search(l)
    if b and "data:image" not in l and "base64," not in l:
        return _finding(CWE_HIDDEN, "a base64 blob in a skill", (rel, i), b.group(0), "b64")
    return None


def _comment_findings(rel: str, text: str) -> list:
    """Comments (HTML or `[//]: #`) whose body tells the agent what to do."""
    out = []
    for m in COMMENT.finditer(text):
        body = m.group(1) or m.group(2) or ""
        if _carries_instruction(body):
            out.append(_finding(CWE_INJECT, "a comment carrying an instruction to the agent", (rel, text.count("\n", 0, m.start()) + 1), body, "comment"))
    return out


def _prose_findings(rel: str, text: str) -> list:
    """Shapes that live in the prose an agent reads: hidden characters, carried-instruction comments, base64, phrases."""
    lines = [_line_finding(rel, i, l) for i, l in enumerate(text.splitlines(), 1)]
    return [fx for fx in lines if fx] + _comment_findings(rel, text)


def _code_findings(rel: str, text: str, is_markdown: bool) -> list:
    """Fetch-and-run anywhere in the code, and a block that both reaches a secret place and sends to an outside host."""
    out = []
    for start, block in _code_regions(text, is_markdown):
        for i, l in enumerate(block, start):
            if FETCH.search(l):
                out.append(_finding(CWE_FETCH, "fetch-and-run in a skill script", (rel, i), l, "fetch"))
        joined = "\n".join(block)
        s = SECRET.search(joined)
        if s and SEND.search(joined):
            out.append(_finding(CWE_EXFIL, "a script that reads a secret and sends it out", (rel, start + joined.count("\n", 0, s.start())), s.group(0), "exfil"))
    return out


def findings_in(f: Path, rel: str) -> list:
    """Every skill-security finding of one file; a binary or unreadable file has none."""
    if f.suffix.lower() not in TEXT_SUFFIX:
        return []
    try:
        text = f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    is_markdown = f.suffix.lower() in MARKDOWN_SUFFIX
    return _prose_findings(rel, text) + _code_findings(rel, text, is_markdown)


# ---- the files, the two callers -----------------------------------------------------------------------------------

def scan_dir(base: Path, rel) -> list:
    """Every finding of every file under a folder, or none when the folder is absent; one skill folder for
    `aix skills add`, a whole skills base for the tree scan."""
    if not base.is_dir():
        return []
    return [fx for f in base.rglob("*") if f.is_file() for fx in findings_in(f, rel(f))]


def _instruction_file_findings(root: Path, rel) -> list:
    files = [root / name for name in INSTRUCTION_FILES]
    return [fx for f in files if f.is_file() for fx in findings_in(f, rel(f))]


def scan_tree(root: Path, rel) -> list:
    """Every installed skill under root/.aix/skills (and .claude/skills, .cursor/rules) plus the instruction files."""
    bases = (root / ".aix" / "skills", root / ".claude" / "skills", root / ".cursor" / "rules")
    return [fx for base in bases for fx in scan_dir(base, rel)] + _instruction_file_findings(root, rel)
