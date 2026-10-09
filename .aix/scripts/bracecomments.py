"""Leaf: the comments of the brace languages (JavaScript/TypeScript, Java, Rust) taken out, string literals kept
whole, so a commented-out import is no edge and the `//` of `"http://x"` is no comment. Rust's single quote opens a
character literal of one character, never a lifetime (`'a`)."""
import re

COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
STRINGS = {
    "js": r"`(?:[^`\\]|\\.)*`|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
    "java": r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])+'",
    "rust": r"\br#+\".*?\"#+|\br\"[^\"]*\"|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\\n])'",
}
_PATTERNS = {lang: re.compile(s + "|" + COMMENTS.pattern, re.S) for lang, s in STRINGS.items()}


def strip_comments(text: str, lang: str = "js", keep_lines: bool = False) -> str:
    """The text without comments; each one becomes a space, or its own newlines with `keep_lines` (line numbers hold)."""
    def blank(m):
        s = m.group(0)
        if not s.startswith(("//", "/*")):
            return s
        return "\n" * s.count("\n") or " " if keep_lines else " "
    return _PATTERNS[lang].sub(blank, text)


def strip_strings(text: str, lang: str = "js") -> str:
    """The text with every string literal emptied (`""`) and comments out: what is left is code."""
    return _PATTERNS[lang].sub(lambda m: " " if m.group(0).startswith(("//", "/*")) else '""', text)
