#!/usr/bin/env python3
"""Skill catalogue data (leaf module: depends on nothing else in scripts/).
Used by skills.py, extern.py and doctor.py.

Activation levels (derived, not configured):
  always       named in AGENTS.md, so every session runs or may need them (resume, workflow, handoff, conflicts)
  orchestrator entry-point skills that chain other skills
  on-demand    invoked by an orchestrator, the user, or the agent when the description matches
Disabled skills are listed in .aix/config.yaml under `disabled_skills:` and are not linked by `aix install`."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".aix" / "skills"
MANIFEST = ROOT / ".aix" / "config.yaml"
AGENTS = ROOT / "AGENTS.md"
import agents
TARGETS = [a["skills"] for a in agents.AGENTS.values() if a["skills"]]
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


def _active_skills() -> dict:
    """class -> the implementation the layers and the profile chose."""
    import layers
    active, _ = layers.resolve(ROOT, layers.active_profile(ROOT))
    return active


def _entries(active: dict) -> dict:
    """flat-name -> the catalogue record, read from each chosen SKILL.md."""
    out, reg = {}, registry_groups()
    for flat, info in sorted(active.items()):
        md = info["path"] / "SKILL.md"
        text = md.read_text(encoding="utf-8")
        out[flat] = {
            "path": info["path"], "category": info["path"].parent.name,
            "group": skill_group(md, text, flat, reg),
            "description": front_matter(text, "description"),
            "orchestrator": "orchestrator" in text.lower()[:600],
            "layer": info["layer"], "shadowed": info["shadowed"], "manual": info["manual"], "id": info["id"], "version": info["version"], "chosen_by": info["chosen_by"],
        }
    return out


def catalogue():
    """All leaf skills: dict flat-name -> {path, category, group, description, orchestrator}."""
    return _entries(_active_skills())


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
    return [RUNTIME[t] for t in agents.skill_dirs(ROOT) if (ROOT / t / flat).exists()]


def unlink_everywhere(flat, project=None, targets=None):
    """Remove a skill's link (or copied folder) from every agent folder; the project's and the selected agents' by default."""
    import shutil
    project = project or ROOT
    for t in (targets if targets is not None else agents.skill_dirs(project)):
        p = project / t / flat
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)


def _use_entries(block: str) -> dict:
    entries = {}
    for line in block.splitlines():
        k, _, v = line.strip().partition(":")
        if k and v.strip():
            entries[k.strip()] = v.split("#")[0].strip().strip("'\"")
    return entries


def set_use(flat, iid):
    """Write (iid) or drop (iid=None) the `use:` entry of one class in .aix/config.yaml."""
    import re
    cfg = ROOT / ".aix" / "config.yaml"
    text = cfg.read_text(encoding="utf-8")
    m = re.search(r"^use:[^\n]*\n((?:[ \t]+\S[^\n]*\n?)*)", text, re.M)
    entries = {k: v for k, v in _use_entries(m.group(1) if m else "").items() if k.replace("/", "-") != flat}
    if iid:
        entries[flat] = iid
    block = "" if not entries else "use:   # skill implementation per class, managed by `aix skills use`\n" + "".join(f"  {k}: \"{v}\"\n" for k, v in sorted(entries.items()))
    if m:
        text = text[:m.start()] + block + text[m.end():]
    elif block:
        text = text.rstrip("\n") + "\n" + block
    cfg.write_text(text, encoding="utf-8")
