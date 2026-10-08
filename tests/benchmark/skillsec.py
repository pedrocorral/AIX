"""Section 29 of docs/tests/benchmark-engines.md: the skill-security scanner (skillsec.py) against NVIDIA
SkillSpector on the same inputs. Positives: the planted sample of tests/test_skillsec.py, one malicious skill with
every shape and its safe twin. Negatives: the kit's own skills and the 29 downloaded registry skills, every finding
read by hand. SkillSpector comes from the bench venv (BENCH_DIR/venv/bin/skillspector); it is skipped and the report
says so when it is not there. Not part of the test suite. Run: `python tests/benchmark/skillsec.py [--real DIR]`
where DIR holds a copy of the installed registry skills under .aix/skills/extern."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".aix" / "scripts"))
import skillsec
from test_skillsec import SKILL, SCRIPT, SAFE_SCRIPT

KIT = Path(__file__).resolve().parents[2]
BENCH = Path(os.environ.get("BENCH_DIR", Path.home() / ".cache" / "aix" / "bench"))
SP = BENCH / "venv" / "bin" / "skillspector"


def write_sample(root: Path):
    bad = root / "sample"; (bad / "scripts").mkdir(parents=True)
    (bad / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (bad / "scripts" / "run.sh").write_text(SCRIPT, encoding="utf-8")
    safe = root / "safe"; (safe / "scripts").mkdir(parents=True)
    (safe / "SKILL.md").write_text("---\nname: safe\ndescription: a clean skill\n---\n\n# Safe\n\nDo the task and tell the user what you did.\n", encoding="utf-8")
    (safe / "scripts" / "ok.sh").write_text(SAFE_SCRIPT, encoding="utf-8")
    return bad, safe


def ours(skill_dir: Path) -> int:
    return len(skillsec.scan_dir(skill_dir, str))


def skillspector(target: Path):
    """(severity, issue count) of SkillSpector on a folder, or None when it is not installed or fails."""
    if not SP.exists():
        return None
    out = Path(tempfile.mkdtemp()) / "sp.json"
    subprocess.run([str(SP), "scan", str(target), "--no-llm", "--format", "json", "-o", str(out)], capture_output=True, text=True)
    if not out.exists():
        return None
    d = json.loads(out.read_text())
    shutil.rmtree(out.parent, ignore_errors=True)
    return d["risk_assessment"]["severity"], len(d["issues"])


def main():
    real = None
    if "--real" in sys.argv:
        real = Path(sys.argv[sys.argv.index("--real") + 1])
    tmp = Path(tempfile.mkdtemp())
    bad, safe = write_sample(tmp)
    print("== the planted sample (positives)")
    print(f"  malicious skill:  ours {ours(bad)}   skillspector {skillspector(bad)}")
    print(f"  safe twin:        ours {ours(safe)}   skillspector {skillspector(safe)}")
    print("== the real skills (negatives), every finding read by hand")
    kit_skills = KIT / ".aix" / "skills"
    kit_total = len(skillsec.scan_tree(KIT, str))
    print(f"  kit's own skills + instruction files:  ours {kit_total}   skillspector {skillspector(kit_skills) if SP.exists() else 'n/a'}")
    if real and (real / ".aix" / "skills" / "extern").is_dir():
        extern = real / ".aix" / "skills" / "extern"
        dirs = [d for d in extern.iterdir() if d.is_dir()]
        r = sum(ours(d) for d in dirs)
        print(f"  {len(dirs)} downloaded registry skills:        ours {r}   skillspector {skillspector(extern)}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
