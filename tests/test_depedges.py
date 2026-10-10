"""The module graph's edges per language (depedges, jsedges, rustedges), the cases benchmark section 30 found against
grimp, dependency-cruiser, cargo-modules and jdeps: each planted in a small project, each with the twin that must
stay no edge. JavaScript: a commented-out import is none, `import(/* chunk */ "./x")` is one, a monorepo workspace
package resolves through its package.json, `./x.js` finds `x.ts`. Rust: a grouped `use` tree, a path written in the
code, `super` inside an inline module, a `#[cfg(test)]` module left out, another crate of the workspace, a name re-exported with `pub use`, a glob
import by the names the file writes, `mod x;` only with ownership. Java: a class named by its full name, an import
that shadows the package's class of that name, a Javadoc-only import. Python: a literal `importlib.import_module`."""
import json, subprocess, sys, textwrap, unittest
from pathlib import Path

from helpers import env, install, temp_home

EDGES = ("import sys, json; sys.path.insert(0, '.aix/scripts'); from depedges import module_graph; "
         "n, e = module_graph({roots!r}, ownership={own}); print(json.dumps(sorted(e)))")


def plant(root: Path, files: dict):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


class _Graph(unittest.TestCase):
    FILES, ROOTS = {}, ["src"]

    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        plant(self.project, self.FILES)
        install(self.home, self.project)

    def edges(self, ownership=True) -> set:
        out = subprocess.run([sys.executable, "-c", EDGES.format(roots=self.ROOTS, own=ownership)], cwd=self.project,
                             env=env(self.home), capture_output=True, text=True, check=True).stdout
        return {tuple(e) for e in json.loads(out)}


class JavaScript(_Graph):
    ROOTS = ["src", "packages"]
    FILES = {
        "src/a.ts": """
            // import { x } from './commented';
            /* import y from './blocked'; */
            const img = await import(/* webpackChunkName: "img" */ "./image");
            import { z } from "./esm.js";
            import { pay } from "@acme/billing";
            import { fmt } from "@acme/billing/format";
            """,
        "src/commented.ts": "export const x = 1;\n",
        "src/blocked.ts": "export default 2;\n",
        "src/image.ts": "export const i = 1;\n",
        "src/esm.ts": "export const z = 1;\n",
        "packages/billing/package.json": '{"name": "@acme/billing", "main": "dist/index.js", "exports": {".": {"import": "./dist/index.js"}, "./format": "./src/format.ts"}}\n',
        "packages/billing/src/index.ts": "export const pay = 1;\n",
        "packages/billing/src/format.ts": "export const fmt = 1;\n",
    }

    def test_comments_dynamic_imports_esm_and_workspaces(self):
        e = self.edges()
        self.assertNotIn(("src/a.ts", "src/commented.ts"), e, "a commented-out import is no edge")
        self.assertNotIn(("src/a.ts", "src/blocked.ts"), e, "nor one inside a block comment")
        self.assertIn(("src/a.ts", "src/image.ts"), e, "import(/* chunk */ './x') is an edge")
        self.assertIn(("src/a.ts", "src/esm.ts"), e, "./esm.js finds esm.ts")
        self.assertIn(("src/a.ts", "packages/billing/src/index.ts"), e, "a workspace package: main points at a missing build, src/index is the entry")
        self.assertIn(("src/a.ts", "packages/billing/src/format.ts"), e, "a subpath through the package's exports")


class Rust(_Graph):
    ROOTS = ["crates"]
    FILES = {
        "Cargo.toml": '[workspace]\nmembers = ["crates/*"]\n',
        "crates/core/Cargo.toml": '[package]\nauthors = ["x"]\nname = "acme-core"\n',
        "crates/core/src/lib.rs": "pub mod money;\npub use money::Money;\n",
        "crates/core/src/money.rs": "pub struct Money;\n",
        "crates/app/Cargo.toml": '[package]\nname = "app"\n',
        "crates/app/src/lib.rs": "mod orders;\nmod billing;\nmod pricing;\nmod util;\nmod wild;\n",
        "crates/app/src/orders.rs": """
            use crate::{billing, pricing::{self, quote}};
            use acme_core::Money;
            pub fn place() -> Money { crate::util::now(); billing::charge(); Money }
            // use crate::wild;
            pub mod inner {
                use super::place;
                pub fn again() { place(); }
            }
            #[cfg(test)]
            mod tests {
                use crate::wild::w;
                #[test] fn t() { w(); }
            }
            """,
        "crates/app/src/billing.rs": "pub fn charge() {}\n",
        "crates/app/src/pricing.rs": "pub fn quote() {}\n",
        "crates/app/src/util.rs": "pub fn now() {}\n",
        "crates/app/src/wild.rs": "use crate::billing::*;\npub fn w() { charge(); }\n",
        "crates/app/tests/fixture/Cargo.toml": '[package]\nname = "app"\n',
    }

    def test_use_trees_paths_inline_modules_workspace_reexports_and_globs(self):
        e, app = self.edges(), "crates/app/src/"
        self.assertIn((app + "orders.rs", app + "billing.rs"), e, "a grouped use tree")
        self.assertIn((app + "orders.rs", app + "pricing.rs"), e, "`pricing::{self, quote}`")
        self.assertIn((app + "orders.rs", app + "util.rs"), e, "a path written in the code")
        self.assertIn((app + "orders.rs", "crates/core/src/money.rs"), e, "another crate of the workspace, through its `pub use`")
        self.assertNotIn((app + "orders.rs", app + "lib.rs"), e, "`super` inside an inline `mod inner` is the file's own module, not lib.rs")
        self.assertNotIn((app + "orders.rs", app + "wild.rs"), e, "a commented-out use, and a use inside `#[cfg(test)] mod tests`, are no edges")
        self.assertIn((app + "wild.rs", app + "billing.rs"), e, "a glob import of a module the file uses")

    def test_module_declarations_only_with_ownership(self):
        app = "crates/app/src/"
        self.assertIn((app + "lib.rs", app + "orders.rs"), self.edges(ownership=True))
        self.assertNotIn((app + "lib.rs", app + "orders.rs"), self.edges(ownership=False), "declaring a module is not using it")


class RustCrateRootElsewhere(_Graph):
    """ripgrep's shape: the binary's root file is not under src/ (`[[bin]] path = "cmd/main.rs"`)."""
    ROOTS = ["tool"]
    FILES = {
        "tool/Cargo.toml": '[package]\nname = "tool"\n\n[[bin]]\nname = "t"\npath = "cmd/main.rs"\n',
        "tool/cmd/main.rs": "mod flags;\nfn main() { crate::flags::defs::run(); }\n",
        "tool/cmd/flags/mod.rs": "pub mod defs;\n",
        "tool/cmd/flags/defs.rs": "pub fn run() {}\n",
    }

    def test_modules_resolve_from_the_root_file_cargo_names(self):
        e = self.edges()
        self.assertIn(("tool/cmd/main.rs", "tool/cmd/flags/mod.rs"), e, "`mod flags;` next to the root file")
        self.assertIn(("tool/cmd/flags/mod.rs", "tool/cmd/flags/defs.rs"), e, "`pub mod defs;` inside it")
        self.assertIn(("tool/cmd/main.rs", "tool/cmd/flags/defs.rs"), e, "`crate::` from the root file's folder")


class RustOwnCrateByName(_Graph):
    """A binary, a bin target and an integration test are crates of their own: they name the library by its name."""
    ROOTS = ["app"]
    FILES = {
        "app/Cargo.toml": '[package]\nname = "my-app"\n',
        "app/src/lib.rs": "pub mod billing;\n",
        "app/src/billing.rs": "pub fn charge() {}\n",
        "app/src/main.rs": "use my_app::billing::charge;\nfn main() { charge(); }\n",
        "app/src/bin/tool.rs": "use my_app::billing::charge;\nfn main() { charge(); }\n",
        "app/tests/it.rs": "use my_app::billing::charge;\n#[test] fn t() { charge(); }\n",
    }

    def test_binaries_and_integration_tests_reach_the_library(self):
        e = self.edges(ownership=False)
        for user in ("app/src/main.rs", "app/src/bin/tool.rs", "app/tests/it.rs"):
            self.assertIn((user, "app/src/billing.rs"), e, user)


class RustExternCrate(_Graph):
    """`pub extern crate other as o;` re-exports a whole workspace crate: an edge to its root; an outside crate is none."""
    ROOTS = ["facade", "core"]
    FILES = {
        "facade/Cargo.toml": '[package]\nname = "facade"\n',
        "facade/src/lib.rs": "pub extern crate core_lib as core;\nextern crate serde;\n",
        "core/Cargo.toml": '[package]\nname = "core-lib"\n',
        "core/src/lib.rs": "pub fn run() {}\n",
    }

    def test_a_reexported_crate_is_an_edge(self):
        self.assertEqual({b for a, b in self.edges(ownership=False) if a == "facade/src/lib.rs"}, {"core/src/lib.rs"})


class JavaScriptConfigsAndStrings(_Graph):
    ROOTS = ["src", "config"]
    FILES = {
        "tsconfig.base.json": '{"compilerOptions": {"baseUrl": "./src"}}\n',
        "tsconfig.json": '{"extends": "./tsconfig.base.json", "compilerOptions": {"paths": {"@lib/*": ["lib/*"]}}}\n',
        "src/lib/util.ts": "export const u = 1;\n",
        "src/lib/other.ts": "export const o = 1;\n",
        "config/index.ts": "export default 1;\n",
        "src/a.ts": """
            import { u } from "@lib/util";
            const msg = "please import the file from './lib/other'";
            const t = `require("./lib/other")`;
            """,
    }

    def test_inherited_base_url_and_imports_written_inside_strings(self):
        e = self.edges()
        self.assertIn(("src/a.ts", "src/lib/util.ts"), e, "paths resolve against the baseUrl inherited through extends")
        self.assertNotIn(("src/a.ts", "src/lib/other.ts"), e, "an import written inside a string is text")


class JavaScriptNoBaseUrl(_Graph):
    ROOTS = ["src", "config"]
    FILES = {
        "tsconfig.json": '{"compilerOptions": {"paths": {"@x/*": ["src/*"]}}}\n',
        "src/a.ts": 'import config from "config";\nexport const a = config;\n',
        "config/index.ts": "export default 1;\n",
    }

    def test_a_bare_import_is_a_package_without_base_url(self):
        self.assertEqual(self.edges(), set(), "without baseUrl, `config` is the npm package, not the local folder")


class Java(_Graph):
    ROOTS = ["src/main/java"]
    FILES = {
        "src/main/java/com/acme/app/Orders.java": """
            package com.acme.app;
            import com.acme.stream.Streams;
            import com.acme.billing.Ledger;
            /** See {@link Ledger}. */
            public class Orders {
                Object a = Streams.of();
                Object b = new com.acme.billing.Invoice();
            }
            """,
        "src/main/java/com/acme/app/Streams.java": "package com.acme.app;\npublic class Streams {}\n",
        "src/main/java/com/acme/stream/Streams.java": "package com.acme.stream;\npublic class Streams { public static Object of() { return null; } }\n",
        "src/main/java/com/acme/billing/Ledger.java": "package com.acme.billing;\npublic class Ledger {}\n",
        "src/main/java/com/acme/billing/Invoice.java": "package com.acme.billing;\npublic class Invoice {}\n",
    }

    def test_qualified_names_shadowing_and_javadoc_imports(self):
        e, j = self.edges(), "src/main/java/com/acme/"
        self.assertIn((j + "app/Orders.java", j + "stream/Streams.java"), e, "the imported Streams")
        self.assertNotIn((j + "app/Orders.java", j + "app/Streams.java"), e, "an import shadows the package's class of that name")
        self.assertIn((j + "app/Orders.java", j + "billing/Invoice.java"), e, "a class named by its full name")
        self.assertNotIn((j + "app/Orders.java", j + "billing/Ledger.java"), e, "an import only Javadoc names is no dependency")


class Python(_Graph):
    FILES = {
        "src/app/__init__.py": "",
        "src/app/main.py": "import importlib\nplugins = importlib.import_module('app.plugins')\nother = importlib.import_module(name)\n",
        "src/app/plugins.py": "X = 1\n",
    }

    def test_literal_dynamic_import(self):
        self.assertIn(("src/app/main.py", "src/app/plugins.py"), self.edges())


class NestedYaml(unittest.TestCase):
    def test_parse_tree_reads_the_declaration_shapes_and_names_the_line_of_an_error(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".aix" / "scripts"))
        from yamlmini import parse_tree
        tree = parse_tree("a:\n  b: {paths: [x/**, 'y z'], n: 1}\n  c:\n    - p\n    - q  # comment\nt: \"v # not a comment\"\n")
        self.assertEqual(tree, {"a": {"b": {"paths": ["x/**", "y z"], "n": "1"}, "c": ["p", "q"]}, "t": "v # not a comment"})
        for bad, line in (("a:\n  b: 1\n    c: 2\n", "line 3"), ("a: [1, 2\n", "line 1"), ("a:\n\tb: 1\n", "line 2")):
            with self.assertRaises(ValueError) as cm:
                parse_tree(bad)
            self.assertIn(line, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
