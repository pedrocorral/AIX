"""23. Dead code and clones on the shapes real projects have: nested code roots are measured once (no self-clones),
files a framework loads by convention are live (Django, Cargo, Maven, tool scripts, dot-files), Java classes the
container instantiates are live, a re-exported function is used, a public unreferenced function is tagged; and a
plain unreferenced file is still reported (the positive control)."""
import re, unittest
from helpers import config, install, project_cmd, temp_home


def write(root, files: dict):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def dead_modules(out: str) -> set:
    tail = out.split("DEAD MODULES")[1].split("DEAD FUNCTIONS")[0].split("  Every line")[0]
    return set(re.findall(r"^    (\S+)$", tail, re.M))


class NestedRoots(unittest.TestCase):
    def test_dot_root_with_children_is_measured_once(self):
        home = temp_home(self)
        project = home / "app"
        write(project, {"setup.py": "from setuptools import setup\nsetup()\n",
                        "src/pkg/__init__.py": "from .core import work\n",
                        "src/pkg/core.py": "def work(a, b):\n    x = a + b\n    y = x * 2\n    z = y - 1\n    w = z + a\n    v = w + b\n    return v\n",
                        "tests/test_core.py": "from pkg.core import work\ndef test_work():\n    assert work(1, 2)\n"})
        install(home, project)
        project_cmd(project, home, "code", "find", "--yes")
        self.assertRegex(config(project), r"code_roots: \[\., src, tests\]", "find still records what it saw")
        style = project_cmd(project, home, "code", "style").stdout
        self.assertIn("Code style — .", style.splitlines()[0])
        self.assertIn("functions analysed 2;", style, "work and test_work, each once")
        clones = project_cmd(project, home, "code", "clones").stdout
        self.assertIn("exact clone groups 0", clones, "a function is not a clone of itself\n" + clones)


class LiveByConvention(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"

    def dead(self, files: dict) -> set:
        write(self.project, files)
        install(self.home, self.project)
        project_cmd(self.project, self.home, "code", "find", "--yes")
        return dead_modules(project_cmd(self.project, self.home, "code", "dead").stdout)

    def test_django_conventions(self):
        dead = self.dead({"manage.py": "import os\n", "shop/apps.py": "class ShopConfig:\n    pass\n", "shop/admin.py": "x = 1\n",
                          "shop/migrations/0001_initial.py": "x = 1\n", "shop/management/commands/seed.py": "x = 1\n",
                          "shop/models.py": "x = 1\n", "shop/views.py": "from shop.models import x\n", "shop/urls.py": "from shop.views import x\n",
                          "shop/forgotten.py": "y = 2\n"})
        self.assertEqual(dead, {"shop/forgotten.py"}, "migrations, admin, apps, commands and urls are loaded by Django; views and models hang from urls")

    def test_cargo_conventions(self):
        dead = self.dead({"Cargo.toml": "[package]\nname = \"x\"\n", "build.rs": "fn main() {}\n",
                          "crates/util/Cargo.toml": "[package]\nname = \"util\"\n", "crates/util/src/lib.rs": "pub mod text;\n",
                          "crates/util/src/text.rs": "pub fn upper() {}\n", "crates/util/benches/speed.rs": "fn main() {}\n",
                          "crates/util/examples/demo.rs": "fn main() {}\n", "crates/util/src/bin/tool.rs": "fn main() {}\n",
                          "crates/util/src/orphan.rs": "pub fn nothing() {}\n"})
        self.assertEqual(dead, {"crates/util/src/orphan.rs"}, "lib.rs and its mod tree, build.rs, benches, examples and bin are live")

    def test_java_container_and_maven_it(self):
        dead = self.dead({"pom.xml": "<project/>\n",
                          "src/main/java/com/a/PetController.java": "package com.a;\n@RestController\npublic class PetController { private final PetService s = null; }\n",
                          "src/main/java/com/a/PetService.java": "package com.a;\n@Service\npublic class PetService { }\n",
                          "src/main/java/com/a/Pet.java": "package com.a;\n@Entity\npublic class Pet { }\n",
                          "src/main/java/com/a/Helper.java": "package com.a;\npublic class Helper { }\n",
                          "src/it/java/com/a/PetIT.java": "package com.a;\npublic class PetIT { }\n"})
        self.assertEqual(dead, {"src/main/java/com/a/Helper.java"}, "a controller, a service, an entity and an integration test are live; a plain unused class is not")

    def test_tooling_files_and_dot_files(self):
        dead = self.dead({"package.json": "{}\n", "Gruntfile.js": "module.exports = 1;\n", ".eslintrc.js": "module.exports = {};\n",
                          "scripts/release.js": "console.log(1);\n", "public/service-worker.js": "self.x = 1;\n",
                          "src/index.js": "import './app.js';\n", "src/app.js": "export const a = 1;\n", "src/unused.js": "export const b = 2;\n"})
        self.assertEqual(dead, {"src/unused.js"})


class AliasesAndDataFolders(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"

    def dead(self, files: dict) -> str:
        write(self.project, files)
        install(self.home, self.project)
        project_cmd(self.project, self.home, "code", "find", "--yes")
        return project_cmd(self.project, self.home, "code", "dead").stdout

    def test_tsconfig_paths_and_base_url(self):
        out = self.dead({"package.json": "{}\n",
                         "tsconfig.json": '{\n  // comments and trailing commas are allowed here\n  "compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["src/*"], "@ui": ["src/ui/index.ts"],},},\n}\n',
                         "src/index.ts": "import { a } from '@/lib/a';\nimport { b } from 'src/lib/b';\nimport { ui } from '@ui';\n",
                         "src/lib/a.ts": "export const a = 1;\n", "src/lib/b.ts": "export const b = 2;\n", "src/ui/index.ts": "export const ui = 3;\n",
                         "src/lib/unused.ts": "export const u = 4;\n"})
        self.assertEqual(dead_modules(out), {"src/lib/unused.ts"}, "@/ (paths), a bare baseUrl path and an exact alias resolve\n" + out)

    def test_solution_style_tsconfig_with_references_and_extends(self):
        out = self.dead({"package.json": "{}\n", "tsconfig.base.json": '{"compilerOptions": {"baseUrl": "./", "paths": {"~/*": ["app/*"]}}}\n',
                         "frontend/tsconfig.json": '{"files": [], "references": [{"path": "./tsconfig.app.json"}]}\n',
                         "frontend/tsconfig.app.json": '{"extends": "../tsconfig.base.json", "compilerOptions": {"outDir": "dist"}}\n',
                         "frontend/main.ts": "import { x } from '~/x';\n", "app/x.ts": "export const x = 1;\n", "app/y.ts": "export const y = 2;\n"})
        self.assertEqual(dead_modules(out), {"app/y.ts"}, out)

    def test_folder_named_in_code_is_loaded_as_data(self):
        out = self.dead({"package.json": "{}\n", "server.js": "const fs = require('fs');\nconst FIXES = 'data/static/fixes';\nfs.readdirSync(FIXES);\n",
                         "data/static/fixes/one.ts": "export const one = 1;\n", "data/static/fixes/two.ts": "export const two = 2;\n",
                         "data/other/three.ts": "export const three = 3;\n"})
        self.assertIn("loaded as data (a folder named by a string in code, its files read, not imported): data/static/fixes", out)
        self.assertEqual(dead_modules(out), {"data/other/three.ts"}, out)

    def test_python_folder_named_relative_to_the_file(self):
        out = self.dead({"app/main.py": "from pathlib import Path\nTEMPLATES = Path(__file__).parent / 'templates/'\nfor f in Path('templates/').iterdir():\n    pass\n",
                         "app/templates/a.py": "x = 1\n", "app/stale.py": "y = 2\n"})
        self.assertEqual(dead_modules(out), {"app/stale.py"}, out)


class DeadFunctions(unittest.TestCase):
    def test_reexport_counts_and_public_is_tagged(self):
        home = temp_home(self)
        project = home / "app"
        write(project, {"pyproject.toml": "[project]\nname = 'lib'\n", "src/lib/__init__.py": "from .api import get, delete\n",
                        "src/lib/api.py": "def get():\n    return 1\n\n\ndef delete():\n    return 2\n\n\ndef list_domains():\n    return 3\n\n\ndef _stale():\n    return 4\n"})
        install(home, project)
        project_cmd(project, home, "code", "find", "--yes")
        out = project_cmd(project, home, "code", "dead", "--functions").stdout
        self.assertNotIn("api.py:get", out); self.assertNotIn("api.py:delete", out)
        self.assertRegex(out, r"api\.py:list_domains  \(line \d+\)  \(public: the API of a library, or dead in an application\)")
        self.assertRegex(out, r"api\.py:_stale  \(line \d+\)\n")
        self.assertIn("DEAD FUNCTIONS 2", out)


if __name__ == "__main__":
    unittest.main()
