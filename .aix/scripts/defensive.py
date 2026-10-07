"""`aix code defensive [PATH...] [--all] [--gate] [--report]`: how guarded the Python is. The counts (annotations,
pydantic, doors, inside), the listed spots with what to do, the recommendation the counts call for, and the gate on
the unambiguous ones (RETURN, OPEN). Swallowed exceptions and mutable defaults belong to `aix code style`."""
import sys

from codefiles import ROOT, default_roots, rel, source_files
from findingtags import is_test
import pyguards

GATED = ("RETURN", "OPEN")
ORDER = {"RETURN": 0, "OPEN": 1, "DOOR": 2, "ASSERT": 3}
ADVICE = {"DOOR": "parse it into a strict pydantic model, or check its shape", "ASSERT": "`python -O` removes it; raise ValueError",
          "OPEN": "`with open(...) as f:`", "RETURN": "annotate `-> {ann} | None` or raise"}
HANDLER_ADVICE = "annotate it; FastAPI checks what is typed"
COUNTS = ("funcs", "full", "untyped", "models", "strict_models", "rules", "validators", "calls", "strict_calls", "doors", "unchecked")
MAX_ROWS = 30


def plural(n: int, word: str, words: str = "") -> str:
    return f"{n} {word if n == 1 else (words or word + 's')}"


def _python_files(roots) -> list:
    return [f for f in source_files(roots) if f.suffix == ".py" and not is_test(f)]


def _add(total: dict, facts: dict, file: str):
    for key in COUNTS:
        total[key] += facts[key]
    total["pydantic"] = total["pydantic"] or facts["pydantic"]
    total["spots"] += [(kind, file, line, what) for kind, line, what in facts["spots"]]


def collect(roots) -> dict:
    """The totals over every non-test Python file under the roots, with the spots carrying their file."""
    total = {key: 0 for key in COUNTS}
    total.update(files=0, pydantic=False, spots=[])
    for f in _python_files(roots):
        facts = pyguards.scan(f.read_text(encoding="utf-8", errors="replace"))
        if facts is not None:
            total["files"] += 1
            _add(total, facts, rel(f))
    total["spots"].sort(key=lambda s: (ORDER[s[0]], s[1], s[2]))
    return total


def _count(total: dict, kind: str) -> int:
    return sum(1 for s in total["spots"] if s[0] == kind)


def _guards_line(t: dict) -> str:
    if not t["pydantic"]:
        return "pydantic not imported: nothing checks an argument at run time"
    return (f"pydantic: {plural(t['models'], 'model')} ({t['strict_models']} strict, {plural(t['rules'], 'field')} with a value rule, "
            f"{plural(t['validators'], 'validator')}), {plural(t['calls'], 'function')} under validate_call ({t['strict_calls']} strict)")


def _not_strict(t: dict) -> list:
    parts = []
    if t["strict_models"] < t["models"]:
        parts.append(f"{t['models'] - t['strict_models']} of {plural(t['models'], 'model')}")
    if t["strict_calls"] < t["calls"]:
        parts.append(f"{t['calls'] - t['strict_calls']} of {t['calls']} validate_call")
    return parts


def recommendations(t: dict) -> list:
    """What the counts call for, one line each: types first, then a guard, then strictness, then the open doors."""
    out = []
    if t["untyped"]:
        out.append(f"{t['untyped']} function{'s carry' if t['untyped'] != 1 else ' carries'} no parameter type: annotate {'them' if t['untyped'] != 1 else 'it'} first, no checker works without types")
    if not t["pydantic"] and t["funcs"]:
        out.append("add pydantic: `@validate_call(config=ConfigDict(strict=True))` on the functions behind the doors, outside data parsed into models;"
                   " a project that allows no dependencies writes one decorator of its own")
    elif _not_strict(t):
        out.append(" and ".join(_not_strict(t)) + " are not strict: pydantic converts '5' to 5 silently; set `ConfigDict(strict=True)`")
    elif t["unchecked"]:
        out.append(f"{t['unchecked']} door{'s' if t['unchecked'] != 1 else ''} unchecked: parse each into a model, or check its shape where it is read")
    return [f"  Recommendation: {line}" for line in out]


def _advice(kind: str, what: str) -> str:
    if kind == "DOOR" and "has no type" in what:
        return HANDLER_ADVICE
    ann = what.rsplit("under `-> ", 1)[-1].rstrip("`") if kind == "RETURN" else ""
    return ADVICE[kind].format(ann=ann)


def _spot_lines(t: dict, show_all: bool) -> list:
    spots = t["spots"] if show_all else t["spots"][:MAX_ROWS]
    lines = [f"  {kind:<7} {file}:{line}  {what}   -> {_advice(kind, what)}" for kind, file, line, what in spots]
    if len(t["spots"]) > len(spots):
        lines.append(f"  ... {len(t['spots']) - len(spots)} more (--all)")
    return lines


def report(roots, show_all: bool = False) -> tuple:
    """(text, gated count) for the roots."""
    t = collect(roots)
    gated = sum(_count(t, k) for k in GATED)
    pct = round(100 * t["full"] / t["funcs"]) if t["funcs"] else 0
    lines = [f"Defensive programming — {', '.join(roots)}", "",
             f"  Python: {plural(t['files'], 'file')}, {plural(t['funcs'], 'function')} (tests excluded); JS/TS, Rust, Java and ABAP are not read yet",
             f"  annotations   {t['full']} fully typed ({pct} %), {t['untyped']} with no typed parameter, {_count(t, 'RETURN')} returning None under an annotation that promises a value",
             f"  guards        {_guards_line(t)}",
             f"  doors         {plural(t['doors'], 'read')} of outside data (json, yaml, toml, request bodies, untyped handler parameters), {t['unchecked']} unchecked",
             f"  inside        {plural(_count(t, 'ASSERT'), 'assert')} in production code, {_count(t, 'OPEN')} open() without `with`",
             f"  listed {len(t['spots'])} ({gated} gated)", ""]
    lines += _spot_lines(t, show_all) + ([""] if t["spots"] else [])
    lines.append("  RETURN and OPEN are gated. DOOR and ASSERT are advice. Swallowed exceptions and mutable defaults: aix code style. Fix with: skill implement-code-python")
    return "\n".join(lines + recommendations(t)), gated


def main(args):
    roots = [a for a in args if not a.startswith("--")] or default_roots()
    text, gated = report(roots, "--all" in args)
    print(text)
    if "--report" in args:
        out = ROOT / "docs" / "tests" / "code-defensive.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Defensive programming (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if "--gate" in args and gated:
        sys.exit(f"GATE FAILED: {gated} finding(s)")
    if "--gate" in args:
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
