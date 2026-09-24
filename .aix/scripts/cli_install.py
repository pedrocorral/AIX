"""`aix install`: link the skills into the agent runtimes here, or (`--into DIR`) copy the kit into a project first:
payload, layers, seeded docs, agents, links, .gitignore, code folders. `aix install aix` is `aix self-install`."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


INSTALL_OPTIONS = {"--copy", "--into", "--from", "--from-org", "--from-custom", "--agents", "--replace-all", "--skip-all", "--merge-all"}


def _option_value(args, flag, into):
    """The value after `flag`, or None when absent; a missing value or a value that looks like a flag is refused."""
    if flag not in args:
        return None
    i = args.index(flag)
    if i + 1 >= len(args) or args[i + 1].startswith("-") or not into:
        sys.exit(f"aix install {flag} SOURCE needs a source and --into DIR")
    return args[i + 1]


class InstallArgs:
    """What `aix install` was asked: copy mode, target folder, collision answer, sources, agents."""
    def __init__(self, args):
        bad = [a for a in args if a.startswith("--") and a not in INSTALL_OPTIONS]
        if bad:
            sys.exit(f"aix install: unknown option {' '.join(bad)}. Options: --copy, --into DIR, --from SRC, --from-org SRC, --from-custom SRC, --agents a,b, --replace-all, --skip-all, --merge-all (aix help install)")
        self.copy = "--copy" in args
        self.into = _into_dir(args)
        self.mode = next((m for flag, m in (("--replace-all", "replace"), ("--skip-all", "skip"), ("--merge-all", "merge")) if flag in args), "ask")
        self.src = _option_value(args, "--from", self.into)
        self.layer_src = {"org": _option_value(args, "--from-org", self.into), "custom": _option_value(args, "--from-custom", self.into)}
        self.wanted_agents = _option_value(args, "--agents", self.into)


def _into_dir(args):
    if "--into" not in args:
        return None
    i = args.index("--into")
    if i + 1 >= len(args) or args[i + 1].startswith("-"):
        sys.exit("aix install --into needs a directory")
    return Path(args[i + 1]).resolve()


def _parse_install(args) -> "InstallArgs":
    return InstallArgs(args)


def _origin_of(src, layer_src):
    """The origin checkout: this one, or the kit named by --from; a bare --from folder becomes the org source."""
    import source as srcmod
    if not src:
        return ROOT
    kind, payload_root, _bare = srcmod.classify(srcmod.fetch(src))
    if kind == "kit":
        print(f"  origin: kit checkout at {payload_root}")
        return payload_root
    layer_src["org"] = layer_src["org"] or src
    print(f"  origin: this checkout; org layer from {src}")
    return ROOT


def _install_new_project(a: "InstallArgs"):
    """The whole `aix install --into DIR`: payload, layers, docs seed, agents, links, .gitignore, code folders."""
    import install_skills as inst, source as srcmod, agents, gitignore, codefind
    origin = _origin_of(a.src, a.layer_src)
    inst.copy_kit_into(a.into, a.mode, kit=origin)
    if a.src:
        srcmod.record(a.into, a.src)
    srcmod.install_layers(a.into, srcmod.resolve_layers(origin, srcmod.layer_sources(a.into, a.layer_src)))
    inst.seed_project(a.into, kit=origin)  # docs/ from .aix/templates/docs overlaid by the layers' templates/docs
    agents.run(a.into, a.wanted_agents.split(",") if a.wanted_agents else None, title="aix install")  # names, checklist, or all
    agents.remove_deselected(a.into, agents.selected(a.into))
    inst.install_into(a.into, a.copy)
    gitignore.ask_and_apply(a.into, label="aix install")
    codefind.run(a.into, title="aix install")  # checklist in a terminal; the table and a hint otherwise


def cmd_install(args):
    if args[:1] == ["aix"]:  # aix install aix = aix self-install
        import selfinstall
        return selfinstall.main(args[1:])
    import install_skills as inst, gitignore
    a = _parse_install(args)
    if a.into:
        return _install_new_project(a)
    inst.install_into(inst.KIT_ROOT, a.copy)  # PATH link is handled in reexec_in_project, by the kit only
    gitignore.ask_and_apply(inst.KIT_ROOT, label="aix install")
