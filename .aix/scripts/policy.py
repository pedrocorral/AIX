#!/usr/bin/env python3
"""Leaf: development policies — the cycle a task goes through, as an ordered list of steps the tool can check.

A policy is `policies/<name>.yaml` in any layer (kit, org, custom), like a profile:
    description: Standard cycle for a feature
    order:    [spec, tests, implement, style, modularity, security, docs, coverage, review]
    required: [implement, style, security, docs]
    advised:  [spec, tests, modularity, coverage, review]
    checks:                       # optional extra steps of this policy: id -> command
      lint: npm run lint
Steps come from STEPS below (a check the tool runs, or a skill the agent performs) or from the policy's own `checks`.
Which policy is active, later wins: kit default `anarchy` < a layer's `defaults.yaml` (policy: standard) < the
project's `policy:` in .aix/config.yaml < a task's `policy:` line. `anarchy` is the state with no cycle: no file,
nothing checked, nobody stopped; `none`, `nothing` and `freedom` are its synonyms."""
import shlex, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layers

ROOT = layers.ROOT
ANARCHY = "anarchy"
SYNONYMS = {"none", "nothing", "freedom", "anarchy"}   # all mean: no cycle


def canonical(name) -> str:
    """'none', 'nothing' and 'freedom' are anarchy; anything else is a policy file's name."""
    n = str(name).strip().lower()
    return ANARCHY if n in SYNONYMS or not n else n
STEPS = {  # id -> (kind, what, label)
    "spec":            ("skill", "spec-write-requirement",  "the requirement exists and is approved"),
    "tests":           ("skill", "testing-plan-tests",      "the test specs (TS-*) are planned"),
    "threat":          ("skill", "security-threat-model",   "new attack surface has VUL rows"),
    "implement":       ("skill", "implement-feature",       "the code carries @implements markers"),
    "unit-tests":      ("skill", "testing-write-unit-tests", "the planned tests are automated and green"),
    "audit":           ("skill", "security-audit",          "the audit skills for the categories touched ran"),
    "review":          ("skill", "review-code-review",      "the diff was reviewed against the rules"),
    "drift":           ("skill", "review-doc-drift-check",  "docs and code agree"),
    "style":           ("check", "aix code style --gate",    "no function over a readability limit"),
    "modularity":      ("check", "aix code graph --gate",    "no cycle, no upward dependency"),
    "dead":            ("check", "aix code dead --gate",     "no dead module"),
    "clones":          ("check", "aix code clones --gate",   "no duplicated function"),
    "security":        ("check", "aix code security --gate", "no unreviewed security finding"),
    "vulnerabilities": ("check", "aix code vulnerabilities --gate", "no taint path, known CVE or secret in history"),
    "licenses":        ("check", "aix code licenses --gate",   "no dependency with a copyleft, proprietary or unknown licence undecided"),
    "sbom":            ("check", "aix code sbom --gate",       "the bill of materials is written; no advisory at or above sbom_max_severity, no licence undecided"),
    "docs":            ("check", "aix docs validate",        "IDs, links, indexes and statuses are consistent"),
    "coverage":        ("check", "aix docs coverage",        "the coverage matrix is regenerated"),
    "register":        ("check", "aix docs security --gate", "no VUL row without evidence"),
}


def policies(project: Path = ROOT) -> dict:
    out = {}
    for layer, root in layers.layer_roots(project):
        if layer == "user":
            continue
        for f in sorted((root / "policies").glob("*.yaml")) if (root / "policies").is_dir() else []:
            data = layers.parse_yaml(f.read_text(encoding="utf-8"))
            out[f.stem] = {**data, "name": f.stem, "layer": layer, "path": f}
    return out


def default_of_layers(project: Path = ROOT):
    """(name, layer) from the highest layer's defaults.yaml naming a policy; else (anarchy, kit)."""
    chosen = (ANARCHY, "kit")
    for layer, root in layers.layer_roots(project):
        f = root / "defaults.yaml"
        if layer != "user" and f.exists():
            name = layers.parse_yaml(f.read_text(encoding="utf-8")).get("policy")
            if name:
                chosen = (canonical(name), layer)
    return chosen


def active_name(project: Path = ROOT, task_policy: str = None):
    """(name, where it comes from): task > config > layer default > anarchy."""
    if task_policy:
        return canonical(task_policy), "task"
    cfg = layers.config(project).get("policy")
    if cfg:
        return canonical(cfg), "config"
    return default_of_layers(project)


def active(project: Path = ROOT, task_policy: str = None):
    name, source = active_name(project, task_policy)
    if name == ANARCHY:
        return None, name, source
    pol = policies(project).get(name)
    if pol is None:
        sys.exit(f"aix: policy '{name}' ({source}) does not exist (aix policy list)")
    return pol, name, source


def _step_def(pol: dict, sid: str):
    """(kind, what, label) of a step id: the policy's own check, or a known step."""
    extra = pol.get("checks") or {}
    if sid in extra:
        return "check", str(extra[sid]), f"`{extra[sid]}` passes"
    if sid in STEPS:
        return STEPS[sid]
    sys.exit(f"aix: policy {pol['name']}: unknown step '{sid}' (known: {', '.join(STEPS)}; or define it under checks:)")


def steps_of(pol: dict) -> list:
    """[(id, kind, what, label, level)] in the policy's order; steps at level off are left out."""
    required, advised = set(pol.get("required") or []), set(pol.get("advised") or [])
    out = []
    for sid in pol.get("order") or []:
        level = "required" if sid in required else "advised" if sid in advised else None
        if level:
            out.append((sid, *_step_def(pol, sid), level))
    return out


def run_check(project: Path, command: str) -> int:
    argv = shlex.split(command)
    if argv and argv[0] == "aix":
        launcher = project / ".aix" / "bin" / ("aix.cmd" if sys.platform.startswith("win") else "aix")
        argv = [str(launcher), *argv[1:]]
    try:
        return subprocess.run(argv, cwd=str(project), capture_output=True, text=True).returncode
    except OSError as e:
        print(f"    cannot run `{command}`: {e}")
        return 1


def _run_step(project: Path, step, quiet: bool) -> bool:
    """Run one step; print its line; True unless a required check failed."""
    sid, kind, what, label, level = step
    if kind == "skill":
        if not quiet:
            print(f"  {sid:16s} {level:9s} skill {what}: {label} (the agent does this; not checked here)")
        return True
    rc = run_check(project, what)
    verdict = "pass" if rc == 0 else ("FAIL" if level == "required" else "advice")
    if not quiet or verdict == "FAIL":
        print(f"  {sid:16s} {level:9s} {verdict:7s} {what}")
    return verdict != "FAIL"


def check(project: Path = ROOT, task_policy: str = None, only: str = None, quiet: bool = False) -> bool:
    """Run the checks of the active policy in order; print one line per step. False when a required check failed."""
    pol, name, source = active(project, task_policy)
    if pol is None:
        if not quiet:
            print(f"policy: {ANARCHY} ({source}). Nothing is checked, nobody is stopped. `aix policy list` shows the cycles on offer.")
        return True
    if not quiet:
        print(f"policy: {name} ({source}, {pol['layer']} layer) — {pol.get('description', '')}")
    results = [_run_step(project, step, quiet) for step in steps_of(pol) if not only or step[0] == only]
    ok = all(results)
    if not quiet:
        print("cycle complete: every required check passed" if ok else "cycle NOT complete: a required check failed (fix it, or `aix task block`)")
    return ok


def cycle_section(project: Path = ROOT) -> str:
    """The `## Cycle` section of AGENTS.md: the active policy's steps in order, so agents and the tool follow one list."""
    pol, name, source = active(project)
    if pol is None:
        return ""
    lines = [f"Policy `{name}` ({source}). Follow these steps in order; `aix check` runs the checks and `aix task done` refuses to close a task while a required one fails."]
    for sid, kind, what, label, level in steps_of(pol):
        how = f"skill `{what}`" if kind == "skill" else f"`{what}`"
        lines.append(f"- {sid} ({level}): {how} — {label}")
    return "## Cycle\n" + "\n".join(lines) + "\n\n"
