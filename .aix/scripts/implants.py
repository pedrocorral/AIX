"""Leaf: supply-chain implants in a repository, the PolinRider family (GitHub community discussion 188732,
opensourcemalware.com; benchmark section 28). Shape-based, so a rotated marker still shows: code hidden after a run
of whitespace in a JavaScript config file, code after the file's export, a duplicate export, `createRequire` in a
config; a VS Code task that runs when the folder opens, settings that allow it or hide the terminal; a file under a
`fonts/` folder, or `.llf`, that is text instead of a font; `spellright.dict` holding code; the propagation scripts
`temp_auto_push.bat` and `config.bat` and a `.gitignore` line hiding them; a package.json install hook that runs code
from the network or decodes base64. Plus the history view (a config file that grew 20x in one commit, a forced update
in the reflog) and the note on `npm install` steps that run lifecycle scripts. The known markers themselves are a
`*` row of securityrules. Findings to review, never proof."""
import re, subprocess
from pathlib import Path

from codefiles import ROOT, rel

ROW, CWE_IMPLANT, CWE_HOOK = "VUL-DEP-001", "CWE-506", "CWE-829"
CONFIG = re.compile(r"^(?:next|postcss|tailwind|eslint|vite|vitest|vue|astro|nuxt|svelte|webpack|babel|jest|rollup|prettier)\.config\.(?:[cm]?js|[cm]?ts)$")
PADDED = re.compile(r"[ \t]{100,}\S")
EXPORT = re.compile(r"^\s*(?:export\s+default\b|module\.exports\s*=)")
FONT_MAGIC = (b"wOF2", b"wOFF", b"\x00\x01\x00\x00", b"true", b"OTTO")
FONT_SUFFIX = (".woff2", ".woff", ".ttf", ".otf", ".eot", ".llf")
TEXT_BY_FORMAT = (".svg", ".md", ".txt", ".css", ".scss", ".less", ".json", ".html", ".xml", ".js", ".ts")   # an SVG font is text, so is a stylesheet next to the fonts
BAT_NAMES = ("temp_auto_push.bat", "config.bat")
HOOK_RUNS = re.compile(r"\bnode\s+-e\b|\bcurl\b|\bwget\b|\bbase64\b|\bpowershell\b|Invoke-(?:WebRequest|Expression)|\biex\b", re.I)
NPM_INSTALL = re.compile(r"\bnpm\s+(?:install|ci|i)\b(?![^\n]*--ignore-scripts)")
ADVICE = {"padding": "open the file with whitespace rendering on, delete everything after the legitimate export, and rotate every secret the build could read",
          "export": "nothing belongs after the export; delete it, then check the file's history for the commit that added it",
          "task": "delete the task; a task that runs on folder open executes before anyone reads the code (VS Code: task.allowAutomaticTasks off)",
          "font": "a font is binary; a text file under fonts/ is a payload carrier: delete it and search the configs for what loads it",
          "bat": "the campaign's propagation script; delete it, revoke the tokens on this machine, and read the reflog for amended commits",
          "hook": "an install hook must not fetch or decode code; `npm ci --ignore-scripts` until it is reviewed",
          "growth": "read the commit: a config file that grew twenty-fold in one change carries something that is not configuration",
          "forced": "a forced update rewrote history: compare the rewritten range with a copy you trust before building"}


SNIPPET = 110
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "target", ".venv", "venv"}


def _finding(cwe: str, title: str, where: tuple, snippet: str, advice: str) -> tuple:
    """`where` is (file, line)."""
    return (ROW, cwe, title, rel(where[0]), where[1], snippet[:SNIPPET], ADVICE[advice], None)


# ---- config files ---------------------------------------------------------------------------------------------------

def _config_findings(f: Path, lines: list) -> list:
    out = []
    exports = [i for i, l in enumerate(lines, 1) if EXPORT.match(l)]
    for i, l in enumerate(lines, 1):
        if PADDED.search(l):
            out.append(_finding(CWE_IMPLANT, "code hidden after whitespace padding in a config file", (f, i), l.strip()[:60], "padding"))
        if "createRequire" in l:
            out.append(_finding(CWE_IMPLANT, "createRequire in a config file", (f, i), l.strip(), "export"))
    if len(exports) > 1:
        out.append(_finding(CWE_IMPLANT, "a second export in a config file", (f, exports[-1]), lines[exports[-1] - 1].strip(), "export"))
    out += _after_export(f, lines, exports)
    return out


def _after_export(f: Path, lines: list, exports: list) -> list:
    """Code on a line after the export statement ends (its own line ends with `;` or `}`): nothing belongs there."""
    if not exports:
        return []
    end = next((i for i in range(exports[-1], len(lines) + 1) if lines[i - 1].rstrip().endswith((";", "}"))), None)
    if end is None:
        return []
    later = [(i, l) for i, l in enumerate(lines[end:], end + 1) if l.strip() and not l.strip().startswith(("//", "/*", "*"))]
    return [_finding(CWE_IMPLANT, "code after the export of a config file", (f, later[0][0]), later[0][1].strip(), "export")] if later else []


# ---- editor, fonts, scripts, hooks ----------------------------------------------------------------------------------

def _vscode_findings(f: Path, lines: list) -> list:
    out = []
    for i, l in enumerate(lines, 1):
        if f.name == "tasks.json" and re.search(r'"runOn"\s*:\s*"folderOpen"', l):
            out.append(_finding(CWE_IMPLANT, "VS Code task that runs when the folder opens", (f, i), l.strip(), "task"))
        if f.name == "tasks.json" and re.search(r"curl[^\n]*\|[^\n]*(?:sh|bash)|node\s+-e\b|powershell", l):
            out.append(_finding(CWE_IMPLANT, "VS Code task that runs fetched or inline code", (f, i), l.strip(), "task"))
        if f.name == "settings.json" and re.search(r'"task\.allowAutomaticTasks"\s*:\s*(?:true|"on")|"terminal\.integrated\.hideOnStartup"', l):
            out.append(_finding(CWE_IMPLANT, "VS Code setting that lets tasks run unseen", (f, i), l.strip(), "task"))
    return out


HEAD_BYTES = 64


def _font_place(f: Path) -> bool:
    """A binary font suffix anywhere, or a file under a fonts folder that is not text by its own format (an SVG font,
    a stylesheet, a licence)."""
    if f.suffix in FONT_SUFFIX:
        return True
    return "fonts" in f.parts and f.suffix not in TEXT_BY_FORMAT and f.stem.upper() not in ("LICENSE", "README", "OFL")


def _is_text(head: bytes) -> bool:
    return bool(head) and not head.startswith(FONT_MAGIC) and all(32 <= b <= 126 or b in (9, 10, 13) for b in head)


def _font_finding(f: Path) -> list:
    """A file where a font should be, holding text."""
    if not _font_place(f):
        return []
    head = f.read_bytes()[:HEAD_BYTES]
    return [_finding(CWE_IMPLANT, "text where a font should be", (f, 1), head.decode("ascii", "replace").strip(), "font")] if _is_text(head) else []


def _named_findings(f: Path, lines: list) -> list:
    out = []
    if f.name in BAT_NAMES:
        out.append(_finding(CWE_IMPLANT, "propagation script of the campaign", (f, 1), (lines[0] if lines else "")[:60], "bat"))
    if f.name == ".gitignore":
        out += [_finding(CWE_IMPLANT, "a .gitignore line hiding the campaign's script", (f, i), l.strip(), "bat") for i, l in enumerate(lines, 1) if l.strip() in BAT_NAMES]
    if f.name == "spellright.dict" and any(re.search(r"\bfunction\b|\beval\b|require\(", l) for l in lines):
        out.append(_finding(CWE_IMPLANT, "code in a dictionary file", (f, 1), "", "font"))
    return out


def _hook_findings(f: Path, lines: list) -> list:
    if f.name != "package.json":
        return []
    return [_finding(CWE_HOOK, "install hook that fetches or decodes code", (f, i), l.strip(), "hook")
            for i, l in enumerate(lines, 1) if re.search(r'"(?:pre|post)?install"\s*:', l) and HOOK_RUNS.search(l)]


def findings(f: Path) -> list:
    """Every implant finding of one file; binary files are read for the font check only."""
    out = _font_finding(f)
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return out
    if CONFIG.match(f.name):
        out += _config_findings(f, lines)
    if ".vscode" in f.parts:
        out += _vscode_findings(f, lines)
    return out + _named_findings(f, lines) + _hook_findings(f, lines)


# ---- the note, the history ------------------------------------------------------------------------------------------

def install_note() -> str:
    """How many workflow and Dockerfile steps of the project run `npm install` with lifecycle scripts on."""
    files = [f for f in ROOT.rglob("*") if f.is_file() and "node_modules" not in f.parts and ".git" not in f.parts
             and (f.name.startswith("Dockerfile") or (".github" in f.parts and f.suffix in (".yml", ".yaml")))]
    n = sum(len(NPM_INSTALL.findall(f.read_text(encoding="utf-8", errors="replace"))) for f in files)
    return f"  {n} npm install step(s) in workflows or Dockerfiles run lifecycle scripts: add `--ignore-scripts` where the build allows it (section 28)" if n else ""


def _git(args: list, cwd: Path) -> str:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _growth(f: Path, cwd: Path) -> list:
    """The commit in which a config file grew from under 500 bytes to over 2 KB."""
    commits = _git(["log", "--format=%H", "--", str(f)], cwd).split()
    sizes = [(c, int(s or 0)) for c in commits for s in [_git(["cat-file", "-s", f"{c}:{rel(f)}"], cwd).strip()]]
    for (newer, big), (_older, small) in zip(sizes, sizes[1:]):
        if small < 500 < 2048 < big:
            return [_finding(CWE_IMPLANT, f"config file grew from {small} to {big} bytes in one commit", (f, 1), newer[:12], "growth")]
    return []


def _configs_under(paths) -> list:
    out = []
    for p in paths:
        base = ROOT / p if not Path(p).is_absolute() else Path(p)
        if base.is_dir():
            out += [x for x in base.rglob("*") if x.is_file() and CONFIG.match(x.name) and not SKIP_DIRS & set(x.parts)]
    return out


def _forced_updates() -> list:
    out = []
    for line in _git(["reflog", "show", "--all"], ROOT).splitlines():
        if "forced-update" in line:
            ref = line.split()[1].rstrip(":") if len(line.split()) > 1 else ".git"
            out.append((ROW, CWE_IMPLANT, "forced update in the reflog", ref, 1, line[:SNIPPET], ADVICE["forced"], None))
    return out


def history_findings(paths) -> list:
    """Config files that grew twenty-fold in one commit, and forced updates in the reflog of a remote branch."""
    if not (ROOT / ".git").exists():
        return []
    return [fx for f in _configs_under(paths) for fx in _growth(f, ROOT)] + _forced_updates()


def root_findings() -> list:
    """The implant findings over the whole project, not only the code roots: an editor task, a font folder, a script
    or a .gitignore at the root are where the campaign puts them."""
    files = (f for f in ROOT.rglob("*") if f.is_file() and not SKIP_DIRS & set(f.parts))
    return [fx for f in files for fx in findings(f)]


def npm_cli_size() -> int:
    """The size of npm's lib/cli.js on this machine, 0 when npm is not there; the campaign bloats it to about 1 MB."""
    import shutil
    npm = shutil.which("npm")
    if not npm:
        return 0
    prefix = Path(npm).resolve().parent.parent
    for candidate in (prefix / "lib" / "node_modules" / "npm" / "lib" / "cli.js", prefix / "node_modules" / "npm" / "lib" / "cli.js"):
        if candidate.is_file():
            return candidate.stat().st_size
    return 0
