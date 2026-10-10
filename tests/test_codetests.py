"""`aix code tests`: every module of the tree with its own tests or NO TESTS, and the functions to test first.
A module counts only the tests that import it directly (a test of the parent does not test the part); Rust's
`#[cfg(test)]` is an inline test; a test that imports nothing is credited to none; the gate fails on an untested
module. Priority: the call paths ending in a function times its cognitive complexity, a function a test calls (from a named test
function or by name from an anonymous callback) is tested, one reached only through others is touched, and the
complex, widely reached, untested function comes first. `--affected` is `aix code affected`."""
import subprocess, sys, unittest

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
import codetests  # noqa: E402

COMPLEX = "def parse(text):\n" + "".join(f"    {'    ' * i}if text[{i}]:\n" for i in range(5)) + "    " * 6 + "return 1\n    return 0\n"


class Weight(unittest.TestCase):
    def test_every_call_path_ending_in_a_function_counts(self):
        weights = codetests.path_weights(["A", "B", "C", "D"], {("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")})
        self.assertEqual(weights["D"], 4, "B->D, C->D, A->B->D, A->C->D")

    def test_a_loop_counts_once(self):
        weights = codetests.path_weights(["a", "b", "c", "d"], {("a", "b"), ("b", "c"), ("c", "b"), ("d", "c")})
        self.assertEqual(weights, {"a": 0, "b": 2, "c": 2, "d": 0}, "b and c call each other: one function; a and d each add one path")

    def test_calls_out_of_a_loop_count_once(self):
        both_call_d = codetests.path_weights(["X", "L1", "L2", "D"], {("X", "L1"), ("L1", "L2"), ("L2", "L1"), ("L1", "D"), ("L2", "D")})
        self.assertEqual(both_call_d["D"], 2, "X->L->D and L->D: the loop is one function")
        entered_twice = codetests.path_weights(["X", "L1", "L2", "D"], {("X", "L1"), ("X", "L2"), ("L1", "L2"), ("L2", "L1"), ("L2", "D")})
        self.assertEqual(entered_twice["D"], 2)
        self.assertEqual(entered_twice["L1"], entered_twice["L2"], "the members of a loop share one weight")

    def test_a_method_takes_its_complexity_whatever_the_language_names_it(self):
        self.assertEqual(codetests.cognitive_of("svc.ts:Cart.total", {"svc.ts:total": 3}), 3)
        self.assertEqual(codetests.cognitive_of("a.py:C.m", {"a.py:C.m": 5, "a.py:m": 1}), 5)


class Command(unittest.TestCase):
    FILES = {
        "src/orders/api.py": "from src.orders.pricing.quote import quote\ndef place(cart):\n    return quote(cart)\n",
        "src/orders/pricing/quote.py": "from src.shared.parse import parse\ndef quote(cart):\n    return parse(cart)\n",
        "src/shared/parse.py": COMPLEX,
        "src/shared/money.py": "def cents(x):\n    return x\n",
        "src/legacy/old.py": "def unused():\n    return 1\n",
        "crates/core/Cargo.toml": '[package]\nname = "core"\n',
        "crates/core/src/lib.rs": "pub fn add(a: u8, b: u8) -> u8 { a + b }\n#[cfg(test)]\nmod tests { #[test] fn t() { assert_eq!(super::add(1, 1), 2); } }\n",
        "tests/test_orders.py": "from src.orders.api import place\ndef test_place():\n    assert place('x') is not None\n",
        "tests/test_money.py": "from src.shared.money import cents\nCASES = [lambda: cents(1)]\n",
        "tests/test_cli.py": "import subprocess\ndef test_cli():\n    subprocess.run(['true'])\n",
    }

    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for rel, text in self.FILES.items():
            (self.project / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.project / rel).write_text(text, encoding="utf-8")
        install(self.home, self.project)

    def run_tool(self, *args, check=True):
        return project_cmd(self.project, self.home, "code", "tests", *args, "src", "crates", "tests", check=check)

    def test_the_tree_its_own_tests_and_the_gate(self):
        out = self.run_tool().stdout
        for line in ("orders/  1 test file(s)", "pricing/  NO TESTS", "shared/  1 test file(s)", "legacy/  NO TESTS", "crates/core/src/  inline tests",
                     "1 test file(s) import no module"):
            self.assertIn(line, out, out)
        self.assertEqual(self.run_tool("--untested").stdout.split(), ["src/legacy", "src/orders/pricing"], "pricing's parent is tested, not pricing")
        r = self.run_tool("--gate", check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("2 module(s) without their own tests", r.stderr)

    def test_the_report_lists_itself_in_an_index_written_before_it_existed(self):
        index = self.project / "docs/tests/INDEX.md"
        index.write_text("\n".join(l for l in index.read_text(encoding="utf-8").splitlines() if "tests-by-module.md" not in l) + "\n", encoding="utf-8")
        self.run_tool("--report"); self.run_tool("--report")
        self.assertEqual(index.read_text(encoding="utf-8").count("`tests-by-module.md`"), 1, "an upgraded project's index gains the row once")

    def test_priority_puts_the_complex_widely_reached_untested_function_first(self):
        out = self.run_tool("--priority").stdout
        rows = [l.split() for l in out.splitlines() if l.strip().startswith(tuple("0123456789"))]
        first = rows[0]
        self.assertTrue(first[-1].endswith("src/shared/parse.py:parse"), out)
        self.assertEqual(first[4], "touched", "reached by the orders test only through place and quote")
        money = [l for l in out.splitlines() if "money.py:cents" in l]
        self.assertFalse(money, "cents scores 0 (no complexity): not listed")

    def test_a_call_from_an_anonymous_callback_credits_the_function(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.aix/scripts'); import codetests; "
                            "print(sorted(codetests.named_in_tests(['src', 'tests'], ['src/shared/money.py:cents', 'src/legacy/old.py:unused'])))"],
                           cwd=self.project, capture_output=True, text=True, env=__import__("helpers").env(self.home))
        self.assertEqual(r.stdout.strip(), "['src/shared/money.py:cents']", r.stderr)

    def test_a_project_inside_a_larger_repository(self):
        """git prints paths from the repository root; the project's are relative to the project (--relative)."""
        repo = self.home / "repo"
        repo.mkdir()
        __import__("shutil").move(str(self.project), str(repo / "app"))
        self.project = repo / "app"
        git = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, capture_output=True, check=True)
        git("init", "-q"); git("add", "-A"); git("commit", "-qm", "base")
        (self.project / "src/orders/api.py").write_text(self.FILES["src/orders/api.py"] + "# changed\n", encoding="utf-8")
        self.assertEqual(self.run_tool("--affected", "--plain").stdout.split(), ["tests/test_orders.py"])

    def test_affected_is_the_same_command(self):
        git = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=self.project, capture_output=True, check=True)
        git("init", "-q"); git("add", "-A"); git("commit", "-qm", "base")
        (self.project / "src/orders/api.py").write_text(self.FILES["src/orders/api.py"] + "# changed\n", encoding="utf-8")
        self.assertEqual(self.run_tool("--affected", "--plain").stdout.split(), ["tests/test_orders.py"])


if __name__ == "__main__":
    unittest.main()
