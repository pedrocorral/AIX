"""Java style measured as Checkstyle and Campbell define it (benchmark section 13): a parameter list over several
lines is counted, a method head with an annotation before the return type is a function, and cognitive complexity
follows the 2017 definition (try is not a nesting level, a run of like boolean operators is +1, `else if` is one
branch): the WebGoat shape that PMD and a hand count put at 10."""
import re, unittest

from helpers import install, project_cmd, temp_home

LESSON = """package app;
public class Lesson {
  public String eight(
      String field1,
      String field2,
      String field3,
      java.util.Map<String, java.util.List<String>> field4,
      String field5,
      String field6,
      String field7,
      Integer error) {
    return field1;
  }

  public @ResponseBody String follow(@PathVariable("user") String user) {
    return user;
  }

  public String completed(String editor) {
    try {
      if (editor.isEmpty()) return "empty";
      boolean a = check(editor), b = check(editor), c = check(editor), d = check(editor), e = check(editor), f = check(editor);
      boolean hasImportant = (a && b && c && d && (e || f));
      java.util.List<String> errors = compile(editor);
      if (hasImportant && errors.size() < 1) {
        return "ok";
      } else if (errors.size() > 0) {
        String out = "";
        for (String err : errors) {
          out += err;
        }
        return out;
      } else {
        return "failed";
      }
    } catch (Exception e) {
      return e.getMessage();
    }
  }

  private boolean check(String s) { return s.isEmpty(); }
  private java.util.List<String> compile(String s) { return java.util.List.of(); }
}
"""


class JavaStyle(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        (self.project / "src/main/java/app").mkdir(parents=True)
        (self.project / "src/main/java/app/Lesson.java").write_text(LESSON, encoding="utf-8")
        install(self.home, self.project)

    def card(self, func: str) -> str:
        return project_cmd(self.project, self.home, "code", "style", f"src/main/java/app/Lesson.java:{func}", check=False).stdout

    def test_parameters_over_several_lines_are_counted(self):
        self.assertRegex(self.card("eight"), r"parameters\s+8\s+limit 5\s+OVER")

    def test_annotation_before_the_return_type_is_a_method(self):
        out = project_cmd(self.project, self.home, "code", "style", "src", check=False).stdout
        self.assertIn("functions analysed 5", out, out)
        self.assertRegex(self.card("follow"), r"parameters\s+1\s")

    def test_cognitive_complexity_by_the_definition(self):
        card = self.card("completed")
        self.assertRegex(card, r"cognitive complexity\s+10\s", card)
        self.assertRegex(card, r"cyclomatic complexity\s+12\s", "McCabe counts every boolean operator, as Checkstyle does\n" + card)
        self.assertRegex(card, r"nesting depth\s+3\s", card)

    def test_line_numbers_still_point_at_the_head(self):
        self.assertTrue(re.search(r"Lesson\.java:completed  \(line 19", self.card("completed")))


if __name__ == "__main__":
    unittest.main()
