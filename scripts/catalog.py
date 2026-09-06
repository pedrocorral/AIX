#!/usr/bin/env python3
"""Skill catalogue data (leaf module: depends on nothing else in scripts/).
Used by skills.py, extern.py and doctor.py.

Activation levels (derived, not configured):
  always       named in AGENTS.md, so every session runs or may need them (resume, workflow, handoff, conflicts)
  orchestrator entry-point skills that chain other skills
  on-demand    invoked by an orchestrator, the user, or the agent when the description matches
Disabled skills are listed in framework.yaml under `disabled_skills:` and are not linked by `aix install`."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "framework.yaml"
AGENTS = ROOT / "AGENTS.md"
TARGETS = [".opencode/skills", ".claude/skills", ".github/skills", ".agents/skills", ".cursor/skills"]
RUNTIME = {".opencode/skills": "opencode", ".claude/skills": "claude", ".github/skills": "copilot",
           ".agents/skills": "agents", ".cursor/skills": "cursor"}   # agents = agentskills.io dir: Antigravity, Gemini CLI, VS Code


def front_matter(text: str, key: str) -> str:
    """Value of a front-matter key; YAML block scalars (`>` / `|`) are joined from their indented lines."""
    m = re.search(rf"^{key}:[ \t]*(.*)$", text, re.M)
    if not m:
        return ""
    value = m.group(1).strip()
    if value not in (">", "|", ">-", "|-"):
        return value
    lines = []
    for line in text[m.end():].splitlines()[1:]:
        if line.startswith((" ", "\t")):
            lines.append(line.strip())
        else:
            break
    return " ".join(lines)


def registry_groups():
    import json
    reg = SKILLS / "extern" / "registry.json"
    if not reg.exists():
        return {}
    return {k: v.get("group", "specific") for k, v in json.loads(reg.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def skill_group(md: Path, text: str, flat: str, reg: dict) -> str:
    """general = behaviour for every session; specific = one job. Front-matter `group:` wins, then .aix-source, then registry."""
    import json
    g = front_matter(text, "group")
    if not g and (md.parent / ".aix-source").exists():
        g = json.loads((md.parent / ".aix-source").read_text(encoding="utf-8")).get("group", "")
    return g or reg.get(flat, "specific")


def catalogue():
    """All leaf skills: dict flat-name -> {path, category, group, description, orchestrator}."""
    out, reg = {}, registry_groups()
    for md in sorted(SKILLS.rglob("SKILL.md")):
        rel = md.parent.relative_to(SKILLS)
        text = md.read_text(encoding="utf-8")
        flat = "-".join(rel.parts[1:]) if rel.parts[0] == "extern" else "-".join(rel.parts)
        out[flat] = {
            "path": md.parent, "category": rel.parts[0],
            "group": skill_group(md, text, flat, reg),
            "description": front_matter(text, "description"),
            "orchestrator": "orchestrator" in text.lower()[:600],
        }
    return out


def always_on():
    """Skills AGENTS.md names explicitly: the agent contract requires them regardless of the request."""
    return set(re.findall(r"`([a-z][a-z0-9-]+)`", AGENTS.read_text(encoding="utf-8")))


def disabled():
    m = re.search(r"^disabled_skills:\s*\[(.*?)\]", MANIFEST.read_text(encoding="utf-8"), re.M)
    return {s.strip() for s in m.group(1).split(",") if s.strip()} if m else set()


def set_disabled(names):
    line = "disabled_skills: [" + ", ".join(sorted(names)) + "]   # managed by `aix skills enable|disable`"
    text = MANIFEST.read_text(encoding="utf-8")
    if re.search(r"^disabled_skills:", text, re.M):
        text = re.sub(r"^disabled_skills:.*$", line, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    MANIFEST.write_text(text, encoding="utf-8")


def installed_in(flat: str):
    return [RUNTIME[t] for t in TARGETS if (ROOT / t / flat).exists()]


def unlink_everywhere(flat):
    import shutil
    for t in TARGETS:
        p = ROOT / t / flat
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)


