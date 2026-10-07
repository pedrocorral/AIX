"""`@checked` (guard.py): types from the annotations, Optional and unions, generics by their container, conditions
through typing.Annotated, keyword and default arguments, the result on request, the error messages, the per-call cost
bound; and `aix code defensive` counting it as a guard and a door passed into a checked function as checked."""
import sys, timeit, unittest
from pathlib import Path
from typing import Annotated, Any, Optional

from helpers import KIT, install, project_cmd, temp_home

sys.path.insert(0, str(KIT / ".aix" / "scripts"))
from guard import between, checked, cond, has_keys, matches, non_empty, one_of, positive  # noqa: E402


@checked
def read_rule(path: Path, weight: Annotated[int, between(0, 100)], name: Annotated[str, non_empty()] = "x", tags: list = None) -> str:
    return f"{path}:{weight}:{name}:{len(tags or [])}"


@checked(result=True)
def half(n: Annotated[int, positive()]) -> int:
    return n // 2 if n > 1 else "zero"


@checked
def pick(kind: Annotated[str, one_of("a", "b")], code: Annotated[str, matches(r"[A-Z]{3}")], extra: Optional[int] = None, anything: Any = 0, rows: list[str] = ()) -> None:
    return None


@checked
def load(data: Annotated[dict, has_keys("name", "version")]) -> str:
    return data["name"]


class Checked(unittest.TestCase):
    def test_right_values_pass_and_return(self):
        self.assertEqual(read_rule(Path("a"), 50), "a:50:x:0")
        self.assertEqual(read_rule(Path("a"), weight=0, name="n", tags=[1]), "a:0:n:1")
        pick("a", "ABC"); pick("b", "XYZ", extra=3, rows=["r"])
        self.assertEqual(load({"name": "k", "version": "1"}), "k")

    def test_wrong_type_names_the_function_the_parameter_and_both_types(self):
        with self.assertRaises(TypeError) as e:
            read_rule("a", 50)
        self.assertEqual(str(e.exception), "read_rule: path must be Path, got str")
        with self.assertRaises(TypeError) as e:
            pick("a", "ABC", extra="3")
        self.assertEqual(str(e.exception), "pick: extra must be int | NoneType, got str")
        with self.assertRaises(TypeError):
            pick("a", "ABC", rows="not a list")

    def test_conditions_fail_with_their_text(self):
        with self.assertRaises(ValueError) as e:
            read_rule(Path("a"), 120)
        self.assertEqual(str(e.exception), "read_rule: weight failed 'between 0 and 100', got 120")
        with self.assertRaises(ValueError) as e:
            read_rule(Path("a"), 1, name="")
        self.assertEqual(str(e.exception), "read_rule: name failed 'non-empty', got ''")
        with self.assertRaises(ValueError) as e:
            pick("c", "ABC")
        self.assertEqual(str(e.exception), "pick: kind failed 'one of a, b', got 'c'")
        with self.assertRaises(ValueError):
            pick("a", "abc")
        with self.assertRaises(ValueError) as e:
            load({"name": "k"})
        self.assertEqual(str(e.exception), "load: data failed 'an object with name, version', got {'name': 'k'}")

    def test_result_checked_on_request_and_optional_none_allowed(self):
        self.assertEqual(half(4), 2)
        with self.assertRaises(TypeError) as e:
            half(1)
        self.assertEqual(str(e.exception), "half: result must be int, got str")
        with self.assertRaises(ValueError):
            half(0)
        pick("a", "ABC", extra=None)

    def test_a_condition_that_errors_fails_the_check_and_any_accepts_everything(self):
        @checked
        def f(v: Annotated[int, cond("even", lambda n: n % 2 == 0)], w: Any = None) -> None:
            return None
        f(2, w=object())
        with self.assertRaises(ValueError):
            f(3)

    def test_the_decorated_function_keeps_its_name_and_is_marked(self):
        self.assertEqual(read_rule.__name__, "read_rule"); self.assertTrue(read_rule.__checked__)

    def test_cost_per_call_stays_small(self):
        n = 50_000
        t = timeit.timeit(lambda: read_rule(Path("a"), 50, "n", []), number=n) / n
        self.assertLess(t, 20e-6, f"{t * 1e6:.1f} µs per call")


class GateKnowsIt(unittest.TestCase):
    def test_defensive_counts_checked_as_a_guard_and_a_door_into_it_as_checked(self):
        home = temp_home(self); project = home / "app"
        (project / "src").mkdir(parents=True)
        (project / "src/guard.py").write_text("def checked(fn=None, **kw):\n    return fn or (lambda f: f)\n")
        (project / "src/reader.py").write_text("import json\nfrom guard import checked\n\n@checked\ndef use(data: dict) -> str:\n    return data['name']\n\n"
                                               "def load(p: str) -> str:\n    data = json.load(open(p))\n    return use(data)\n\ndef raw(p: str) -> dict:\n    return json.load(open(p))\n")
        install(home, project)
        out = project_cmd(project, home, "code", "defensive", "src", check=False).stdout
        self.assertIn("guards        @checked on 1 function; pydantic not imported", out, out)
        self.assertIn("2 reads of outside data (json, yaml, toml, request bodies, untyped handler parameters), 1 unchecked", out, out)
        self.assertRegex(out, r"DOOR    src/reader\.py:13", out); self.assertNotRegex(out, r"DOOR    src/reader\.py:9\b", out)
        self.assertNotIn("add pydantic", out, "a project with its own guard is not told to add one\n" + out)
        self.assertIn("Recommendation: 1 door unchecked: pass each parsed value into a @checked function, or check its shape where it is read", out, out)


if __name__ == "__main__":
    unittest.main()
