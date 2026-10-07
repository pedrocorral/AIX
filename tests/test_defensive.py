"""`aix code defensive` on planted Python (the shapes checked against flask, requests, pygoat and a FastAPI project): the annotation counts, the pydantic facts and the recommendation, the
doors (outside data reaching the code unchecked, an untyped FastAPI handler parameter), and the inside findings
(an assert in production code, `open()` without `with`, None returned under an annotation that promises a value).
RETURN and OPEN gate; DOOR and ASSERT are advice; a handler is known by its decorator, never by a parameter name."""
import unittest

from helpers import install, project_cmd, temp_home

RETURNS = '''
import sys
from typing import Any, Optional

def explicit(x: int) -> str:
    if x:
        return "a"
    return None

def ternary(x: int) -> str:
    return None if x else "a"

def bare(x: int) -> str:
    if x:
        return "a"
    return

def falls_off(x: int) -> str:
    if x:
        return "a"

def honest(x: int) -> str | None:
    return None

def optional(x: int) -> Optional[str]:
    return None

def nothing(x: int) -> None:
    return None

def stub(x: int) -> str:
    raise NotImplementedError

def both_branches(x: int) -> str:
    if x:
        return "a"
    else:
        return "b"

def exits(x: int) -> str:
    if x:
        return "a"
    sys.exit("no")

def anything(x: int) -> Any:
    return None
'''

OPENS = '''
import json

def leaks(p):
    f = open(p)
    return f.read()

def nested(p):
    return json.load(open(p))

def managed(p):
    with open(p) as f:
        return f.read()

def closed(p):
    f = open(p)
    try:
        return f.read()
    finally:
        f.close()

def handed_over(p):
    return open(p, "rb")
'''

DOORS = '''
import json
from flask import request
from app.models import Config

def unchecked(p):
    data = json.load(p)
    return data["x"]

def wrapped(p):
    return Config.model_validate(json.load(p))

def built(p):
    data = json.load(p)
    return Config(**data)

def typed(p):
    data = json.load(p)
    if not isinstance(data, dict):
        raise ValueError("object expected")
    return data

def form():
    return request.form["name"]

def converted():
    return int(request.args.get("page", 1))
'''

HANDLERS = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items/{item_id}")
def read_item(item_id: int, q):
    return {"item_id": item_id, "q": q}

@app.post("/items")
def create_item(item: dict):
    return item

class Adapter:
    def send(self, request, stream=False):
        return request
'''

MODELS = '''
from pydantic import BaseModel, ConfigDict, Field, field_validator, validate_call

class Loose(BaseModel):
    name: str

class Strict(BaseModel):
    model_config = ConfigDict(strict=True)
    age: int = Field(gt=0)

    @field_validator("age")
    @classmethod
    def positive(cls, v):
        return v

@validate_call
def double(n: int) -> int:
    return n * 2
'''


class Defensive(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src").mkdir(parents=True); (self.project / "tests").mkdir()
        install(self.home, self.project)

    def plant(self, name: str, text: str, folder: str = "src"):
        (self.project / folder / name).write_text(text)

    def run_tool(self, *flags):
        return project_cmd(self.project, self.home, "code", "defensive", "src", *flags, check=False)

    def output(self, *flags) -> str:
        r = self.run_tool(*flags)
        return r.stdout + r.stderr

    def test_none_under_an_annotation_that_promises_a_value(self):
        self.plant("returns.py", RETURNS)
        out = self.output("--gate")
        self.assertIn("RETURN  src/returns.py:5  explicit(): returns None (line 8) under `-> str`   -> annotate `-> str | None` or raise", out, out)
        self.assertIn("RETURN  src/returns.py:10  ternary(): returns None (line 11) under `-> str`", out, out)
        self.assertIn("RETURN  src/returns.py:13  bare(): returns None (line 16) under `-> str`", out, out)
        self.assertIn("RETURN  src/returns.py:18  falls_off(): falls off the end (line 20) under `-> str`", out, out)
        for name in ("honest", "optional", "nothing", "stub", "both_branches", "exits", "anything"):
            self.assertNotIn(f"{name}()", out, out)
        self.assertIn("4 returning None under an annotation that promises a value", out, out)
        self.assertIn("GATE FAILED: 4 finding(s)", out, out)

    def test_open_without_with_and_without_close(self):
        self.plant("opens.py", OPENS)
        out = self.output("--gate")
        self.assertIn("OPEN    src/opens.py:5  open() without `with` and no close()   -> `with open(...) as f:`", out, out)
        self.assertIn("OPEN    src/opens.py:9  open() without `with`", out, out)
        for line in (12, 16, 23):
            self.assertNotIn(f"opens.py:{line}", out, out)
        self.assertIn("2 open() without `with`", out, out)
        self.assertIn("GATE FAILED: 2 finding(s)", out, out)

    def test_doors_are_reads_of_outside_data_reaching_the_code_unchecked(self):
        self.plant("doors.py", DOORS)
        r = self.run_tool("--gate")
        out = r.stdout
        self.assertIn("DOOR    src/doors.py:7  json.load(...) reaches the code unchecked   -> parse it into a strict pydantic model, or check its shape", out, out)
        self.assertIn("DOOR    src/doors.py:24  request.form reaches the code unchecked", out, out)
        for line in (11, 14, 18, 27):
            self.assertNotIn(f"doors.py:{line}", out, out)
        self.assertIn("6 reads of outside data (json, yaml, toml, request bodies, untyped handler parameters), 2 unchecked", out, out)
        self.assertEqual(r.returncode, 0, "doors are advice: " + out)
        self.assertIn("GATE PASSED", out)

    def test_a_handler_is_known_by_its_decorator_not_by_a_parameter_name(self):
        self.plant("handlers.py", HANDLERS)
        out = self.run_tool().stdout
        self.assertIn("DOOR    src/handlers.py:6  read_item(): parameter `q` has no type, it arrives unchecked   -> annotate it; FastAPI checks what is typed", out, out)
        self.assertNotIn("item_id", out, out); self.assertNotIn("create_item", out, out); self.assertNotIn("send(", out, out)
        self.assertIn("3 reads of outside data", out, out); self.assertIn(", 1 unchecked", out, out)

    def test_asserts_count_in_production_code_only(self):
        self.plant("checks.py", "def pick(x: int) -> int:\n    assert x > 0\n    return x\n")
        self.plant("test_checks.py", "def test_pick():\n    assert pick(1) == 1\n", folder="tests")
        r = project_cmd(self.project, self.home, "code", "defensive", "src", "tests", "--gate", check=False)
        self.assertIn("ASSERT  src/checks.py:2  assert as a check   -> `python -O` removes it; raise ValueError", r.stdout, r.stdout)
        self.assertNotIn("test_checks.py", r.stdout, r.stdout)
        self.assertIn("1 assert in production code", r.stdout, r.stdout)
        self.assertEqual(r.returncode, 0, "asserts are advice: " + r.stdout)

    def test_annotation_counts_and_the_recommendation_to_annotate_first(self):
        self.plant("mixed.py", "def typed(a: int, b: str) -> int:\n    return a\n\ndef half(a: int, b) -> int:\n    return a\n\ndef bare(a, b):\n    return a\n\ndef none() -> int:\n    return 1\n")
        out = self.run_tool().stdout
        self.assertIn("annotations   2 fully typed (50 %), 1 with no typed parameter", out, out)
        self.assertIn("Recommendation: 1 function carries no parameter type: annotate it first, no checker works without types", out, out)

    def test_pydantic_facts_and_the_strict_recommendation(self):
        self.plant("models.py", MODELS)
        out = self.run_tool().stdout
        self.assertIn("guards        pydantic: 2 models (1 strict, 1 field with a value rule, 1 validator), 1 function under validate_call (0 strict)", out, out)
        self.assertIn("Recommendation: 1 of 2 models and 1 of 1 validate_call are not strict: pydantic converts '5' to 5 silently; set `ConfigDict(strict=True)`", out, out)
        self.assertNotIn("add pydantic", out, out)

    def test_without_pydantic_the_recommendation_names_it(self):
        self.plant("plain.py", "import json\n\ndef load(p: str) -> dict:\n    return json.load(open(p))\n")
        out = self.run_tool().stdout
        self.assertIn("guards        pydantic not imported: nothing checks an argument at run time", out, out)
        self.assertIn("Recommendation: add pydantic: `@validate_call(config=ConfigDict(strict=True))` on the functions behind the doors, outside data parsed into models;"
                      " a project that allows no dependencies writes one decorator of its own", out, out)
        self.assertIn("Swallowed exceptions and mutable defaults: aix code style", out, out)

    def test_a_project_without_python_says_so(self):
        self.plant("app.js", "function f(a) { return a }\n")
        r = self.run_tool("--gate")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Python: 0 files, 0 functions (tests excluded); JS/TS, Rust and Java are not read yet", r.stdout, r.stdout)
        self.assertIn("listed 0 (0 gated)", r.stdout)

    def test_report_file(self):
        self.plant("opens.py", OPENS)
        self.run_tool("--report")
        self.assertIn("OPEN    src/opens.py:5", (self.project / "docs/tests/code-defensive.md").read_text())


if __name__ == "__main__":
    unittest.main()
