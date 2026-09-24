#!/usr/bin/env python3
"""Third-party skills: `aix skills add|remove|update|registry|always|on-demand`.

Known skills live in .aix/skills/extern/registry.json (name -> GitHub repo + sub-path + evidence). `add` downloads the
repo tarball over HTTPS (no git needed), copies the skill folder to .aix/skills/extern/<name>/, records provenance in
.aix-source and links it into every runtime. `--always` also names it in AGENTS.md, .github/copilot-instructions.md,
.cursor/rules/aix.mdc and GEMINI.md so every session applies it.

Two kinds of entry. Without `class`, the skill keeps its bare name (caveman, ponytail): something the kit has no class
for. With `class` (e.g. "coach/grill-me"), the download is one more implementation of that kit class: its SKILL.md gets
`name: <class flat>`, `class:` and `id: "@owner/name"`, `add` selects it (config `use:`) and the runtimes see it as the
class folder (coach-grill-me); `aix skills use CLASS default` goes back to the kit's; `remove` drops the selection."""
import io, json, re, shutil, sys, tarfile, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTERN = ROOT / ".aix" / "skills" / "extern"
REGISTRY = EXTERN / "registry.json"
AGENTS = ROOT / "AGENTS.md"
ALWAYS_HEADER = "## Always-on skills"
# file -> where that runtime finds the skill folder (Copilot reads .github/skills, Cursor .cursor/skills,
# Gemini CLI .agents/skills; Antigravity reads AGENTS.md itself)
ALWAYS_FILES = {
    ROOT / "AGENTS.md": "Apply these in every session, before anything else. Read `<your runtime's skills dir>/<name>/SKILL.md` (e.g. `.claude/skills/`, `.opencode/skills/`, `.agents/skills/`):",
    ROOT / ".github" / "copilot-instructions.md": "Apply these in every session, before anything else. Read `.github/skills/<name>/SKILL.md` first:",
    ROOT / ".cursor" / "rules" / "aix.mdc": "Apply these in every session, before anything else. Read `.cursor/skills/<name>/SKILL.md` first:",
    ROOT / "GEMINI.md": "Apply these in every session, before anything else. Read `.agents/skills/<name>/SKILL.md` first:",
}


def registry():
    return {k: v for k, v in json.loads(REGISTRY.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def fetch_repo(repo: str):
    """Return (tarball, top folder) of the default branch: main, then master."""
    for branch in ("main", "master"):
        url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"
        try:
            data = urllib.request.urlopen(url, timeout=60).read()
        except Exception:
            continue
        tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
        return tar, tar.getnames()[0].split("/")[0]
    sys.exit(f"cannot download {repo} (tried main and master)")


def extract_subdir(tar, top: str, sub: str, dest: Path):
    prefix = f"{top}/{sub}/"
    members = [m for m in tar.getmembers() if m.name.startswith(prefix) and m.isfile()]
    if not members:
        sys.exit(f"{sub} not found in repository")
    for m in members:
        rel = Path(m.name[len(prefix):])
        if ".." in rel.parts:
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(tar.extractfile(m).read())


def fix_name(skill_md: Path, name: str):
    """Runtimes and `aix docs validate` require front-matter name == folder name."""
    t = skill_md.read_text(encoding="utf-8")
    t2 = re.sub(r"^name:.*$", f"name: {name}", t, count=1, flags=re.M)
    if t2 != t:
        skill_md.write_text(t2, encoding="utf-8")


def fix_class(skill_md: Path, cls: str, iid: str):
    """Make a downloaded skill an implementation of a kit class: name = class flat name, class:, id: in the front matter."""
    t = skill_md.read_text(encoding="utf-8")
    t = re.sub(r"^(class|id):.*\n", "", t, flags=re.M)
    t = re.sub(r"^name:.*$", f"name: {cls.replace('/', '-')}\nclass: {cls}\nid: \"{iid}\"", t, count=1, flags=re.M)
    skill_md.write_text(t, encoding="utf-8")


def runtime_tools():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import install_skills, catalog
    return install_skills, catalog


def install_one(name: str, entry: dict):
    dest = EXTERN / name
    if dest.exists():
        shutil.rmtree(dest)
    tar, top = fetch_repo(entry["repo"])
    extract_subdir(tar, top, entry["path"], dest)
    if not (dest / "SKILL.md").exists():
        shutil.rmtree(dest)
        sys.exit(f"{entry['repo']}/{entry['path']} has no SKILL.md")
    cls = entry.get("class")
    iid = f"@{entry['repo'].split('/')[0]}/{name}"
    fix_class(dest / "SKILL.md", cls, iid) if cls else fix_name(dest / "SKILL.md", name)
    prov = {"repo": entry["repo"], "path": entry["path"], "group": entry.get("group", "specific"), "fetched": date.today().isoformat()}
    if cls:
        prov["class"] = cls
    (dest / ".aix-source").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    inst, sk = runtime_tools()
    if cls:
        flat = cls.replace("/", "-")
        sk.set_use(flat, iid)
        inst.install_into(ROOT, copy=False)
        print(f"  {name}: {entry['repo']}/{entry['path']} -> .aix/skills/extern/{name}; now the implementation of {flat} (id {iid}; back with `aix skills use {flat} default`)")
        return
    for t in inst.TARGETS:
        inst.link_or_copy(dest, ROOT / t / name, copy=False)
    print(f"  {name}: {entry['repo']}/{entry['path']} -> .aix/skills/extern/{name} (linked into all runtimes)")


# ---- always-on wiring -------------------------------------------------------------------------------------

def always_on_names(text: str):
    sec = text.split(ALWAYS_HEADER, 1)
    return re.findall(r"^- `([^`]+)`", sec[1].split("\n## ", 1)[0], re.M) if len(sec) > 1 else []


def set_always(text: str, names, intro: str):
    """The `## Always-on skills` section rewritten with `names` (removed when empty); the rest of the file untouched."""
    import install_skills
    block = "" if not names else ALWAYS_HEADER + "\n" + intro + "\n" + "".join(f"- `{n}`\n" for n in names) + "\n"
    return install_skills._replace_section(text, ALWAYS_HEADER, block)


def mark_always(name: str, on: bool):
    for f, intro in ALWAYS_FILES.items():
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        names = always_on_names(t)
        names = sorted(set(names) | {name}) if on else [n for n in names if n != name]
        f.write_text(set_always(t, names, intro), encoding="utf-8")


def known_skill(name: str) -> bool:
    _, sk = runtime_tools()
    return name in sk.catalogue()


# ---- commands ---------------------------------------------------------------------------------------------

def cmd_registry(group=None, only=None):
    reg = registry()
    for n, e in reg.items():
        if (group and e.get("group", "specific") != group) or (only and n != only):
            continue
        state = "installed" if (EXTERN / n).exists() else "available"
        print(f"{n:32s} {e.get('group', 'specific'):9s} {e['kind']:7s} {state:10s} {e['repo']}  [{e['license']}]" + (f"  class {e['class']}" if e.get("class") else ""))
        print(f"    {e['description']}\n    evidence: {e['evidence']}")
        if e.get("also"):
            print(f"    same repo, add with: aix skills add {n} --extra " + ",".join(e["also"]))
    print(f"\n{len(reg)} known skills. Edit .aix/skills/extern/registry.json to add more (require evidence). "
          "An entry with `class` is installed as that kit class's implementation (selected on add); one without keeps its bare name.")


def _install_extras(name: str, entry: dict, extra):
    for x in extra:
        if x not in entry.get("also", []):
            sys.exit(f"'{x}' is not a listed extra of {name}")
        install_one(x, {"repo": entry["repo"], "path": entry["path"].rsplit("/", 1)[0] + "/" + x, "group": "specific"})


def _make_always(name: str, entry: dict, styles_on: list):
    if entry["kind"] == "style" and any(s != name for s in styles_on):
        print(f"  warning: another style skill is already always-on ({', '.join(styles_on)}); two output styles conflict")
    mark_always(name, True)
    print(f"  {name}: always-on (AGENTS.md, .github/copilot-instructions.md, .cursor/rules/aix.mdc, GEMINI.md)")


def cmd_add(names, always: bool, on_demand: bool, extra):
    """General skills become always-on unless --on-demand; specific ones stay on-demand unless --always."""
    reg = registry()
    styles_on = [n for n in always_on_names(AGENTS.read_text(encoding="utf-8")) if reg.get(n, {}).get("kind") == "style"]
    for name in names:
        entry = reg.get(name) or sys.exit(f"'{name}' is not in the registry; see `aix skills registry`")
        install_one(name, entry)
        _install_extras(name, entry, extra)
        if always or (entry.get("group") == "general" and not on_demand):
            _make_always(name, entry, styles_on)


def cmd_remove(names):
    _, sk = runtime_tools()
    for name in names:
        dest = EXTERN / name
        if not dest.exists():
            sys.exit(f"{name} is not installed under .aix/skills/extern/")
        src = json.loads((dest / ".aix-source").read_text(encoding="utf-8")) if (dest / ".aix-source").exists() else {}
        if src.get("class"):
            flat = src["class"].replace("/", "-")
            shutil.rmtree(dest)
            sk.set_use(flat, None)
            inst, _ = runtime_tools()
            inst.install_into(ROOT, copy=False)
            print(f"  removed {name}; {flat} is back to layer precedence")
            continue
        sk.unlink_everywhere(name)
        shutil.rmtree(dest)
        mark_always(name, False)
        print(f"  removed {name}")


def cmd_update(names):
    targets = names or [p.name for p in EXTERN.iterdir() if (p / ".aix-source").exists()]
    for name in targets:
        src = json.loads((EXTERN / name / ".aix-source").read_text(encoding="utf-8"))
        install_one(name, {k: src[k] for k in ("repo", "path", "group", "class") if k in src})


def cmd_always(name: str, on: bool):
    if not known_skill(name):
        sys.exit(f"unknown skill {name}")
    mark_always(name, on)
    print(f"  {name}: {'always-on' if on else 'on-demand'}")


USAGE = "usage: aix skills registry | add NAME... [--always|--on-demand] [--extra a,b] | remove NAME... | update [NAME...] | always NAME | on-demand NAME"


def main(args):
    sub, rest = (args[0], list(args[1:])) if args else ("registry", [])
    always, on_demand, extra = "--always" in rest, "--on-demand" in rest, []
    if "--extra" in rest:
        i = rest.index("--extra")
        extra = rest[i + 1].split(",")
        del rest[i:i + 2]
    rest = [r for r in rest if r not in ("--always", "--on-demand")]
    actions = {
        "registry": lambda: cmd_registry(),
        "add": lambda: cmd_add(rest, always, on_demand, extra),
        "remove": lambda: cmd_remove(rest),
        "update": lambda: cmd_update(rest),
        "always": lambda: cmd_always(rest[0], True),
        "on-demand": lambda: cmd_always(rest[0], False),
    }
    if sub not in actions or (sub in ("add", "remove", "always", "on-demand") and not rest):
        sys.exit(USAGE)
    actions[sub]()


if __name__ == "__main__":
    main(sys.argv[1:])
