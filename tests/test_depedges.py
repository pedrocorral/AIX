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
