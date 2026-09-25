"""Leaf: what the kit writes into AGENTS.md and the per-agent instruction files. The managed sections of AGENTS.md
(organisation, scoped instructions, cycle, always-on skills, notes), the instruction blocks assembled from the
layers, and the scoped instructions rendered natively for Copilot and Cursor or listed for the others."""
import re
from pathlib import Path

import agents
from sections import INS_HEADER, MANAGED, replace_section






def render_agents(project: Path, profile) -> bool:
    """Assemble AGENTS.md from the instruction blocks (kit defaults, overridden or extended by layers); the managed
    sections written by other commands are kept as they are. Returns True when the file changed."""
    import layers
    blocks = sorted((v for v in layers.instructions(project, profile).values() if v["block"]), key=lambda v: (v["order"], v["section"]))
    if not blocks:
        return False
    out = []
    for b in blocks:
        body = b["path"].read_text(encoding="utf-8")
        body = body[body.find("\n---", 3) + 4:].strip("\n") if body.startswith("---") else body.strip("\n")
        out.append((f"## {b['section']}\n" if b["section"] else "") + body + "\n")
    text = "\n".join(out)
    f = project / "AGENTS.md"
    old = f.read_text(encoding="utf-8") if f.exists() else ""
    for header in MANAGED:
        kept = _section_text(old, header)
        if kept:
            text = text.rstrip("\n") + "\n\n" + kept
    changed = text != old
    f.write_text(text, encoding="utf-8")
    return changed


def _section_text(text: str, header: str) -> str:
    if header not in text:
        return ""
    body = text.split(header, 1)[1].split("\n## ", 1)[0]
    return header + body.rstrip("\n") + "\n"


def _instruction_body(v: dict) -> str:
    body = v["path"].read_text(encoding="utf-8")
    return body[body.find("\n---", 3) + 4:].lstrip("\n") if body.startswith("---") else body


def _render_native(project: Path, chosen, iid: str, v: dict):
    """The Copilot and Cursor files for one scoped instruction, when those agents are selected."""
    slug = re.sub(r"[^a-z0-9]+", "-", iid.lower()).strip("-")
    slug = slug[4:] if slug.startswith("aix-") else slug  # the file already carries the aix- prefix
    body, apply = _instruction_body(v), (",".join(v["applyTo"]) if v["applyTo"] else "**")
    if "copilot" in chosen:
        gh = project / ".github" / "instructions"
        gh.mkdir(parents=True, exist_ok=True)
        (gh / f"aix-{slug}.instructions.md").write_text(f"---\ndescription: \"{v['description']}\"\napplyTo: \"{apply}\"\n---\n{body}", encoding="utf-8")
    if "cursor" in chosen:
        cur = project / ".cursor" / "rules"
        cur.mkdir(parents=True, exist_ok=True)
        always = "true" if v["always"] or not v["applyTo"] else "false"
        (cur / f"aix-{slug}.mdc").write_text(f"---\ndescription: {v['description']}\nglobs: {apply}\nalwaysApply: {always}\n---\n{body}", encoding="utf-8")


def _instruction_line(project: Path, iid: str, v: dict) -> str:
    shown = v["path"].relative_to(project) if v["path"].is_relative_to(project) else v["path"]
    scope = "always" if v["always"] or not v["applyTo"] else "when touching " + ", ".join(v["applyTo"])
    return f"- `{iid}` ({scope}): read `{shown}` — {v['description']}"


def _write_section(project: Path, files, header: str, section: str):
    for name in files:
        f = project / name
        if f.exists():
            f.write_text(replace_section(f.read_text(encoding="utf-8"), header, section), encoding="utf-8")


def _clear_rendered(project: Path):
    for d, pat in ((project / ".github" / "instructions", "aix-*.instructions.md"), (project / ".cursor" / "rules", "aix-*.mdc")):
        for old in (d.glob(pat) if d.is_dir() else []):
            old.unlink()


def _rendered_where(chosen) -> list:
    return [x for x, ok in (("AGENTS.md", True), (".github/instructions/aix-*.instructions.md", "copilot" in chosen), (".cursor/rules/aix-*.mdc", "cursor" in chosen)) if ok]


def render_instructions(project: Path, profile):
    """Scoped instructions -> native files per agent (git-ignored, regenerated) + managed sections in AGENTS.md/GEMINI.md."""
    import layers, policy
    if render_agents(project, profile):
        print("  AGENTS.md assembled from instruction blocks")
    ins = {k: v for k, v in layers.instructions(project, profile).items() if not v["block"]}
    chosen = agents.selected(project)
    _clear_rendered(project)
    lines = []
    for iid, v in sorted(ins.items()):
        _render_native(project, chosen, iid, v)
        lines.append(_instruction_line(project, iid, v))
    section = (INS_HEADER + "\nRead these before working on matching files:\n" + "\n".join(lines) + "\n\n") if lines else ""
    _write_section(project, ("AGENTS.md", "GEMINI.md"), INS_HEADER, section)
    _write_section(project, ("AGENTS.md",), "## Cycle", policy.cycle_section(project))
    org = (profile or {}).get("router") or _org_fragment(project)
    _write_section(project, ("AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md"), "## Organisation", ("## Organisation\n" + org.strip() + "\n\n") if org else "")
    if lines:
        print(f"  rendered {len(lines)} scoped instruction(s) -> {', '.join(_rendered_where(chosen))}")


def _org_fragment(project: Path) -> str:
    for d in (project / ".aix" / "custom", project / ".aix" / "org"):
        f = d / "AGENTS.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return ""


