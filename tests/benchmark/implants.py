"""Section 28 of docs/tests/benchmark-engines.md: the supply-chain implant family (PolinRider) on the planted shapes
of tests/test_implants.py and on the extended projects. Positives: the planted project, ours vs the maintainer's
signature scanner (OpenSourceMalware/PolinRider, polinrider-scanner.sh, cloned into BENCH_DIR). Negatives: every
extended project, each implant finding read by hand. Run: `python tests/benchmark/implants.py [--negatives]`."""
import re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engines
from helpers import env, install
from test_implants import FILES

KIT = Path(__file__).resolve().parents[2]
IMPLANT = re.compile(r"^\s+(\S+):(\d+)\s+((?:code hidden after|code after the export|a second export|createRequire|known marker|VS Code|text where a font|code in a dictionary|propagation script|a \.gitignore line|install hook that)[^\n]*?) \((CWE-(?:506|829))\)", re.M)


def planted(home: Path) -> Path:
    project = home / "sample"
    for rel, text in FILES.items():
        (project / rel).parent.mkdir(parents=True, exist_ok=True); (project / rel).write_text(text, encoding="utf-8")
    (project / "public/fonts/real.woff2").write_bytes(b"wOF2" + bytes(range(64)))
    subprocess.run(["git", "init", "-q"], cwd=project, env=env(home))
    install(home, project)
    return project


def ours(project: Path, home: Path) -> list:
    out = subprocess.run([str(project / ".aix" / "bin" / "aix"), "code", "security"], cwd=project, env=env(home), capture_output=True, text=True).stdout
    return [(m.group(1), int(m.group(2)), m.group(3)) for m in IMPLANT.finditer(out)]


def maintainer_scanner(project: Path) -> str:
    scanner = engines.BENCH / "PolinRider" / "polinrider-scanner.sh"
    if not scanner.is_file():
        return "(scanner not in BENCH_DIR: git clone https://github.com/OpenSourceMalware/PolinRider)"
    r = subprocess.run(["bash", str(scanner), str(project.parent)], capture_output=True, text=True)
    hits = [l.strip() for l in r.stdout.splitlines() if "detected" in l or "found" in l or "injected" in l]
    return f"{len(hits)} finding(s): " + "; ".join(re.sub(r"\x1b\[[0-9;]*m", "", h) for h in hits)


def negatives() -> list:
    lines = []
    for project in engines.PROJECTS:
        tmp = engines.prepare(project)
        out = subprocess.run([str(tmp / ".aix" / "bin" / "aix"), "code", "security"], cwd=tmp, env=engines.env(), capture_output=True, text=True).stdout
        hits = [(m.group(1), int(m.group(2)), m.group(3)) for m in IMPLANT.finditer(out)]
        note = re.search(r"(\d+) npm install step", out)
        lines.append(f"   {project['name']:28s} implant findings {len(hits)}  npm steps with scripts on {note.group(1) if note else 0}" + "".join(f"\n      {f}:{l} {t}" for f, l, t in hits[:5]))
    return lines


def main(argv):
    home = Path(tempfile.mkdtemp(prefix="aix-implants-"))
    project = planted(home)
    found = ours(project, home)
    print(f"== planted sample: ours {len(found)} implant findings")
    print("\n".join(f"   {f}:{l} {t}" for f, l, t in found))
    print("   maintainer's scanner on the same sample:", maintainer_scanner(project))
    if "--negatives" in argv:
        print("== extended projects as negatives"); print("\n".join(negatives()))


if __name__ == "__main__":
    main(sys.argv[1:])
