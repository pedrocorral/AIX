"""Regenerate .aix/scripts/secretrules.py from a gitleaks config (config/gitleaks.toml in the gitleaks repo, MIT).

Maintainer tool, Python 3.11+ (tomllib); the generated module is stdlib-only and runs on 3.9. Every regex is
compiled with Python's `re` after two mechanical fixes (a `(?i)` in the middle of a pattern moves to its start,
`\\z` becomes `\\Z`); a pattern that still fails is dropped and named on stderr.
Usage: python3 tests/benchmark/gitleaks_rules.py path/to/gitleaks.toml [version]"""
import re, sys, tomllib, warnings
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / ".aix" / "scripts" / "secretrules.py"
HEAD = '''"""Leaf: secret patterns, generated from gitleaks {version} config/gitleaks.toml (MIT, github.com/gitleaks/gitleaks)
by tests/benchmark/gitleaks_rules.py. Do not edit: regenerate. Read by secretscan.py.

aix: skip-security-scan generated rule patterns look like the secrets they detect

RULES: (id, description, regex, keywords, entropy, secret_group, allow, path). `keywords` gate the regex (a line without
any of them, case-insensitively, is never matched); `entropy` is the Shannon threshold the secret must reach (None =
no threshold); `secret_group` is the capture group holding the secret (0 = the whole match); `allow` is a list of
allowlists, each a dict with optional `regexes` (on the secret, or on `target` = "line" / "match"), `stopwords`
(lowercase substrings of the secret), `paths`, and `condition` ("AND": every listed kind must match); `path` restricts
the rule to files whose path matches (None = every file). Regexes follow RE2: compile them with re.ASCII.
PATH_RULES: (id, description, path_regex) for files that are secrets by name. GLOBAL_ALLOW: paths, regexes,
stopwords applied to every rule."""

'''


def fix_regex(rx: str) -> str:
    rx = rx.replace("\\z", "\\Z")
    if "(?i)" in rx[1:]:
        rx = "(?i)" + rx.replace("(?i)", "")
    return rx


def compiles(rx: str) -> bool:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            re.compile(rx)
        return True
    except re.error:
        return False


def allowlist(a: dict) -> dict:
    out = {k: [x for x in map(fix_regex, a[k]) if compiles(x)] for k in ("regexes", "paths") if k in a}
    if "stopwords" in a:
        out["stopwords"] = [s.lower() for s in a["stopwords"]]
    out.update({new: a[old] for old, new in (("regexTarget", "target"), ("condition", "condition")) if a.get(old)})
    return out


def convert(cfg: dict) -> tuple:
    rules, path_rules, dropped = [], [], []
    for r in cfg["rules"]:
        allow = [allowlist(a) for a in r.get("allowlists", [])]
        if "regex" not in r:
            path_rules.append((r["id"], r["description"], fix_regex(r["path"])))
            continue
        rx = fix_regex(r["regex"])
        if not compiles(rx):
            dropped.append(r["id"])
            continue
        rules.append((r["id"], r["description"], rx, [k.lower() for k in r.get("keywords", [])], r.get("entropy"), r.get("secretGroup", 1), allow,
                      fix_regex(r["path"]) if "path" in r else None))
    return rules, path_rules, dropped


def main(argv: list):
    cfg = tomllib.load(open(argv[0], "rb"))
    version = argv[1] if len(argv) > 1 else cfg.get("minVersion", "?")
    rules, path_rules, dropped = convert(cfg)
    glob = allowlist(cfg.get("allowlist", {}))
    body = HEAD.format(version=version)
    body += "RULES = [\n" + "".join(f"    {r!r},\n" for r in rules) + "]\n\n"
    body += "PATH_RULES = [\n" + "".join(f"    {r!r},\n" for r in path_rules) + "]\n\n"
    body += f"GLOBAL_ALLOW = {glob!r}\n"
    OUT.write_text(body, encoding="utf-8")
    print(f"wrote {OUT}: {len(rules)} rules, {len(path_rules)} path rules; dropped {dropped or 'none'}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
