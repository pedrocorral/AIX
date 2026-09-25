"""Leaf: secrets by pattern, the gitleaks logic on the gitleaks rule set (secretrules.py): a keyword gate, the regex,
a Shannon-entropy floor on the captured secret, then the allowlists (placeholders, stopwords, example values, paths).
`find(path, line)` is what the tree scan and the history walk call; `path_secret(path)` names files that are secrets
by name (a .p12 keystore)."""
import math, re, warnings
from functools import lru_cache

from secretrules import GLOBAL_ALLOW, PATH_RULES, RULES

SECRET_ADVICE = "revoke and rotate now; read it from the environment or a secret manager"


class _Rule:
    """One compiled rule; `allow` keeps its allowlists with their regexes compiled."""
    def __init__(self, rule: tuple):
        rid, description, rx, keywords, entropy, group, allow, path = rule
        self.id, self.description, self.rx = rid, description, _compile(rx)
        self.keywords, self.entropy, self.group = set(keywords), entropy, group
        self.allow, self.path = [_allowlist(a) for a in allow], _compile(path) if path else None


def _compile(rx: str):
    """RE2 semantics: ASCII word characters and case folding; a few upstream patterns look like nested sets to
    Python and compile all the same."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return re.compile(rx, re.ASCII)


def _allowlist(a: dict) -> dict:
    return dict(a, regexes=[_compile(x) for x in a.get("regexes", [])], paths=[_compile(x) for x in a.get("paths", [])])


_RULES = [_Rule(r) for r in RULES]
_PATH_RULES = [(rid, description, _compile(rx)) for rid, description, rx in PATH_RULES]
_KEYWORDS = sorted({k for r in _RULES for k in r.keywords})
_ANY_KEYWORD = re.compile("|".join(map(re.escape, _KEYWORDS)))
_GLOBAL = _allowlist(GLOBAL_ALLOW)


def entropy(text: str) -> float:
    """Shannon entropy in bits per character: random keys score above 3.5, words and repeats below."""
    if not text:
        return 0.0
    counts = {c: text.count(c) for c in set(text)}
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts.values())


@lru_cache(maxsize=4096)
def path_allowed(path: str) -> bool:
    """Files gitleaks never scans: images, fonts, binaries, lockfiles of package managers, its own config."""
    return any(rx.search(path) for rx in _GLOBAL["paths"])


def _allowed(allow: dict, path: str, line: str, match: str, secret: str) -> bool:
    """One allowlist: any of its kinds matching allows (all of them under condition AND)."""
    checks = []
    if allow.get("regexes"):
        target = {"line": line, "match": match}.get(allow.get("target"), secret)
        checks.append(any(rx.search(target) for rx in allow["regexes"]))
    if allow.get("stopwords"):
        low = secret.lower()
        checks.append(any(w in low for w in allow["stopwords"]))
    if allow.get("paths"):
        checks.append(any(rx.search(path) for rx in allow["paths"]))
    return bool(checks) and (all(checks) if allow.get("condition") == "AND" else any(checks))


def _secret_of(rule: _Rule, m) -> str:
    return m.group(rule.group) if rule.group <= m.re.groups and m.group(rule.group) is not None else m.group(0)


def _hit(rule: _Rule, path: str, line: str):
    """The first match of this rule on the line that survives the path restriction, entropy and the allowlists."""
    if rule.path and not rule.path.search(path):
        return None
    for m in rule.rx.finditer(line):
        secret = _secret_of(rule, m)
        if rule.entropy is not None and entropy(secret) < rule.entropy:
            continue
        if _allowed(_GLOBAL, path, line, m.group(0), secret) or any(_allowed(a, path, line, m.group(0), secret) for a in rule.allow):
            continue
        return (rule.id, rule.description, secret)
    return None


def _candidates(line: str) -> list:
    """The rules whose keyword gate the line passes: the gate keeps the 221 regexes cheap."""
    low = line.lower()
    if not _ANY_KEYWORD.search(low):
        return []
    present = {k for k in _KEYWORDS if k in low}
    return [rule for rule in _RULES if not rule.keywords or rule.keywords & present]


def find(path: str, line: str) -> list:
    """[(rule id, description, secret)] for one line of one file; a specific rule wins over the generic one."""
    if path_allowed(path):
        return []
    hits = [h for h in (_hit(rule, path, line) for rule in _candidates(line)) if h]
    specific = [h for h in hits if h[0] != "generic-api-key"]
    return specific or hits


def path_secret(path: str):
    """(rule id, description) when the file is a secret by its name, else None."""
    for rid, description, rx in _PATH_RULES:
        if rx.search(path):
            return (rid, description)
    return None


def secret_findings(path: str, lines: list, taken: set, accepted_of):
    """The register-shaped findings of one file: raw lines (a token in a comment is a token), skipping the lines in
    `taken` (another VUL-SECRET-001 rule already reported them); `accepted_of(line)` reads the accept marker."""
    for i, raw in enumerate(lines, 1):
        if i in taken:
            continue
        for rid, _description, _secret in find(path, raw):
            yield ("VUL-SECRET-001", "CWE-798", f"secret pattern: {rid}", path, i, raw.strip()[:110], SECRET_ADVICE, accepted_of(raw))
