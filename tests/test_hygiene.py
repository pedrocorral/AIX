"""24. Hygiene findings of `aix code style`, gated, five languages: leftovers (unused imports, variables, parameters),
swallowed exceptions, and the unambiguous bugs (mutable defaults, assignment in a condition, String ==). Every line
marked FIND:kind is reported with that kind, every other line is clean: re-export files, `_` names, framework-called
and overriding functions, abstract bodies, explicit intent inside a catch, parenthesised assignments."""
import re, unittest
from helpers import install, project_cmd, temp_home
from hygiene_samples import JAVA, JS, PY, RS

def marks(src: str) -> dict:
    """line -> kind for every FIND marker."""
    return {i: m.group(1) for i, l in enumerate(src.splitlines(), 1) for m in [re.search(r"FIND:(\w+)", l)] if m}


SAMPLES = {"sample.py": (PY, marks(PY)), "sample.js": (JS, marks(JS)), "sample.rs": (RS, marks(RS)), "Sample.java": (JAVA, marks(JAVA))}


class Hygiene(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self)
        self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True)
        for name, (src, _) in SAMPLES.items():
            (self.project / "src" / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)

    def found(self, name: str) -> dict:
        out = project_cmd(self.project, self.home, "code", "style", f"src/{name}", "--all").stdout
        return {int(m.group(1)): m.group(2) for m in re.finditer(rf"LINE  src/{re.escape(name)}:(\d+)  (leftover|swallowed|bug):", out)}, out

    def check(self, name):
        got, out = self.found(name)
        self.assertEqual(got, SAMPLES[name][1], "\n" + out)

    def test_python(self):
        self.check("sample.py")

    def test_javascript(self):
        self.check("sample.js")

    def test_rust(self):
        self.check("sample.rs")

    def test_java(self):
        self.check("Sample.java")

    def test_every_kind_is_in_every_language_sample(self):
        for name, (_, want) in SAMPLES.items():
            self.assertIn("leftover", want.values(), name)
        self.assertEqual(sum(v == "leftover" for _, w in SAMPLES.values() for v in w.values()), 17)

    def test_reexport_module_and_test_file(self):
        (self.project / "src" / "compat.py").write_text("from collections.abc import Mapping, MutableMapping\nfrom json import loads\n", encoding="utf-8")
        (self.project / "src" / "core.py").write_text("from compat import Mapping\nfrom .compat import MutableMapping\n", encoding="utf-8")
        out = project_cmd(self.project, self.home, "code", "style", "src/compat.py", "--all").stdout
        self.assertNotIn("`Mapping`", out); self.assertNotIn("`MutableMapping`", out)
        self.assertIn("unused import `loads`", out, "a re-export module still has real leftovers")

    def test_gate_counts_and_card(self):
        r = project_cmd(self.project, self.home, "code", "style", "src", "--gate", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"leftovers 17, swallowed 7, bugs 5")
        card = project_cmd(self.project, self.home, "code", "style", "src/sample.py:mutable_default").stdout
        self.assertIn("mutable default", card)
        clean = project_cmd(self.project, self.home, "code", "style", "src/sample.py:fine_defaults").stdout
        self.assertIn("no findings", clean)


if __name__ == "__main__":
    unittest.main()
