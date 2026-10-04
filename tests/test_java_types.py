"""Java taint across files through the receiver's declared type (javatypes.py, benchmark section 17): a call on a
field typed `AccountService` is followed into that class only, not into another class with a method of the same
name; a field typed by an interface is followed into every implementation; a chain of two calls is followed to its
end; a receiver whose type cannot be read falls back to the name-and-arity rule."""
import unittest

from helpers import install, project_cmd, temp_home

FILES = {
    "Api.java": """package app;
@RestController
public class Api {
  private AccountService accountService;
  private ThingInterface thing;
  @GetMapping("/a")
  public String a(@RequestParam String q) {
    return accountService.find(q);
  }
  @GetMapping("/b")
  public String b(@RequestParam String q) {
    return thing.doSomething(q);
  }
  @GetMapping("/c")
  public String c(@RequestParam String q) {
    return accountService.twoHops(q);
  }
  @GetMapping("/d")
  public String d(@RequestParam String q) {
    return mystery.find(q);
  }
}
""",
    "AccountService.java": """package app;
public class AccountService {
  private AccountRepository accountRepository;
  public String find(String name) {
    return jdbc.queryForList("SELECT * FROM a WHERE n = '" + name + "'").toString();
  }
  public String twoHops(String name) {
    return accountRepository.raw(name);
  }
}
""",
    "AccountRepository.java": """package app;
public class AccountRepository {
  public String raw(String name) {
    return jdbc.queryForObject("SELECT * FROM r WHERE n = '" + name + "'", String.class);
  }
}
""",
    "LabelService.java": """package app;
public class LabelService {
  public String find(String name) {
    return jdbc.queryForList("SELECT * FROM labels WHERE n = '" + name + "'").toString();
  }
}
""",
    "ThingInterface.java": "package app;\npublic interface ThingInterface {\n  String doSomething(String x);\n}\n",
    "Thing1.java": """package app;
public class Thing1 implements ThingInterface {
  public String doSomething(String x) {
    return jdbc.queryForList("SELECT * FROM t1 WHERE n = '" + x + "'").toString();
  }
}
""",
    "Thing2.java": """package app;
public class Thing2 implements ThingInterface {
  public String doSomething(String x) {
    return jdbc.queryForList("SELECT * FROM t2 WHERE n = '" + x + "'").toString();
  }
}
""",
}


class TypedTaint(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        src = self.project / "src/main/java/app"; src.mkdir(parents=True)
        for name, text in FILES.items():
            (src / name).write_text(text, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "vulnerabilities", check=False).stdout

    def paths(self, file: str) -> list:
        return [l.strip() for l in self.out.splitlines() if "argument of" in l and file in l]

    def test_followed_through_the_type_not_by_name(self):
        self.assertIn("AccountService.java:5  input reaches SQL statement", self.out, self.out)
        self.assertTrue(any("AccountService.find in" in p and "q: @RequestParam" in p for p in self.paths("AccountService")), self.out)

    def test_an_interface_reaches_every_implementation(self):
        for cls in ("Thing1", "Thing2"):
            self.assertIn(f"{cls}.java:4  input reaches SQL statement", self.out, self.out)

    def test_two_hops(self):
        self.assertIn("AccountRepository.java:4  input reaches SQL statement", self.out, self.out)
        self.assertTrue(any("AccountRepository.raw in" in p for p in self.paths("AccountRepository")), self.out)

    def test_unknown_receiver_falls_back_to_the_name(self):
        hits = [l for l in self.out.splitlines() if "LabelService.java:4" in l]
        self.assertEqual(len(hits), 1, "reached once, from `mystery.find(q)` by name; not from `accountService.find(q)`, whose type is known\n" + self.out)


if __name__ == "__main__":
    unittest.main()
