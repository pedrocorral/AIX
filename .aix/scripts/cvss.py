"""Leaf: the CVSS 3.x base score from a vector string (the arithmetic of the specification, no lookup), and the
label bands NVD uses: none 0, low 0.1-3.9, medium 4.0-6.9, high 7.0-8.9, critical 9.0-10.0."""
import math

AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
AC = {"L": 0.77, "H": 0.44}
PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}
PR_C = {"N": 0.85, "L": 0.68, "H": 0.5}
UI = {"N": 0.85, "R": 0.62}
CIA = {"H": 0.56, "L": 0.22, "N": 0.0}
LABELS = ("critical", "high", "medium", "low")


def _roundup(x: float) -> float:
    """CVSS 3.1 Roundup: the smallest number, one decimal, at or above x (integer arithmetic against float drift)."""
    i = int(round(x * 100000))
    return i / 100000.0 if i % 10000 == 0 else (math.floor(i / 10000) + 1) / 10.0


def base_score(vector: str):
    """The base score of a `CVSS:3.0/...` or `CVSS:3.1/...` vector; None when the vector is not one of those."""
    parts = dict(p.split(":", 1) for p in vector.split("/") if ":" in p)
    if parts.get("CVSS") not in ("3.0", "3.1") or not {"AV", "AC", "PR", "UI", "S", "C", "I", "A"} <= set(parts):
        return None
    try:
        changed = parts["S"] == "C"
        iss = 1 - (1 - CIA[parts["C"]]) * (1 - CIA[parts["I"]]) * (1 - CIA[parts["A"]])
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed else 6.42 * iss
        exploitability = 8.22 * AV[parts["AV"]] * AC[parts["AC"]] * (PR_C if changed else PR_U)[parts["PR"]] * UI[parts["UI"]]
    except KeyError:
        return None
    if impact <= 0:
        return 0.0
    return _roundup(min(1.08 * (impact + exploitability), 10)) if changed else _roundup(min(impact + exploitability, 10))


def label(score) -> str:
    """NVD's band for a score; 'unknown' without one."""
    if score is None:
        return "unknown"
    return "critical" if score >= 9.0 else "high" if score >= 7.0 else "medium" if score >= 4.0 else "low" if score > 0 else "none"


def rank(name: str) -> int:
    """Order for thresholds: critical 0, high 1, medium 2, low 3; unknown and none sort last."""
    return LABELS.index(name) if name in LABELS else len(LABELS)
