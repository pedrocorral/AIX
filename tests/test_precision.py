"""Precision fixes the engine benchmark exposed (docs/tests/benchmark-engines.md): a Java `byte hash[]` parameter
is read, functions in a file named app.py are not tests, vendored libraries are not the project's code for any
tool, and `?.`, `x?: T`, `??` and template-literal text are not branches for the cyclomatic count."""
import sys, unittest
from pathlib import Path

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import codefiles, passthrough  # noqa: E402

JAVA = "class MD5 {\n  private static String toHex(byte hash[]) {\n    StringBuilder buf = new StringBuilder(hash.length * 2);\n    return buf.toString();\n  }\n  static int sum(int... values) { return values.length; }\n}\n"
TSX = """export function renderEmbeddables(state: State, el?: Element) {
  const link = state.activeEmbeddable?.element ?? null;
  const label = `${el?.width ? "wide" : "narrow"} ? maybe`;
  return state.visible ? link : label;
}
"""


class Params(unittest.TestCase):
    def test_java_array_and_varargs_parameters(self):
        self.assertEqual(passthrough._param_names("private static String toHex(byte hash[])", "toHex", "java"), ["hash"])
        self.assertEqual(passthrough._param_names("static int sum(int... values)", "sum", "java"), ["values"])


class Vendored(unittest.TestCase):
    def test_names(self):
        for name in ("jquery-1.10.2.min.js", "static/js/libs/ace.js", "jquery.form.js", "jquery-ui-1.10.4.custom.min.js", "dat.gui.min.js", "three.js", "morris-0.4.3.min.js", "app.bundle.js"):
            self.assertTrue(codefiles.is_vendored(Path(name)), name)
        for name in ("src/reactor.js", "stats.js", "app.js", "acer.js", "threefold.ts"):
            self.assertFalse(codefiles.is_vendored(Path(name)), name)


class Tools(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.p = self.home / "proj"; (self.p / "src").mkdir(parents=True)
        install(self.home, self.p, "--agents", "claude", "--skip-all")

    def run_tool(self, *args):
        r = project_cmd(self.p, self.home, "code", *args, check=False)
        return r.stdout + r.stderr

    def test_java_array_parameter_is_read(self):
        (self.p / "src" / "MD5.java").write_text(JAVA, encoding="utf-8")
        out = self.run_tool("style", "--all", "src")
        self.assertNotIn("never read", out, out)

    def test_app_py_groups_are_gated_and_test_groups_are_not(self):
        body = "\n".join(f"    x{i} = {i}" for i in range(8))
        pair = f"def alpha(a):\n{body}\n    return a\n\n\ndef beta(b):\n{body}\n    return b\n"
        (self.p / "src" / "app.py").write_text(pair, encoding="utf-8")
        tests = pair.replace("alpha", "test_alpha").replace("beta", "test_beta").replace("    return", "    assert True\n    return")
        (self.p / "tests").mkdir(); (self.p / "tests" / "test_x.py").write_text(tests, encoding="utf-8")
        out = self.run_tool("clones", "src", "tests")
        self.assertRegex(out, r"src/app\.py:alpha.*\n?.*(?<!\[tests\])$", "app.py is not a test file")
        self.assertIn("test_x.py:test_alpha", out)
        self.assertEqual(out.count("[tests]"), 1, out)

    def test_vendored_files_are_invisible_to_style_and_security(self):
        (self.p / "src" / "static" / "js" / "libs").mkdir(parents=True)
        (self.p / "src" / "static" / "js" / "libs" / "ace.js").write_text("function a(){ document.body.innerHTML = location.hash; eval(location.hash); }\n" * 3, encoding="utf-8")
        (self.p / "src" / "jquery-1.10.2.min.js").write_text("eval(location.hash);\n", encoding="utf-8")
        (self.p / "src" / "own.js").write_text("export function f(x) { return eval(x); }\n", encoding="utf-8")
        security = self.run_tool("security", "src")
        self.assertIn("own.js", security); self.assertNotIn("ace.js", security); self.assertNotIn("jquery", security)
        style = self.run_tool("style", "--all", "src")
        self.assertNotIn("ace.js", style)

    def test_tsx_optional_chaining_is_not_a_branch(self):
        (self.p / "src" / "embed.tsx").write_text(TSX, encoding="utf-8")
        out = self.run_tool("style", "src/embed.tsx:renderEmbeddables")
        self.assertRegex(out, r"cyclomatic complexity\s+3\b", out)   # `??` and the last ternary, plus 1; `?.`, `el?:` and the template text count nothing


if __name__ == "__main__":
    unittest.main()
