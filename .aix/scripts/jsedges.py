"""Leaf: the import edges of one JavaScript/TypeScript file, resolved to project files. Comments are taken out first
(a commented-out import is no edge; `import(/* chunk */ "./x")` is one). A relative specifier resolves against the
file; a bare one through the tsconfig/jsconfig `paths` and `baseUrl` (following `extends` and `references`), then
through the packages of a monorepo's workspaces (every package.json with a `name`: its `exports`, `module`, `main` or
`types`, falling back to `src/index` when those point at a build output that is not there). `./x.js` also finds
`x.ts` (TypeScript's NodeNext style). Anything else (an npm dependency, an asset) is no edge."""
import json, os, re
from pathlib import Path

from bracecomments import strip_comments
from codefiles import ROOT, SKIP
from guard import checked

JS_IMPORT = re.compile(r"""(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\(\s*['"]([^'"]+)['"]\s*\)|^[ \t]*import\s*['"]([^'"]+)['"]""", re.M)   # the last: `import 'app/config/dayjs';`, a side-effect import
JS_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs")
TS_FOR_JS = {".js": (".ts", ".tsx"), ".jsx": (".tsx",), ".mjs": (".mts", ".ts")}
_TS_CONFIGS = {}    # folder -> {"baseUrl": Path, "paths": {pattern: [targets]}} or {}, once per run
_WORKSPACES = {}    # ROOT -> {package name: (folder, package.json data)}, once per run


@checked
def _tsconfig(data: dict) -> dict:
    return data


def _jsonc(text: str):
    """tsconfig.json is JSON with comments and trailing commas."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
    return _tsconfig(json.loads(re.sub(r",\s*([}\]])", r"\1", text)))


# ---- tsconfig paths -----------------------------------------------------------------------------------------------

def _own_options(data: dict, cfg: Path) -> dict:
    """baseUrl (resolved) and paths declared in this file; paths without a baseUrl are relative to the file."""
    opts = data.get("compilerOptions") or {}
    out = {}
    if opts.get("baseUrl"):
        out["baseUrl"] = (cfg.parent / opts["baseUrl"]).resolve()
    if opts.get("paths"):
        out["paths"] = opts["paths"]
        out.setdefault("baseUrl", cfg.parent.resolve())
    return out


def _linked_configs(data: dict, cfg: Path) -> list:
    """The files `extends` and (solution-style tsconfigs) `references` point to."""
    links = ([data["extends"]] if isinstance(data.get("extends"), str) else []) + [r.get("path", "") for r in data.get("references", [])]
    return [(cfg.parent / (link if link.endswith(".json") else link + "/tsconfig.json")).resolve() for link in links if link]


def _ts_options(cfg: Path, seen: set = None) -> dict:
    """baseUrl and paths of a tsconfig, following `extends` and `references`; the nearest declaration wins."""
    seen = seen or set()
    if cfg in seen or not cfg.is_file():
        return {}
    seen.add(cfg)
    try:
        data = _jsonc(cfg.read_text(encoding="utf-8", errors="replace"))
    except ValueError:
        return {}
    out = _own_options(data, cfg)
    for linked in _linked_configs(data, cfg):
        for k, v in _ts_options(linked, seen).items():
            out.setdefault(k, v)
    return out


def _ts_config_for(f: Path) -> dict:
    """The options of the nearest tsconfig.json / jsconfig.json at or above the file, inside the project."""
    for folder in [f.parent, *f.parent.parents]:
        if folder in _TS_CONFIGS:
            return _TS_CONFIGS[folder]
        cfg = next((folder / n for n in ("tsconfig.json", "jsconfig.json") if (folder / n).is_file()), None)
        if cfg or folder == ROOT.resolve() or not folder.is_relative_to(ROOT.resolve()):
            _TS_CONFIGS[folder] = _ts_options(cfg) if cfg else {}
            return _TS_CONFIGS[folder]
    return {}


def _alias_bases(spec: str, f: Path) -> list:
    """Where a bare specifier may live: tsconfig `paths` patterns (`@/*` -> `src/*`), then `baseUrl` itself."""
    cfg = _ts_config_for(f)
    if not cfg:
        return []
    bases = []
    for pattern, targets in (cfg.get("paths") or {}).items():
        prefix = pattern.split("*")[0]
        if spec.startswith(prefix) and (("*" in pattern) or spec == pattern):
            rest = spec[len(prefix):]
            bases += [cfg["baseUrl"] / t.replace("*", rest) for t in targets]
    return bases + [cfg["baseUrl"] / spec]


# ---- workspace packages -------------------------------------------------------------------------------------------

def _package_files():
    """Every package.json of the project outside node_modules, build output and hidden folders (never walked into)."""
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        if "package.json" in files:
            yield Path(folder) / "package.json"


def workspaces() -> dict:
    """package name -> (folder, package.json data) for the packages of this project; computed once per run."""
    if ROOT not in _WORKSPACES:
        found = {}
        for p in _package_files():
            try:
                data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except ValueError:
                continue
            if isinstance(data, dict) and isinstance(data.get("name"), str):
                found.setdefault(data["name"], (p.parent.resolve(), data))
        _WORKSPACES[ROOT] = found
    return _WORKSPACES[ROOT]


def _export_target(value):
    """The file an `exports` entry names: a string, or the first of import/module/default/require/types."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("import", "module", "default", "require", "types"):
            if key in value:
                return _export_target(value[key])
    return None


def _entry_bases(folder: Path, data: dict, sub: str) -> list:
    """Candidate files for `name` (sub == '') or `name/sub` inside a workspace package."""
    if sub:
        exported = data.get("exports", {}).get("./" + sub) if isinstance(data.get("exports"), dict) else None
        target = _export_target(exported)
        return ([folder / target] if target else []) + [folder / sub, folder / "src" / sub]
    exports = data.get("exports")
    root = _export_target(exports.get(".") if isinstance(exports, dict) and "." in exports else exports)
    named = [root] + [data.get(k) for k in ("module", "main", "types", "typings", "source")]
    return [folder / t for t in named if isinstance(t, str)] + [folder / "src" / "index", folder / "index"]


def _workspace_bases(spec: str) -> list:
    """`@acme/billing` or `@acme/billing/sub/path` -> candidate files in that package of the monorepo."""
    for name, (folder, data) in workspaces().items():
        if spec == name or spec.startswith(name + "/"):
            return _entry_bases(folder, data, spec[len(name) + 1:])
    return []


# ---- one file -----------------------------------------------------------------------------------------------------

def resolve_js(base: Path):
    """The file a specifier base names: itself, with a suffix, its index, or the .ts behind a .js."""
    cands = [base] + [base.with_name(base.name + e) for e in JS_SUFFIXES] + [base / f"index{e}" for e in JS_SUFFIXES]   # `./activate.service` + `.ts`: with_suffix would replace `.service`
    cands += [base.with_suffix(t) for t in TS_FOR_JS.get(base.suffix, ())]
    return next((c for c in cands if c.is_file()), None)


def specifier_bases(spec: str, f: Path) -> list:
    """Where a specifier may live: next to the file when relative, else tsconfig aliases and workspace packages."""
    if spec.startswith("."):
        return [f.parent / spec]
    return _alias_bases(spec, f) + _workspace_bases(spec)


def js_module_edges(f: Path) -> list:
    out = []
    for m in JS_IMPORT.finditer(strip_comments(f.read_text(encoding="utf-8", errors="replace"), "js")):
        spec = next(g for g in m.groups() if g)
        hit = next((h for h in map(resolve_js, specifier_bases(spec, f)) if h), None)
        if hit:
            out.append(hit)
    return out
