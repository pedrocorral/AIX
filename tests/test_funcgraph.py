"""27. Function graphs for JavaScript/TypeScript, Rust and Java, by tokens: a chain, a cycle, `this.m()` /
`self.m()`, `Class.m()` / `Type::m()`, a name imported by name, a module import, and a call on an unknown receiver
that must stay out. Exact nodes, arcs and the resolved-calls ratio; Python's graph unchanged."""
import re, unittest
from helpers import install, project_cmd, temp_home


def write(root, files: dict):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


class FunctionGraphs(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"

    def graph(self, files: dict) -> str:
        write(self.project, files)
        install(self.home, self.project)
        project_cmd(self.project, self.home, "code", "find", "--yes")
        return project_cmd(self.project, self.home, "code", "graph", "--functions", "src", "--roles").stdout

    def roles(self, out: str) -> dict:
        """node -> (fan-in, fan-out) from the --roles table."""
        return {m.group(3): (int(m.group(1)), int(m.group(2))) for m in re.finditer(r"in\s+(\d+) out\s+(\d+)  (\S+)$", out, re.M)}

    def test_javascript(self):
        out = self.graph({
            "src/main.ts": "import { helper, other as renamed } from './util';\nimport * as api from './api';\nimport fs from 'fs';\n"
                           "export function a() { b(); helper(); renamed(); api.fetchAll(); item.save(); fs.readFileSync('x'); }\n"
                           "function b() { c(); }\nfunction c() { a(); }\n"
                           "class Thing {\n  run() { this.step(); Thing.make(); }\n  step() { return 1; }\n  static make() { return new Thing(); }\n}\n"
                           "const arrow = () => { b(); };\n",
            "src/util.ts": "export function helper() {}\nexport function other() {}\n",
            "src/api.ts": "export function fetchAll() { return []; }\n"})
        self.assertIn("nodes 10, edges 9", out, out)
        self.assertIn("resolved calls 9 of 9 (100 %)", out, "item.save(), fs.readFileSync() and new Thing() are not project calls: not counted")
        r = self.roles(out)
        self.assertEqual(r["src/main.ts:a"], (1, 4)); self.assertEqual(r["src/main.ts:Thing.run"], (0, 2)); self.assertEqual(r["src/main.ts:b"], (2, 1))
        self.assertRegex(out, r"CUT    src/main\.ts:(a|b|c) -> src/main\.ts:(a|b|c)  \(closes a cycle among 3 nodes")

    def test_rust(self):
        out = self.graph({
            "Cargo.toml": "[package]\nname = \"x\"\n",
            "src/lib.rs": "mod util;\nuse crate::util::{helper, other as renamed};\npub fn a() { b(); helper(); renamed(); util::third(); Thing::new(); item.save(); }\n"
                          "fn b() { c(); }\nfn c() { a(); }\n"
                          "pub struct Thing;\nimpl Thing {\n    pub fn new() -> Thing { Self::build() }\n    fn build() -> Thing { Thing }\n    pub fn run(&self) { self.step(); }\n    fn step(&self) {}\n}\n",
            "src/util.rs": "pub fn helper() {}\npub fn other() {}\npub fn third() {}\n"})
        self.assertIn("nodes 10, edges 9", out, out)
        self.assertIn("resolved calls 9 of 9 (100 %)", out, out)
        r = self.roles(out)
        self.assertEqual(r["src/lib.rs:a"], (1, 5)); self.assertEqual(r["src/lib.rs:Thing.run"], (0, 1)); self.assertEqual(r["src/lib.rs:Thing.new"], (1, 1))

    def test_java(self):
        out = self.graph({
            "pom.xml": "<project/>\n",
            "src/main/java/com/a/Main.java": "package com.a;\nimport com.b.Remote;\npublic class Main {\n    public void run() { step(); this.again(); Util.help(); Remote.call(); item.save(); }\n"
                                             "    void step() {}\n    void again() {}\n}\n",
            "src/main/java/com/a/Util.java": "package com.a;\npublic class Util {\n    public static void help() { new Main().run(); }\n}\n",
            "src/main/java/com/b/Remote.java": "package com.b;\npublic class Remote {\n    public static void call() {}\n}\n"})
        self.assertIn("nodes 5, edges 5", out, out)
        self.assertIn("resolved calls 5 of 5 (100 %)", out, out)
        r = self.roles(out)
        self.assertEqual(r["src/main/java/com/a/Main.java:Main.run"], (1, 4))
        self.assertRegex(out, r"CUT    .*Main\.run -> .*Util\.help|CUT    .*Util\.help -> .*Main\.run")

    def test_python_facade_and_constructor(self):
        out = self.graph({"src/pkg/__init__.py": "from .core import helper as helper\nfrom .core import Thing\n",
                          "src/pkg/core.py": "class Thing:\n    def __init__(self):\n        self.x = 1\n\n\nclass Plain:\n    pass\n\n\ndef helper():\n    pass\n",
                          "src/app.py": "import pkg\nfrom pkg.core import Plain\n\n\ndef f(cb):\n    pkg.helper()\n    pkg.Thing()\n    Plain()\n    cb()\n"})
        self.assertIn("nodes 3, edges 2", out, "f -> helper through the package facade, f -> Thing.__init__; Plain() and cb() are neither arcs nor misses\n" + out)
        self.assertIn("resolved calls 2 of 2 (100 %)", out)

    def test_javascript_default_export(self):
        out = self.graph({"src/index.js": "module.exports = require('./lib/app');\n",
                          "src/lib/app.js": "module.exports = createApp;\nfunction createApp() { return 1; }\n",
                          "src/main.js": "const app = require('./index');\nconst { t } = useI18n();\nfunction boot() { app(); t('x'); expect(1); return 2; }\n"})
        self.assertIn("nodes 2, edges 1", out, "boot -> createApp through two facades; t is a destructured value, expect a test global\n" + out)
        self.assertIn("resolved calls 1 of 1 (100 %)", out)

    def test_python_unchanged(self):
        out = self.graph({"src/a.py": "from b import helper\n\ndef f():\n    helper()\n    g()\n\n\ndef g():\n    pass\n", "src/b.py": "def helper():\n    pass\n"})
        self.assertIn("nodes 3, edges 2", out)
        self.assertIn("resolved calls 2 of 2 (100 %)", out)


if __name__ == "__main__":
    unittest.main()
